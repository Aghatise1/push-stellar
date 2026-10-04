import base64
import binascii
import hashlib
import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from stellar_sdk import Asset, Keypair, Network, Server, TransactionBuilder, TransactionEnvelope
from stellar_sdk.exceptions import BadRequestError, BadSignatureError, BaseRequestError, NotFoundError


class StellarVerificationError(ValueError):
    pass


TESTNET_PASSPHRASE = Network.TESTNET_NETWORK_PASSPHRASE


def valid_account_id(value):
    try:
        raw = base64.b32decode(value,casefold=False)
    except (binascii.Error,ValueError):
        return False
    if len(raw) != 35 or raw[0] != 6 << 3:
        return False
    checksum = 0
    for byte in raw[:-2]:
        checksum ^= byte << 8
        for _ in range(8):
            checksum = ((checksum << 1) ^ 0x1021) & 0xffff if checksum & 0x8000 else (checksum << 1) & 0xffff
    return raw[-2:] == checksum.to_bytes(2,'little')


def assignment_memo(assignment_id):
    return f'push-{assignment_id.hex[:20]}'


def payment_uri(*, destination, amount, memo, asset='USDC'):
    query = urlencode({
        'destination': destination,
        'amount': str(amount),
        'memo': memo,
        'memo_type': 'MEMO_TEXT',
        'network_passphrase': 'Test SDF Network ; September 2015',
        'msg': 'Push testnet assignment settlement. Test assets have no monetary value.',
    })
    if asset == 'USDC':
        query += '&' + urlencode({
            'asset_code': 'USDC',
            'asset_issuer': settings.STELLAR_TESTNET_USDC_ISSUER,
        })
    return f'web+stellar:pay?{query}'


def _get_json(url):
    request = Request(url,headers={'Accept':'application/json','User-Agent':'Push-Stellar-Prototype/1.0'})
    try:
        with urlopen(request,timeout=8) as response:
            return json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise StellarVerificationError('That transaction was not found on Stellar testnet.') from exc
        raise StellarVerificationError('Stellar testnet could not verify that transaction.') from exc
    except (URLError,TimeoutError,json.JSONDecodeError) as exc:
        raise StellarVerificationError('Stellar testnet is temporarily unavailable. Try verification again shortly.') from exc


def account_balances(address):
    """Return the connected account's native XLM and configured test USDC balances."""
    base = settings.STELLAR_TESTNET_HORIZON.rstrip('/')
    try:
        account = _get_json(f'{base}/accounts/{address}')
    except StellarVerificationError as exc:
        if 'transaction was not found' in str(exc):
            raise StellarVerificationError('This account has not been funded on Stellar testnet yet.') from exc
        raise

    result = {'xlm': Decimal('0'), 'usdc': Decimal('0'), 'has_usdc_trustline': False}
    for balance in account.get('balances', []):
        try:
            amount = Decimal(str(balance.get('balance', '0')))
        except InvalidOperation:
            continue
        if balance.get('asset_type') == 'native':
            result['xlm'] = amount
        elif (
            balance.get('asset_code') == 'USDC'
            and balance.get('asset_issuer') == settings.STELLAR_TESTNET_USDC_ISSUER
        ):
            result['usdc'] = amount
            result['has_usdc_trustline'] = True
    return result


def _transaction_body_digest(envelope):
    body = envelope.transaction.to_xdr_object().to_xdr_bytes()
    return hashlib.sha256(body).hexdigest()


def build_payment_xdr(*, source_account, destination, amount, memo, asset='XLM', base_fee=100):
    """Build an unsigned, short-lived Stellar testnet payment transaction."""
    if not valid_account_id(destination):
        raise StellarVerificationError('Enter a valid Stellar testnet recipient address.')
    try:
        amount = Decimal(str(amount)).quantize(Decimal('0.0000001'))
    except InvalidOperation as exc:
        raise StellarVerificationError('Enter a valid payment amount.') from exc
    if amount <= 0:
        raise StellarVerificationError('The payment amount must be greater than zero.')
    if len(memo.encode('utf-8')) > 28:
        raise StellarVerificationError('The Stellar memo must be 28 bytes or fewer.')
    if asset == 'XLM':
        stellar_asset = Asset.native()
    elif asset == 'USDC':
        stellar_asset = Asset('USDC', settings.STELLAR_TESTNET_USDC_ISSUER)
    else:
        raise StellarVerificationError('Push supports only testnet XLM and the configured testnet USDC asset.')
    envelope = (TransactionBuilder(
        source_account=source_account,
        network_passphrase=TESTNET_PASSPHRASE,
        base_fee=max(100, int(base_fee)),
    ).append_payment_op(
        destination=destination,
        asset=stellar_asset,
        amount=str(amount),
    ).add_text_memo(memo).set_timeout(180).build())
    return {
        'xdr': envelope.to_xdr(),
        'transaction_body_digest': _transaction_body_digest(envelope),
        'network_passphrase': TESTNET_PASSPHRASE,
    }


def prepare_payment(*, source, destination, amount, memo, asset='XLM'):
    """Validate live testnet accounts and build an unsigned transaction for Freighter."""
    if not valid_account_id(source):
        raise StellarVerificationError('Reconnect a valid Stellar testnet wallet before sending.')
    if source == destination:
        raise StellarVerificationError('Choose a recipient other than your connected wallet.')
    destination_balances = account_balances(destination)
    source_balances = account_balances(source)
    try:
        amount_decimal = Decimal(str(amount)).quantize(Decimal('0.0000001'))
    except InvalidOperation as exc:
        raise StellarVerificationError('Enter a valid payment amount.') from exc
    if amount_decimal <= 0:
        raise StellarVerificationError('The payment amount must be greater than zero.')
    if asset == 'USDC':
        if not source_balances['has_usdc_trustline']:
            raise StellarVerificationError('Your wallet needs the configured testnet USDC trustline before it can send USDC.')
        if not destination_balances['has_usdc_trustline']:
            raise StellarVerificationError('The recipient needs the configured testnet USDC trustline before receiving USDC.')
        available = source_balances['usdc']
    else:
        available = source_balances['xlm']
    if available < amount_decimal:
        raise StellarVerificationError(f'Your wallet does not have enough testnet {asset} for this payment.')
    server = Server(settings.STELLAR_TESTNET_HORIZON)
    try:
        source_account = server.load_account(source)
        base_fee = server.fetch_base_fee()
    except (NotFoundError, BaseRequestError) as exc:
        raise StellarVerificationError('Stellar testnet could not prepare this account. Confirm that it is funded and try again.') from exc
    return build_payment_xdr(
        source_account=source_account,destination=destination,amount=amount_decimal,
        memo=memo,asset=asset,base_fee=base_fee,
    )


def validate_signed_payment(*, signed_xdr, source, destination, amount, memo, asset, transaction_body_digest):
    """Reject any signed envelope that differs from the server-prepared payment intent."""
    try:
        envelope = TransactionEnvelope.from_xdr(signed_xdr, TESTNET_PASSPHRASE)
    except Exception as exc:
        raise StellarVerificationError('Freighter returned an invalid signed transaction.') from exc
    transaction = envelope.transaction
    if _transaction_body_digest(envelope) != transaction_body_digest:
        raise StellarVerificationError('The signed transaction differs from the payment Push prepared.')
    if transaction.source.account_id != source or len(transaction.operations) != 1:
        raise StellarVerificationError('The signed transaction source or operations do not match this payment.')
    operation = transaction.operations[0]
    if operation.__class__.__name__ != 'Payment' or operation.destination.account_id != destination:
        raise StellarVerificationError('The signed transaction recipient does not match this payment.')
    expected_amount = Decimal(str(amount)).quantize(Decimal('0.0000001'))
    if Decimal(str(operation.amount)).quantize(Decimal('0.0000001')) != expected_amount:
        raise StellarVerificationError('The signed transaction amount does not match this payment.')
    asset_matches = operation.asset.is_native() if asset == 'XLM' else (
        operation.asset.code == 'USDC' and operation.asset.issuer == settings.STELLAR_TESTNET_USDC_ISSUER
    )
    if not asset_matches:
        raise StellarVerificationError('The signed transaction asset does not match this payment.')
    signed_memo = getattr(transaction.memo,'memo_text',b'')
    if isinstance(signed_memo,bytes):
        signed_memo = signed_memo.decode('utf-8','strict')
    if signed_memo != memo:
        raise StellarVerificationError('The signed transaction memo does not match this payment.')
    if not envelope.signatures:
        raise StellarVerificationError('Freighter did not sign the transaction.')
    signer = Keypair.from_public_key(source)
    for signature in envelope.signatures:
        try:
            signer.verify(envelope.hash(),signature.signature)
            return envelope
        except BadSignatureError:
            continue
    raise StellarVerificationError('The transaction was not signed by the connected wallet.')


def submit_signed_payment(**expected):
    signed_xdr = expected.pop('signed_xdr')
    envelope = validate_signed_payment(signed_xdr=signed_xdr,**expected)
    try:
        result = Server(settings.STELLAR_TESTNET_HORIZON).submit_transaction(envelope)
    except BadRequestError as exc:
        codes = getattr(exc,'extras',{}).get('result_codes',{}) if getattr(exc,'extras',None) else {}
        transaction_code = codes.get('transaction','')
        message = {
            'tx_bad_seq':'The wallet sequence changed. Prepare the payment again.',
            'tx_insufficient_balance':'The wallet does not have enough spendable balance after network reserves.',
            'tx_too_late':'The payment approval expired. Prepare it again.',
        }.get(transaction_code,'Stellar rejected the signed transaction. Check the balance, trustline and recipient, then try again.')
        raise StellarVerificationError(message) from exc
    except BaseRequestError as exc:
        raise StellarVerificationError('Stellar testnet did not accept the transaction. Try again shortly.') from exc
    transaction_hash = str(result.get('hash','')).lower()
    if len(transaction_hash) != 64:
        raise StellarVerificationError('Stellar accepted the request but did not return a valid transaction hash.')
    return transaction_hash


def verify_payment(*, transaction_hash, destination, amount, memo):
    transaction_hash = transaction_hash.lower()
    base = settings.STELLAR_TESTNET_HORIZON.rstrip('/')
    transaction = _get_json(f'{base}/transactions/{transaction_hash}')
    if not transaction.get('successful'):
        raise StellarVerificationError('The transaction did not complete successfully.')
    if transaction.get('memo_type') != 'text' or transaction.get('memo') != memo:
        raise StellarVerificationError('The transaction reference does not match this assignment.')

    operations = _get_json(f'{base}/transactions/{transaction_hash}/operations?limit=200')
    records = operations.get('_embedded',{}).get('records',[])
    expected_amount = Decimal(str(amount)).quantize(Decimal('0.0000001'))
    for operation in records:
        if operation.get('type') not in {'payment','path_payment_strict_receive'}:
            continue
        try:
            received = Decimal(operation.get('amount','')).quantize(Decimal('0.0000001'))
        except InvalidOperation:
            continue
        if (
            operation.get('to') == destination
            and operation.get('asset_code') == 'USDC'
            and operation.get('asset_issuer') == settings.STELLAR_TESTNET_USDC_ISSUER
            and received == expected_amount
        ):
            return transaction_hash
    raise StellarVerificationError('No matching USDC payment to the worker was found in that transaction.')

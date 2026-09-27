import base64
import binascii
import json
from decimal import Decimal, InvalidOperation
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings


class StellarVerificationError(ValueError):
    pass


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


def payment_uri(*, destination, amount, memo):
    query = urlencode({
        'destination': destination,
        'amount': str(amount),
        'asset_code': 'USDC',
        'asset_issuer': settings.STELLAR_TESTNET_USDC_ISSUER,
        'memo': memo,
        'memo_type': 'MEMO_TEXT',
        'network_passphrase': 'Test SDF Network ; September 2015',
        'msg': 'Push testnet assignment settlement. Test assets have no monetary value.',
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

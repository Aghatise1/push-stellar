"""Testnet-only Soroban gateway. Never signs or holds a wallet secret."""
import hashlib
import json
from django.conf import settings
from stellar_sdk import Asset, Keypair, Network, SorobanServer, TransactionBuilder, TransactionEnvelope, scval, xdr
from stellar_sdk.client.requests_client import RequestsClient
from .stellar import StellarVerificationError

NETWORK = Network.TESTNET_NETWORK_PASSPHRASE
RPC = 'https://soroban-testnet.stellar.org'
ISSUER = 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'
SCALE = 10_000_000


def require_enabled():
    if not settings.PUSH_TESTNET_ESCROW_ENABLED or not settings.PUSH_TESTNET_ESCROW_CONTRACT:
        raise StellarVerificationError('Testnet escrow is not enabled on this deployment yet.')
    if settings.STELLAR_TESTNET_SOROBAN_RPC.rstrip('/') != RPC or settings.STELLAR_TESTNET_USDC_ISSUER != ISSUER:
        raise StellarVerificationError('Escrow requires the fixed official Stellar testnet configuration.')


def server():
    require_enabled()
    return SorobanServer(RPC,client=RequestsClient(request_timeout=12))


def token_address(asset):
    if asset not in ('XLM','USDC'):
        raise StellarVerificationError('Choose test XLM or test USDC.')
    return (Asset.native() if asset == 'XLM' else Asset('USDC',ISSUER)).contract_id(NETWORK)


def digest(payload):
    return hashlib.sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).digest()


def build(agreement,action,source,payload):
    rpc=server()
    aid=scval.to_bytes(bytes.fromhex(agreement.agreement_id))
    method=action
    args=[aid]
    if action == 'fund':
        method='create_fund'
        args += [scval.to_address(v) for v in (agreement.client_address,agreement.worker_address,agreement.reviewer_address,agreement.token_address)]
        args += [scval.to_int128(agreement.amount*SCALE),scval.to_uint64(agreement.deadline),scval.to_uint64(agreement.review_seconds),scval.to_uint32(agreement.revision_limit)]
    elif action == 'submit': args += [scval.to_bytes(digest(payload))]
    elif action == 'dispute':
        method='open_dispute';args += [scval.to_address(source)]
    elif action == 'resolve': args += [scval.to_int128(payload['client_amount']*SCALE),scval.to_int128(payload['worker_amount']*SCALE)]
    elif action not in ('approve','revise','refund_expired','claim_expired'):
        raise StellarVerificationError('Unsupported escrow operation.')
    envelope=(TransactionBuilder(rpc.load_account(source),NETWORK,base_fee=100)
              .append_invoke_contract_function_op(agreement.contract,method,args).set_timeout(300).build())
    prepared=rpc.prepare_transaction(envelope)
    # Refuse an unexpectedly expensive test invocation rather than silently approving it.
    if prepared.transaction.fee > SCALE:
        raise StellarVerificationError('Estimated network fee exceeds the 1 test XLM safety limit.')
    return prepared


def validate_signature(record,signed_xdr):
    if not isinstance(signed_xdr,str) or len(signed_xdr)>100_000:
        raise StellarVerificationError('Invalid signed transaction.')
    try:
        envelope=TransactionEnvelope.from_xdr(signed_xdr,NETWORK)
        if envelope.hash_hex()!=record.tx_hash:
            raise StellarVerificationError('Signed transaction differs from the exact prepared escrow operation.')
        signer=Keypair.from_public_key(record.source)
        for signature in envelope.signatures:
            try:
                signer.verify(envelope.hash(),signature.signature)
                return envelope
            except Exception:
                continue
    except StellarVerificationError: raise
    except Exception as exc:
        raise StellarVerificationError('Could not read the signed escrow transaction.') from exc
    raise StellarVerificationError('The expected wallet did not sign this transaction.')


def read_agreement(agreement,rpc=None):
    rpc=rpc or server()
    key=scval.to_vec([scval.to_symbol('Agreement'),scval.to_bytes(bytes.fromhex(agreement.agreement_id))])
    entry=rpc.get_contract_data(agreement.contract,key)
    if not entry: raise StellarVerificationError('Escrow agreement is not present on the testnet ledger.')
    data=scval.to_native(xdr.LedgerEntryData.from_xdr(entry.xdr).contract_data.val)
    expected={'client':agreement.client_address,'worker':agreement.worker_address,'arbiter':agreement.reviewer_address,'token':agreement.token_address}
    if any(str(data[k].address)!=v for k,v in expected.items()) or data['amount']!=agreement.amount*SCALE:
        raise StellarVerificationError('On-chain escrow terms do not match the accepted agreement.')
    return data

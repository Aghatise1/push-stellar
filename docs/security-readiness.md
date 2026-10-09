# Security and operational readiness

This is an engineering readiness record, not an independent audit or legal opinion. Mainnet remains outside the approved test scope.

## Trust boundaries and threats

| Risk | Existing control to verify | Remaining evidence or procedure |
| --- | --- | --- |
| Wrong signer or altered transaction | Prepared envelope and signature validation | Browser rejection and tampering regression evidence |
| Duplicate or uncertain payment | Stored transaction reference and confirmation reconciliation | Outage, concurrent request and recovery exercise |
| Forged staff access | Server role checks plus contract wallet permissions | Owner grant, revoke and dispute browser exercise |
| Staff conflict of interest | Participant exclusions in app and contract | Negative test evidence with participant wallet |
| Saved address mistaken for permission | Separate connection, ownership and contract state | Disconnect, reload and account switch browser checks |
| Reviewer key loss | No platform collection of private keys | Owner continuity, wallet replacement and recovery procedure |
| Contract storage expiry | Contract lifetime extension logic | Operational lifetime checks and restoration procedure |
| Private data exposure | Private application records; public chain references | Review metadata and uploaded file access boundaries |

## Monitoring specification

Track failed preparations, rejected submissions, age of pending transactions, reconciliation failures, RPC availability, staff permission changes and contract storage lifetime. Separate user rejection from service failure. Alert an assigned operator when a pending transaction exceeds the agreed operational threshold; thresholds and the operator must be chosen before broader operation. Do not log secrets, signed envelopes unnecessarily, or private delivery contents.

## Incident procedure

1. Record the affected release, agreement and transaction hash privately.
2. Preserve the database record and chain evidence. Never overwrite a payment as successful to clear a queue.
3. Disable new funding if required while investigating; account for existing funded agreements and authorised recovery paths.
4. Reconcile the original transaction before allowing a new attempt.
5. If staff access is compromised, suspend app access and arrange a separately signed contract revocation. An app suspension alone does not revoke chain authority.
6. Record the cause, correction and regression check before reopening the affected path.

Before real money use: independent application and contract review, legal review of escrow and dispute authority, tested key governance and recovery, monitored infrastructure, reviewed terms and asset configuration. A funding award does not replace these controls.

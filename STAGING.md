# Push staging and release procedure

The staging Blueprint and CI workflow are configuration, not evidence that an online staging service exists. Provisioning requires access to Render and a separate PostgreSQL database, OAuth client and mail credentials. No production user data should be copied to staging.

## Initial setup

1. Integrate the candidate into the existing `staging` branch through a reviewed merge, preserving its history. Do not force-push or replace that branch. Create a separate Render Blueprint using `render-staging.yaml`; do not apply it to the existing live service.
2. Check available hosting resources and pricing before provisioning. This file requests a free web service but does not provision or purchase a database.
3. Supply a separate PostgreSQL connection and new OAuth/mail credentials through protected Render settings. Never reuse the production connection or secret key. Bootstrap only designated staging owners.
4. The application derives its HTTPS origin and exact allowed host from Render's generated hostname. Register that hostname and `/accounts/google/login/callback/` on the staging OAuth client. No extra purchased domain is required for this configuration.
5. Keep escrow disabled. Test with disposable accounts and Stellar testnet assets only. Configure invitation access through the existing staff workflow.
6. Require the `application` and `contracts` GitHub checks for pull requests to `main`. Enable branch protection and disallow direct pushes. These repository settings are not enabled merely by committing YAML.
7. Set the live Render service's auto-deploy mode to **After CI Checks Pass**, or manual deployment. Verify this in the dashboard; the existing production configuration has deliberately not been altered by this batch.

## Release acceptance

On staging, use separate client, worker and unrelated accounts. Verify selection, acceptance, payment-route selection, delivery, revision and dispute. Before acceptance both message POST routes must reject writes. Accepted and disputed projects allow participant messages; completed and cancelled projects retain read-only evidence. Unrelated users cannot read or post.

The wallet must retain its receiving address after Disconnect without silently reconnecting on reload. Explicit reconnect restores signing. Test wrong networks, changed accounts and revoked permissions in a browser with Freighter. Only assignment-based payments may be prepared or submitted; requests from the removed general-transfer UI must be rejected. Confirm an assignment USDC payment against the testnet ledger and verify a replay cannot pay twice.

Review mobile and desktop pages, verify email/OAuth on staging, then merge the same tested change through a reviewed pull request. Confirm `/healthz/` reports the deployed commit. Do not call a release staged until the hosted service and these checks have actually passed.

## Recovery

Keep the prior deploy available and record the release commit. This batch changes status display labels only; it preserves stored status values and transaction history. If a release fails, roll back the application to the prior known-good deploy and verify health. Do not automatically reverse database migrations or restore production data. Future structural migrations require a separate backup and compatibility plan.

References: https://render.com/docs/blueprint-spec and https://render.com/docs/deploys

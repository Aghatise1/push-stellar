# Email delivery on Render Free

Render Free blocks outbound SMTP ports 25, 465 and 587. Gmail app-password SMTP on port 587 therefore cannot deliver Push verification or recovery messages from the current service. Push supports Brevo's transactional email API over HTTPS as the free-host-compatible transport. Existing SMTP remains useful for local or paid hosting.

1. Create a Brevo account, enable transactional email, and verify a sender address in Brevo. A custom domain with DKIM/DMARC is preferred. If you use a Gmail address as sender, Brevo may replace the visible From address with its own compliant domain.
2. Generate a Brevo API key. In Render's **push-preview → Environment**, add `PUSH_BREVO_API_KEY` as a secret. Set `PUSH_EMAIL_FROM` to the verified sender, for example `Push <verified-address@example.com>`. Never commit the key.
3. Save the environment and wait for a successful deploy. Push chooses the HTTPS backend automatically when the API key and non-local sender are present.
4. Sign in as owner or administrator and open **Email delivery**. It should show `BrevoEmailBackend`, with no Render SMTP warning. Create a one-time invitation addressed to an inbox you control, then complete registration and password recovery. Check the recipient inbox and the delivery log. A provider acceptance record does not by itself prove inbox delivery.

Until the key and sender are ready, the existing SMTP configuration can start the app but will not send mail on Render Free. Do not distribute new tester invitations expecting automatic email delivery yet; copy the one-time code from the staff invitation page and share it securely with the intended tester.

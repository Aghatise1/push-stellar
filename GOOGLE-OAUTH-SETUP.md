# Google sign-in activation

Google sign-in is implemented but remains hidden until both credentials are configured. Push uses `django-allauth` and starts OAuth with a CSRF-protected POST request.

## Google Cloud values required

Create an **OAuth 2.0 Client ID** with application type **Web application**. Configure:

- Local authorised origin: `http://127.0.0.1:8765`
- Local authorised redirect URI: `http://127.0.0.1:8765/accounts/google/login/callback/`
- Production origin: the final HTTPS domain
- Production redirect URI: `https://YOUR-DOMAIN/accounts/google/login/callback/`

Google will issue a client ID and client secret. Do not paste the client secret into templates, JavaScript, screenshots or committed files.

## Local configuration

Copy `.env.example` to `.env`, then fill only the local untracked file:

```text
PUSH_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
PUSH_GOOGLE_CLIENT_SECRET=your-client-secret
```

Restart the server. The **Continue with Google** action will appear automatically on registration and sign-in pages. If either value is absent, the route and button remain disabled.

## Production controls

- Use an HTTPS-only production origin and redirect URI.
- Keep the client secret in the hosting provider's secret manager.
- Restrict the OAuth consent screen to the intended test users until review.
- Request only `profile` and `email` scopes.
- Rotate the secret if it appears in source, logs, screenshots or chat.
- Test new-account login, existing-email linking, logout and account recovery before submission.


import os
import secrets
from pathlib import Path
from urllib.parse import parse_qsl, unquote, urlparse
from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent
local_env_path = BASE_DIR / '.env'
if local_env_path.exists():
    for raw_line in local_env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        name, value = line.split('=', 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ.setdefault(name.strip(), value)
PRODUCTION = os.environ.get('PUSH_ENV') == 'production'
DEBUG = not PRODUCTION
SECRET_KEY = os.environ.get('PUSH_SECRET_KEY')
if not SECRET_KEY:
    if PRODUCTION:
        raise ImproperlyConfigured('Set PUSH_SECRET_KEY in protected server settings.')
    key_path = BASE_DIR / '.local-key'
    if not key_path.exists():
        try:
            with key_path.open('x') as f:
                f.write(secrets.token_urlsafe(64))
        except FileExistsError:
            pass
    SECRET_KEY = key_path.read_text().strip()
if PRODUCTION and len(SECRET_KEY) < 50:
    raise ImproperlyConfigured('Production secret must contain at least 50 random characters.')
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME','').strip()
default_allowed_hosts = RENDER_EXTERNAL_HOSTNAME if PRODUCTION and RENDER_EXTERNAL_HOSTNAME else 'localhost,127.0.0.1'
ALLOWED_HOSTS = [host.strip() for host in os.environ.get('PUSH_ALLOWED_HOSTS', default_allowed_hosts).split(',') if host.strip()]
INSTALLED_APPS = ['django.contrib.auth', 'django.contrib.contenttypes', 'django.contrib.sessions',
                  'django.contrib.messages', 'django.contrib.staticfiles',
                  'allauth', 'allauth.account', 'allauth.socialaccount',
                  'allauth.socialaccount.providers.google', 'core']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'whitenoise.middleware.WhiteNoiseMiddleware',
              'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware', 'allauth.account.middleware.AccountMiddleware',
              'django.contrib.messages.middleware.MessageMiddleware',
              'django.middleware.clickjacking.XFrameOptionsMiddleware', 'core.middleware.AppSecurityMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates', 'DIRS':[BASE_DIR/'templates'],
              'APP_DIRS':True, 'OPTIONS':{'context_processors':['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth','django.contrib.messages.context_processors.messages',
              'core.context.app_context']}}]
database_url = os.environ.get('PUSH_DATABASE_URL', '').strip()
# PowerShell removes environment variables assigned an empty string. The
# explicit "local" sentinel lets the offline preview override a URL in .env.
if database_url.lower() in {'local','sqlite'}:
    database_url = ''
if database_url:
    parsed_database = urlparse(database_url)
    if parsed_database.scheme not in {'postgres', 'postgresql'} or not parsed_database.hostname or not parsed_database.path.strip('/'):
        raise ImproperlyConfigured('PUSH_DATABASE_URL must be a complete PostgreSQL connection URL.')
    database_options = dict(parse_qsl(parsed_database.query))
    database_options.setdefault('sslmode', 'require')
    database_options.setdefault('connect_timeout', 10)
    DATABASES = {'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': parsed_database.path.lstrip('/'),
        'USER': unquote(parsed_database.username or ''),
        'PASSWORD': unquote(parsed_database.password or ''),
        'HOST': parsed_database.hostname,
        'PORT': parsed_database.port or 5432,
        'OPTIONS': database_options,
        'CONN_MAX_AGE': 60,
        'CONN_HEALTH_CHECKS': True,
    }}
else:
    if PRODUCTION:
        raise ImproperlyConfigured('Production requires PUSH_DATABASE_URL for a managed PostgreSQL database.')
    DATABASES = {'default':{'ENGINE':'django.db.backends.sqlite3','NAME':BASE_DIR/'db.sqlite3','OPTIONS':{'timeout':20}}}
AUTH_USER_MODEL = 'core.User'
AUTHENTICATION_BACKENDS = ['django.contrib.auth.backends.ModelBackend','allauth.account.auth_backends.AuthenticationBackend']
AUTH_PASSWORD_VALIDATORS = [
    {'NAME':'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME':'django.contrib.auth.password_validation.MinimumLengthValidator','OPTIONS':{'min_length':12}},
    {'NAME':'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME':'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/workspace/'
LOGOUT_REDIRECT_URL = '/'
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
SESSION_COOKIE_SECURE = PRODUCTION
CSRF_COOKIE_SECURE = PRODUCTION
SESSION_COOKIE_AGE = 3600
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SECURE_SSL_REDIRECT = PRODUCTION
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https') if PRODUCTION else None
SECURE_HSTS_SECONDS = 31536000 if PRODUCTION else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = PRODUCTION
SECURE_HSTS_PRELOAD = PRODUCTION
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'
DATA_UPLOAD_MAX_MEMORY_SIZE = 128 * 1024
PASSWORD_RESET_TIMEOUT = 3600
EMAIL_FILE_PATH = BASE_DIR/'private-mail'
EMAIL_HOST = os.environ.get('PUSH_EMAIL_HOST','')
EMAIL_HOST_USER = os.environ.get('PUSH_EMAIL_USER','')
EMAIL_HOST_PASSWORD = os.environ.get('PUSH_EMAIL_PASSWORD','')
EMAIL_PORT = int(os.environ.get('PUSH_EMAIL_PORT','587'))
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get('PUSH_EMAIL_FROM','Push <noreply@localhost>')
EMAIL_DELIVERY_CONFIGURED = bool(EMAIL_HOST and EMAIL_HOST_USER and EMAIL_HOST_PASSWORD and 'localhost' not in DEFAULT_FROM_EMAIL)
EMAIL_BACKEND = ('django.core.mail.backends.smtp.EmailBackend' if EMAIL_DELIVERY_CONFIGURED
                 else 'django.core.mail.backends.filebased.EmailBackend')
default_origin = f'https://{RENDER_EXTERNAL_HOSTNAME}' if PRODUCTION and RENDER_EXTERNAL_HOSTNAME else 'http://127.0.0.1:8765'
PUSH_ORIGIN = os.environ.get('PUSH_ORIGIN',default_origin).rstrip('/')
if PRODUCTION and (not EMAIL_DELIVERY_CONFIGURED or not PUSH_ORIGIN.startswith('https://')):
    raise ImproperlyConfigured('Production requires SMTP, a verified sender and an HTTPS PUSH_ORIGIN.')
if PRODUCTION:
    parsed_origin = urlparse(PUSH_ORIGIN)
    if not ALLOWED_HOSTS or '*' in ALLOWED_HOSTS:
        raise ImproperlyConfigured('Production requires one or more exact PUSH_ALLOWED_HOSTS values; wildcards are not allowed.')
    if any('://' in host or '/' in host for host in ALLOWED_HOSTS):
        raise ImproperlyConfigured('PUSH_ALLOWED_HOSTS must contain hostnames only, without a scheme or path.')
    if not parsed_origin.hostname or parsed_origin.hostname not in ALLOWED_HOSTS or parsed_origin.path not in {'','/'}:
        raise ImproperlyConfigured('PUSH_ORIGIN must be the HTTPS origin for a hostname listed in PUSH_ALLOWED_HOSTS.')
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'UTC'
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR/'static']
STATIC_ROOT = BASE_DIR/'staticfiles'
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('PUSH_GOOGLE_CLIENT_ID','').strip()
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('PUSH_GOOGLE_CLIENT_SECRET','').strip()
GOOGLE_AUTH_ENABLED = bool(GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET)
if PRODUCTION and not GOOGLE_AUTH_ENABLED:
    raise ImproperlyConfigured('Production requires the Google OAuth client ID and client secret.')
CSRF_TRUSTED_ORIGINS = [PUSH_ORIGIN] if PUSH_ORIGIN.startswith('https://') else []
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_SIGNUP_FIELDS = ['email*','password1*','password2*']
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_LOGOUT_REDIRECT_URL = '/'
SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_ADAPTER = 'core.oauth.PushSocialAccountAdapter'
SOCIALACCOUNT_PROVIDERS = ({
    'google': {
        'APPS': [{'client_id':GOOGLE_OAUTH_CLIENT_ID,'secret':GOOGLE_OAUTH_CLIENT_SECRET,'key':''}],
        'SCOPE':['profile','email'],
        'AUTH_PARAMS':{'access_type':'online'},
        'EMAIL_AUTHENTICATION':True,
        'EMAIL_AUTHENTICATION_AUTO_CONNECT':True,
    }
} if GOOGLE_AUTH_ENABLED else {})
# Fixed public testnet endpoints and asset identity. No secret keys are stored by Push.
STELLAR_TESTNET_HORIZON = os.environ.get('STELLAR_TESTNET_HORIZON','https://horizon-testnet.stellar.org')
STELLAR_TESTNET_USDC_ISSUER = os.environ.get('STELLAR_TESTNET_USDC_ISSUER','GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5')

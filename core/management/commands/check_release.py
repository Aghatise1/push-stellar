from urllib.parse import urlparse

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from core.stellar import _get_json


OFFICIAL_TESTNET_USDC_ISSUER = 'GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5'


class Command(BaseCommand):
    help = 'Validate protected configuration, database and Stellar testnet dependencies before deployment.'

    def add_arguments(self, parser):
        parser.add_argument('--skip-database', action='store_true', help='Check settings without opening the configured database.')
        parser.add_argument('--live-stellar', action='store_true', help='Also contact the configured Stellar Horizon server.')

    def handle(self, *args, **options):
        failures = []
        passed = []

        def require(condition, success, failure):
            if condition:
                passed.append(success)
            else:
                failures.append(failure)

        require(not settings.DEBUG, 'Django production mode is enabled.', 'PUSH_ENV must be production.')
        require(settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql',
                'PostgreSQL is configured.', 'Production must use PostgreSQL.')
        require(settings.EMAIL_DELIVERY_CONFIGURED, 'Email delivery is configured.',
                'A protected HTTPS mail API or SMTP transport and a non-local sender are required.')
        require(settings.GOOGLE_AUTH_ENABLED, 'Google OAuth is configured.',
                'Google OAuth client ID and client secret are required.')
        require(settings.PUSH_ORIGIN.startswith('https://'), 'The public origin uses HTTPS.',
                'PUSH_ORIGIN must use HTTPS.')
        require(bool(settings.ALLOWED_HOSTS) and '*' not in settings.ALLOWED_HOSTS,
                'Exact allowed hosts are configured.', 'PUSH_ALLOWED_HOSTS must not be empty or contain a wildcard.')

        horizon = urlparse(settings.STELLAR_TESTNET_HORIZON)
        require(horizon.scheme == 'https' and horizon.hostname == 'horizon-testnet.stellar.org',
                'The official Stellar testnet Horizon endpoint is configured.',
                'STELLAR_TESTNET_HORIZON must be https://horizon-testnet.stellar.org for this release.')
        require(settings.STELLAR_TESTNET_USDC_ISSUER == OFFICIAL_TESTNET_USDC_ISSUER,
                'The official Stellar testnet USDC issuer is configured.',
                'The Stellar testnet USDC issuer does not match the official issuer.')

        if not options['skip_database']:
            try:
                with connection.cursor() as cursor:
                    cursor.execute('SELECT 1')
                    cursor.fetchone()
                executor = MigrationExecutor(connection)
                pending = executor.migration_plan(executor.loader.graph.leaf_nodes())
                require(not pending, 'The database is reachable and all migrations are applied.',
                        f'The database has {len(pending)} unapplied migration(s).')
            except Exception as exc:
                failures.append(f'Database readiness failed: {type(exc).__name__}.')

        if options['live_stellar']:
            try:
                response = _get_json(settings.STELLAR_TESTNET_HORIZON.rstrip('/'))
                require(response.get('network_passphrase') == 'Test SDF Network ; September 2015',
                        'Stellar Horizon is reachable and reports testnet.',
                        'The configured Horizon server did not report the Stellar testnet passphrase.')
            except Exception as exc:
                failures.append(f'Stellar Horizon readiness failed: {type(exc).__name__}.')

        for message in passed:
            self.stdout.write(self.style.SUCCESS(f'PASS  {message}'))
        if failures:
            for message in failures:
                self.stderr.write(self.style.ERROR(f'FAIL  {message}'))
            raise CommandError(f'Release readiness failed with {len(failures)} issue(s).')

        self.stdout.write(self.style.SUCCESS('Push is configured for a Stellar testnet deployment.'))

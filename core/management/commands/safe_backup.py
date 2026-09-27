import gzip
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management import BaseCommand, call_command


class Command(BaseCommand):
    help = 'Create an ignored logical backup and prove that it restores into an isolated SQLite database.'

    def handle(self, *args, **options):
        backup_dir = Path(settings.BASE_DIR) / 'private-backups'
        backup_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        backup_path = backup_dir / f'push-{stamp}.json.gz'
        restore_db = backup_dir / f'restore-check-{stamp}.sqlite3'

        with gzip.open(backup_path, 'wt', encoding='utf-8') as output:
            call_command(
                'dumpdata',
                '--natural-foreign',
                '--natural-primary',
                '--exclude=contenttypes',
                '--exclude=auth.permission',
                '--exclude=sessions',
                stdout=output,
            )

        with gzip.open(backup_path, 'rt', encoding='utf-8') as source:
            records = json.load(source)
        if not isinstance(records, list):
            raise RuntimeError('The backup did not contain a Django record list.')

        restore_env = os.environ.copy()
        restore_env.update({
            'PUSH_ENV': 'development',
            'PUSH_DATABASE_URL': 'sqlite',
            'PUSH_SQLITE_PATH': str(restore_db),
        })
        command = [sys.executable, str(Path(settings.BASE_DIR) / 'manage.py')]
        try:
            subprocess.run(command + ['migrate', '--noinput'], env=restore_env, check=True, capture_output=True, text=True)
            subprocess.run(command + ['loaddata', str(backup_path)], env=restore_env, check=True, capture_output=True, text=True)
            subprocess.run(command + ['check'], env=restore_env, check=True, capture_output=True, text=True)
        finally:
            restore_db.unlink(missing_ok=True)

        self.stdout.write(self.style.SUCCESS(
            f'Backup created and restore-tested: {backup_path.name} ({len(records)} records)'
        ))

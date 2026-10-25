from django.core.management.base import BaseCommand, CommandError

from core.pilot_reliability import build_pilot_reliability_report


class Command(BaseCommand):
    help = 'Report read-only Push database pilot reliability metrics and attention records.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fail-on-attention',
            action='store_true',
            help='Raise CommandError if any pilot records require operator attention.',
        )

    def handle(self, *args, **options):
        report = build_pilot_reliability_report()
        deployment = report['deployment']
        agreements = report['agreement_counts']
        transactions = report['transaction_counts']

        self.stdout.write(
            'Push database records summary (does not replace Stellar ledger verification).'
        )
        self.stdout.write(f"generated_at: {report['generated_at'].isoformat()}")
        self.stdout.write(f"stale_minutes: {report['stale_minutes']}")
        self.stdout.write(
            'deployment: '
            f"tier={deployment['tier']} "
            f"release={deployment['release']} "
            f"network={deployment['network']} "
            f"testnet_only={deployment['testnet_only']} "
            f"escrow_enabled={deployment['escrow_enabled']}"
        )
        self.stdout.write(
            'agreements: '
            f"total={agreements['total']} "
            f"by_assignment_status={agreements['by_assignment_status']} "
            f"by_chain_status={agreements['by_chain_status']}"
        )
        self.stdout.write(
            'transactions: '
            f"total={transactions['total']} "
            f"prepared={transactions['prepared']} "
            f"pending={transactions['pending']} "
            f"confirmed={transactions['confirmed']} "
            f"failed={transactions['failed']} "
            f"expired={transactions['expired']}"
        )
        self.stdout.write(f"attention_total: {report['attention_total']}")

        for item in report['attention']:
            self.stdout.write(
                'attention_item: '
                f"assignment_id={item['assignment_id']} "
                f"action={item['action']} "
                f"state={item['state']} "
                f"age_seconds={item['age_seconds']} "
                f"asset={item['asset']} "
                f"amount={item['amount']} "
                f"source={item['source']} "
                f"workroom_url={item['workroom_url']}"
            )

        if options.get('fail_on_attention') and report['attention_total'] > 0:
            raise CommandError(
                f"{report['attention_total']} pilot reliability record(s) require attention."
            )

from django.db import migrations


ARTICLES=[
    ('what-is-push','What is Push?','How Push keeps independent work, delivery and settlement evidence in one record.',
     'Push is an invite-only development preview for independent work. A member can post a job, apply for work, agree scope, submit delivery evidence, communicate and preserve payment references from one account.\n\nPush does not employ either party and the current preview does not custody money. Testnet assets have no monetary value.','public'),
    ('tester-access','Tester access and account verification','How invitations, email verification and protected access work.',
     'New accounts require an email-bound invitation code. After entering the invitation, the approved email must receive and verify a six-digit code before the account is created.\n\nNever share your password, email verification code or wallet secret key. Push staff will not ask for them.','public'),
    ('work-record','The work record','What happens from a job post through delivery and review.',
     'A job records the outcome, deliverables, acceptance criteria, budget, deadline and revision rules. When a worker is selected, Push preserves an agreement snapshot so later edits cannot silently change the accepted scope.\n\nMessages, submissions, revisions, disputes and settlement evidence remain attached to that assignment.','member'),
    ('stellar-testnet','Stellar testnet payments','What the wallet and payment records do in the current preview.',
     'Push can read public Stellar testnet balances and verify a submitted testnet transaction against its destination, amount, asset and assignment memo. Push never needs a secret key.\n\nA transaction committed to the ledger cannot be recalled by an administrator. A refund requires a new signed payment. Future escrow would require a separately designed and audited smart contract.','public'),
]


def seed_articles(apps,schema_editor):
    Article=apps.get_model('core','DocumentationArticle')
    for slug,title,summary,body,audience in ARTICLES:
        Article.objects.get_or_create(slug=slug,defaults={
            'title':title,'summary':summary,'body':body,'audience':audience,'status':'published',
        })


class Migration(migrations.Migration):
    dependencies=[('core','0013_emaildelivery_auditevent_documentationarticle_and_more')]
    operations=[migrations.RunPython(seed_articles,migrations.RunPython.noop)]

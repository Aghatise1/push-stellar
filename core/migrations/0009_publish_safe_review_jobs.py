from django.db import migrations


def publish_safe_review_jobs(apps, schema_editor):
    Job = apps.get_model('core', 'Job')
    Job.objects.filter(moderation_status='review', moderation_notes='').update(moderation_status='approved')


class Migration(migrations.Migration):
    dependencies = [
        ('core', '0008_assignment_accepted_terms_at_and_more'),
    ]

    operations = [
        migrations.RunPython(publish_safe_review_jobs, migrations.RunPython.noop),
    ]

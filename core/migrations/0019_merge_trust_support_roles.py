from django.db import migrations, models


def merge_staff_roles(apps, schema_editor):
    StaffAccess = apps.get_model('core', 'StaffAccess')
    StaffAccess.objects.filter(role__in=['moderator', 'support']).update(role='trust_support')


class Migration(migrations.Migration):
    dependencies = [('core', '0018_alter_ratebucket_expires_and_more')]

    operations = [
        migrations.RunPython(merge_staff_roles, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='staffaccess',
            name='role',
            field=models.CharField(
                choices=[
                    ('owner', 'Owner'),
                    ('admin', 'Administrator'),
                    ('trust_support', 'Trust & Support'),
                ],
                default='trust_support',
                max_length=20,
            ),
        ),
    ]

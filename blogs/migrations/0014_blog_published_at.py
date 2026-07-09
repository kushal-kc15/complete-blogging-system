# Generated manually for publishing visibility correctness.

from django.db import migrations, models


def backfill_published_at(apps, schema_editor):
    Blog = apps.get_model('blogs', 'Blog')
    Blog.objects.filter(status='published', published_at__isnull=True).update(
        published_at=models.F('created_at')
    )


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0013_comment_is_visible'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RunPython(backfill_published_at, migrations.RunPython.noop),
    ]

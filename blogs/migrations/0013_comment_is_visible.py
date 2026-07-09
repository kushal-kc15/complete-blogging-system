# Generated manually for simple comment moderation.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0012_remove_blog_tags_delete_tag'),
    ]

    operations = [
        migrations.AddField(
            model_name='comment',
            name='is_visible',
            field=models.BooleanField(default=True),
        ),
    ]

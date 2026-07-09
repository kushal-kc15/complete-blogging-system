# Generated manually for article image accessibility.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blogs', '0014_blog_published_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='blog',
            name='featured_image_alt',
            field=models.CharField(blank=True, max_length=200),
        ),
    ]

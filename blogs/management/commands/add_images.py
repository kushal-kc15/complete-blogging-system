from django.core.management.base import BaseCommand
from blogs.models import Blog


class Command(BaseCommand):
    help = 'Add sample images to existing blog posts'

    def handle(self, *args, **options):
        blogs = Blog.objects.all()

        for idx, blog in enumerate(blogs):
            image_num = (idx % 10) + 1
            blog.featured_image = f'uploads/sample/blog{image_num}.jpg'
            blog.save()
            self.stdout.write(f"Added image to: {blog.title[:50]}...")

        self.stdout.write(self.style.SUCCESS(
            f'\n✓ Added images to {blogs.count()} blog posts!'))

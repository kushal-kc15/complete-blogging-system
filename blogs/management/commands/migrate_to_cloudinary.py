import os
import glob

import cloudinary.uploader
from django.conf import settings
from django.core.management.base import BaseCommand

from blogs.models import Blog, UserProfile


class Command(BaseCommand):
    help = "Upload existing local media files to Cloudinary with correct public_ids."

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._file_index = None

    def _build_file_index(self, media_root):
        """Index all files in media/ by their basename for fast lookup."""
        index = {}
        for root, dirs, files in os.walk(media_root):
            for f in files:
                full_path = os.path.join(root, f)
                basename = os.path.splitext(f)[0].lower()
                if basename not in index:
                    index[basename] = []
                index[basename].append(full_path)
        return index

    def handle(self, *args, **options):
        media_root = str(settings.MEDIA_ROOT)
        self._file_index = self._build_file_index(media_root)

        self.stdout.write("Migrating Blog featured images...")
        blogs = Blog.objects.exclude(featured_image="").exclude(featured_image__isnull=True)
        for blog in blogs:
            self._upload_field(blog, "featured_image", media_root)

        self.stdout.write("\nMigrating UserProfile avatars...")
        profiles = UserProfile.objects.exclude(avatar="").exclude(avatar__isnull=True)
        for profile in profiles:
            self._upload_field(profile, "avatar", media_root)

        self.stdout.write(self.style.SUCCESS("\nDone."))

    def _find_local_file(self, media_root, db_value):
        """Find local file matching the DB value by trying multiple strategies."""
        # Strategy 1: exact path
        exact = os.path.join(media_root, db_value)
        if os.path.isfile(exact):
            return exact

        # Strategy 2: glob with extensions (DB value might lack extension)
        stem = os.path.splitext(db_value)[0]
        pattern = os.path.join(media_root, stem + ".*")
        matches = glob.glob(pattern)
        if matches:
            return matches[0]

        # Strategy 3: try prepending "uploads/" (common mismatch)
        with_uploads = os.path.join(media_root, "uploads", db_value)
        if os.path.isfile(with_uploads):
            return with_uploads

        # Strategy 4: search by basename anywhere in media/
        basename = os.path.splitext(os.path.basename(db_value))[0].lower()
        candidates = self._file_index.get(basename, [])
        if candidates:
            return candidates[0]

        return None

    def _upload_field(self, instance, field_name, media_root):
        field_value = getattr(instance, field_name)
        db_value = str(field_value)

        local_path = self._find_local_file(media_root, db_value)
        if not local_path:
            self.stdout.write(self.style.WARNING(
                f"  SKIP (not found): {db_value}"
            ))
            return

        # The URL resolver does: _prepend_prefix(db_value) -> "media/{db_value}"
        # Then CloudinaryResource("media/{db_value}") generates the URL.
        # For images, Cloudinary public_id must NOT have the extension.
        name_no_ext = os.path.splitext(db_value)[0]
        public_id = f"media/{name_no_ext}"

        try:
            result = cloudinary.uploader.upload(
                local_path,
                public_id=public_id,
                resource_type="image",
                overwrite=True,
            )
            self.stdout.write(self.style.SUCCESS(
                f"  OK: {db_value} -> {result['secure_url']}"
            ))
        except Exception as e:
            self.stdout.write(self.style.ERROR(
                f"  FAIL: {db_value} — {e}"
            ))

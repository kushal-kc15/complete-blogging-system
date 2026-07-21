from pathlib import Path
import warnings

from django.core.exceptions import ValidationError
from PIL import Image, UnidentifiedImageError


MAX_IMAGE_SIZE = 5 * 1024 * 1024
MAX_IMAGE_WIDTH = 5000
MAX_IMAGE_HEIGHT = 5000
ALLOWED_IMAGE_FORMATS = {'JPEG', 'PNG', 'WEBP'}
ALLOWED_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
ALLOWED_IMAGE_MIME_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
FORMAT_EXTENSIONS = {
    'JPEG': {'.jpg', '.jpeg'},
    'PNG': {'.png'},
    'WEBP': {'.webp'},
}


def validate_image_upload(upload):
    """Validate user-uploaded images without trusting client metadata."""
    suffixes = [suffix.lower() for suffix in Path(upload.name).suffixes]
    if len(suffixes) != 1 or suffixes[0] not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValidationError('Upload a JPEG, PNG, or WebP image with a valid extension.')

    if upload.size > MAX_IMAGE_SIZE:
        raise ValidationError('Image must be 5 MB or smaller.')

    content_type = getattr(upload, 'content_type', '')
    if content_type and content_type.lower() not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError('Upload a JPEG, PNG, or WebP image.')

    try:
        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                image.verify()

        upload.seek(0)
        with warnings.catch_warnings():
            warnings.simplefilter('error', Image.DecompressionBombWarning)
            with Image.open(upload) as image:
                image.load()
                image_format = image.format
                width, height = image.size
    except (Image.DecompressionBombWarning, Image.DecompressionBombError):
        raise ValidationError('Image could not be processed safely.')
    except (UnidentifiedImageError, OSError, ValueError):
        raise ValidationError('Upload a valid, non-corrupted JPEG, PNG, or WebP image.')
    finally:
        upload.seek(0)

    extension = suffixes[0]
    if (
        image_format not in ALLOWED_IMAGE_FORMATS or
        extension not in FORMAT_EXTENSIONS[image_format]
    ):
        raise ValidationError('Image content must match its JPEG, PNG, or WebP extension.')

    if width > MAX_IMAGE_WIDTH or height > MAX_IMAGE_HEIGHT:
        raise ValidationError('Image dimensions must not exceed 5000 × 5000 pixels.')

    return upload

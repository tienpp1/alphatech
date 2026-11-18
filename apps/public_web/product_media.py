"""Serve only validated, referenced public product images from local storage."""
import io
import re

from django.http import FileResponse, Http404
from PIL import Image, UnidentifiedImageError

from apps.retail.models import ProductImage, ProductImageContent


def product_image(request, image_path):
    if not re.fullmatch(r"products/\d{4}/\d{2}/[0-9a-f]{32}\.(?:jpg|jpeg|png|webp)", image_path):
        raise Http404
    if not ProductImage.objects.filter(image=image_path, product__deleted_at__isnull=True).exists():
        raise Http404
    field = ProductImage._meta.get_field("image")
    try:
        stored = ProductImageContent.objects.filter(image__image=image_path,
            image__product__deleted_at__isnull=True).values_list("content", flat=True).first()
        handle = io.BytesIO(bytes(stored)) if stored is not None else field.storage.open(image_path, "rb")
        with Image.open(handle) as image:
            content_type = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}.get(image.format)
        if not content_type:
            handle.close()
            raise Http404
        handle.seek(0)
    except (OSError, ValueError, UnidentifiedImageError):
        raise Http404 from None
    response = FileResponse(handle, content_type=content_type)
    response["X-Content-Type-Options"] = "nosniff"
    return response

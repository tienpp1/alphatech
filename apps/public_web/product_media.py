"""Serve only validated, referenced public product images from local storage."""
import io
import re

from django.http import FileResponse, Http404, HttpResponse
from PIL import Image, UnidentifiedImageError

from apps.retail.models import ProductImage, ProductImageContent


MISSING_IMAGE = b'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 280" role="img" aria-label="Anh san pham khong con, vui long tai lai"><rect width="480" height="280" fill="#111827"/><rect x="190" y="55" width="100" height="75" rx="8" fill="none" stroke="#94a3b8" stroke-width="5"/><circle cx="219" cy="78" r="9" fill="#94a3b8"/><path d="M200 118l25-26 20 20 15-15 20 21" fill="none" stroke="#94a3b8" stroke-width="5"/><text x="240" y="175" text-anchor="middle" font-family="sans-serif" font-size="22" fill="#e2e8f0">Anh khong con</text><text x="240" y="207" text-anchor="middle" font-family="sans-serif" font-size="18" fill="#94a3b8">Vui long tai lai anh san pham</text></svg>'''


def missing_image():
    response = HttpResponse(MISSING_IMAGE, content_type="image/svg+xml")
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["Content-Security-Policy"] = "default-src 'none'; style-src 'none'; sandbox"
    return response


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
        return missing_image()
    response = FileResponse(handle, content_type=content_type)
    response["X-Content-Type-Options"] = "nosniff"
    return response

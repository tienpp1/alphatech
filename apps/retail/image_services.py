"""
Product Image Services for Secure File Validation, Storage, and Management.
"""

import os
import uuid
from typing import List, Optional
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from PIL import Image

from apps.retail.models import Product, ProductImage

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_IMAGE_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024  # 5 MB


def validate_product_image_file(uploaded_file) -> None:
    """
    Validates uploaded product image against extension, file size, MIME type, and Pillow integrity.
    Rejects scripts, executables, corrupted files, and oversized uploads.
    """
    if not uploaded_file:
        raise ValidationError("Không có tệp ảnh nào được cung cấp.")

    # 1. Size Validation
    if uploaded_file.size > MAX_IMAGE_SIZE_BYTES:
        max_mb = MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(f"Kích thước tệp ảnh ({uploaded_file.size / (1024*1024):.1f} MB) vượt quá giới hạn cho phép ({max_mb} MB).")

    # 2. Extension Validation
    filename = uploaded_file.name or ""
    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower not in ALLOWED_IMAGE_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise ValidationError(f"Định dạng tệp '{ext}' không được hỗ trợ. Chỉ chấp nhận các định dạng ảnh: {allowed_str}.")

    # 3. Content Type Validation (if provided by client)
    content_type = getattr(uploaded_file, "content_type", "").lower()
    if content_type and content_type not in ALLOWED_IMAGE_MIME_TYPES:
        raise ValidationError(f"Loại nội dung '{content_type}' không hợp lệ cho tệp hình ảnh.")

    # 4. Pillow Image Integrity & Format Verification
    try:
        # Read a portion or the whole stream to verify with Pillow
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        img.verify()
        uploaded_file.seek(0)
    except Exception as e:
        raise ValidationError("Tệp tin bị lỗi hoặc không phải là hình ảnh hợp lệ.")


def generate_safe_image_filename(original_filename: str) -> str:
    """
    Generates a secure UUID-based filename preserving only the sanitized lowercase extension.
    Prevents path traversal, special characters, and remote execution vectors.
    """
    _, ext = os.path.splitext(original_filename or "")
    ext_lower = ext.lower() if ext else ".jpg"
    if ext_lower not in ALLOWED_IMAGE_EXTENSIONS:
        ext_lower = ".jpg"
    return f"{uuid.uuid4().hex}{ext_lower}"


@transaction.atomic
def save_product_image(
    workspace,
    product: Product,
    uploaded_file,
    alt_text: str = "",
    is_primary: bool = False,
    sort_order: Optional[int] = None,
) -> ProductImage:
    """
    Validates and stores a product image with automatic primary management.
    """
    validate_product_image_file(uploaded_file)

    # Sanitize and assign safe filename
    safe_name = generate_safe_image_filename(uploaded_file.name)
    uploaded_file.name = safe_name

    existing_images_count = ProductImage.objects.filter(product=product).count()

    # If first image or explicitly marked primary, manage primary state
    if existing_images_count == 0:
        is_primary = True

    if is_primary:
        ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)

    if sort_order is None:
        sort_order = existing_images_count

    product_image = ProductImage.objects.create(
        workspace=workspace,
        product=product,
        image=uploaded_file,
        sort_order=sort_order,
        is_primary=is_primary,
        alt_text=alt_text or product.name,
    )
    return product_image


@transaction.atomic
def set_primary_product_image(product: Product, product_image: ProductImage) -> None:
    """
    Sets the specified image as the primary image for the product.
    """
    if product_image.product_id != product.id:
        raise ValidationError("Hình ảnh không thuộc về sản phẩm này.")

    ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
    product_image.is_primary = True
    product_image.save(update_fields=["is_primary", "updated_at"])


@transaction.atomic
def delete_product_image(product_image: ProductImage) -> None:
    """
    Safely deletes a product image record and its associated physical file.
    If the deleted image was primary, promotes another image as primary.
    """
    product = product_image.product
    was_primary = product_image.is_primary

    # Delete physical media file safely
    try:
        if product_image.image and hasattr(product_image.image, "path") and os.path.isfile(product_image.image.path):
            product_image.image.delete(save=False)
    except Exception:
        pass

    product_image.delete()

    # If was primary, promote the next image
    if was_primary:
        next_image = ProductImage.objects.filter(product=product).order_by("sort_order", "created_at").first()
        if next_image:
            next_image.is_primary = True
            next_image.save(update_fields=["is_primary", "updated_at"])

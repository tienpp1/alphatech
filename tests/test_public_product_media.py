import io
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings
from PIL import Image


@override_settings(DEBUG=False)
class PublicProductMediaTests(SimpleTestCase):
    def test_referenced_image_is_served_with_debug_off(self):
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2)).save(buffer, format="PNG")
        data = buffer.getvalue()
        url = "/media/products/2026/11/" + "a" * 32 + ".png"
        with (patch("apps.public_web.product_media.ProductImage.objects.filter") as query,
              patch("apps.public_web.product_media.ProductImageContent.objects.filter") as content,
              patch("apps.public_web.product_media.ProductImage._meta.get_field") as field):
            query.return_value.exists.return_value = True
            content.return_value.values_list.return_value.first.return_value = None
            field.return_value.storage.open.return_value = io.BytesIO(data)
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response["Content-Type"], "image/png")
            self.assertEqual(b"".join(response.streaming_content), data)

    def test_database_image_survives_missing_local_file(self):
        buffer = io.BytesIO()
        Image.new("RGB", (2, 2)).save(buffer, format="PNG")
        data = buffer.getvalue()
        url = "/media/products/2026/11/" + "a" * 32 + ".png"
        with (patch("apps.public_web.product_media.ProductImage.objects.filter") as query,
              patch("apps.public_web.product_media.ProductImageContent.objects.filter") as content,
              patch("apps.public_web.product_media.ProductImage._meta.get_field") as field):
            query.return_value.exists.return_value = True
            content.return_value.values_list.return_value.first.return_value = data
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b"".join(response.streaming_content), data)
            field.return_value.storage.open.assert_not_called()

    def test_unreferenced_and_other_media_are_not_served(self):
        with patch("apps.public_web.product_media.ProductImage.objects.filter") as query:
            query.return_value.exists.return_value = False
            self.assertEqual(self.client.get("/media/products/2026/11/" + "a" * 32 + ".png").status_code, 404)
            self.assertEqual(self.client.get("/media/private/document.pdf").status_code, 404)

    def test_missing_referenced_legacy_image_shows_uncached_placeholder(self):
        url = "/media/products/2026/11/" + "a" * 32 + ".png"
        with (patch("apps.public_web.product_media.ProductImage.objects.filter") as query,
              patch("apps.public_web.product_media.ProductImageContent.objects.filter") as content,
              patch("apps.public_web.product_media.ProductImage._meta.get_field") as field):
            query.return_value.exists.return_value = True
            content.return_value.values_list.return_value.first.return_value = None
            field.return_value.storage.open.side_effect = FileNotFoundError()
            response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/svg+xml')
        self.assertIn('no-store', response['Cache-Control'])
        self.assertIn(b'Vui long tai lai anh', response.content)

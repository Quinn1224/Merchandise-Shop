import shutil
import tempfile
from decimal import Decimal
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from captcha.models import CaptchaStore

from .models import (
    Color,
    CustomizationOption,
    EmailTemplate,
    Order,
    Product,
    ProductVariant,
    Size,
)


class OrderWorkflowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._temp_media_dir = tempfile.mkdtemp(prefix='merchandise_shop_test_media_')
        cls._override_media = override_settings(MEDIA_ROOT=cls._temp_media_dir)
        cls._override_media.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override_media.disable()
        shutil.rmtree(cls._temp_media_dir, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.product = Product.objects.create(
            name='Team Hoodie',
            slug='team-hoodie',
            description='Komfortables Team-Produkt.',
            price=Decimal('29.99'),
            image=SimpleUploadedFile(
                'hoodie.jpg',
                b'fake-image-content',
                content_type='image/jpeg',
            ),
        )
        self.size = Size.objects.create(name='M')
        self.color = Color.objects.create(name='Navy', hex_code='#1f2a44')
        self.variant = ProductVariant.objects.create(
            product=self.product,
            size=self.size,
            color=self.color,
        )
        self.customization = CustomizationOption.objects.create(
            product=self.product,
            name='Name',
            option_type='text',
            required=False,
            price=Decimal('2.50'),
        )
        self.email_template = EmailTemplate.objects.create(
            name='Bestellung',
            template_type='order_confirmation',
            subject='Bestellung {{ order.id }}',
            txt_content='Vielen Dank für deine Bestellung, {{ order.full_name }}.',
            html_content='<p>Vielen Dank für deine Bestellung, {{ order.full_name }}.</p>',
            active=True,
        )

    def add_product_to_cart(self):
        response = self.client.post(
            reverse('merchandiseshop:product_detail', args=[self.product.slug]),
            {
                'quantity': 2,
                'variant_id': self.variant.id,
                f'option_{self.customization.id}': 'Max',
            },
        )
        self.assertRedirects(response, reverse('merchandiseshop:cart_detail'))

    def get_captcha_data(self, response='abcde'):
        hashkey = CaptchaStore.generate_key()
        captcha = CaptchaStore.objects.get(hashkey=hashkey)
        captcha.response = response
        captcha.save(update_fields=['response'])
        return {
            'captcha_hashkey': hashkey,
            'captcha_response': response,
        }

    def checkout_data(self, **overrides):
        data = {
            'full_name': 'Max Mustermann',
            'email': 'max@example.com',
            'notes': 'Bitte schnell versenden.',
            'privacy_accepted': 'on',
        }
        data.update(self.get_captcha_data())
        data.update(overrides)
        return data

    def test_add_to_cart_and_checkout_creates_order(self):
        self.add_product_to_cart()
        response = self.client.get(reverse('merchandiseshop:checkout'))
        self.assertEqual(response.status_code, 200)

        cart = self.client.session.get('cart', {})
        self.assertEqual(
            len(cart),
            1,
            f'Schritt 2/5: Erwartet wurde genau ein Warenkorb-Artikel, erhalten: {cart!r}',
        )
        item = next(iter(cart.values()))
        self.assertEqual(
            item['product_id'],
            self.product.id,
            f'Schritt 2/5: Falsches Produkt im Warenkorb: {item!r}',
        )
        self.assertEqual(
            item['quantity'],
            2,
            f'Schritt 2/5: Falsche Menge im Warenkorb: {item!r}',
        )
        self.assertEqual(
            item['customizations'],
            {'Name': 'Max'},
            f'Schritt 2/5: Falsche Personalisierung im Warenkorb: {item!r}',
        )

        with patch('merchandiseshop.views.EmailMultiAlternatives.send') as mock_send:
            checkout_response = self.client.post(
                reverse('merchandiseshop:checkout'),
                self.checkout_data(),
            )

        self.assertEqual(
            checkout_response.status_code,
            200,
            'Schritt 3/5: Der Checkout muss erfolgreich mit HTTP 200 antworten.',
        )
        actual_templates = [
            template.name for template in checkout_response.templates if template.name
        ]
        self.assertTemplateUsed(
            checkout_response,
            'merchandiseshop/order_success.html',
            msg_prefix=(
                'Schritt 3/5: Nach erfolgreichem Checkout wurde nicht die Erfolgsseite '
                f'gerendert. Gerenderte Templates: {actual_templates!r}. '
                'Prüfe, ob ein aktives order_confirmation-E-Mail-Template vorhanden ist.'
            ),
        )

        order = Order.objects.get(full_name='Max Mustermann', email='max@example.com')
        self.assertEqual(
            order.total_price,
            Decimal('59.98'),
            f'Schritt 4/5: Falscher Bestellgesamtbetrag für Bestellung #{order.id}.',
        )
        self.assertEqual(
            order.items.count(),
            1,
            f'Schritt 4/5: Bestellung #{order.id} enthält nicht genau eine Position.',
        )
        order_item = order.items.get()
        self.assertEqual(
            order_item.variant,
            self.variant,
            f'Schritt 4/5: Falsche Variante in Bestellung #{order.id}.',
        )
        self.assertEqual(
            order_item.quantity,
            2,
            f'Schritt 4/5: Falsche Menge in Bestellung #{order.id}.',
        )
        self.assertEqual(
            order_item.customization_details,
            {'Name': 'Max'},
            f'Schritt 4/5: Falsche Personalisierung in Bestellung #{order.id}.',
        )
        self.assertEqual(
            self.client.session.get('cart', {}),
            {},
            f'Schritt 5/5: Der Warenkorb wurde nach Bestellung #{order.id} nicht geleert.',
        )
        # The template is now loaded from the database and may result in more
        # than one send invocation depending on the configured notifications.
        self.assertTrue(
            mock_send.called,
            f'Schritt 5/5: Für Bestellung #{order.id} wurde keine E-Mail versendet.',
        )

    def test_checkout_redirects_when_cart_is_empty(self):
        response = self.client.get(reverse('merchandiseshop:checkout'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'merchandiseshop/checkout.html')
        self.assertTrue(response.context['captcha_hashkey'])
        self.assertTrue(
            CaptchaStore.objects.filter(
                hashkey=response.context['captcha_hashkey']
            ).exists()
        )

    def test_checkout_does_not_create_order_without_privacy_consent(self):
        self.add_product_to_cart()
        checkout_data = self.checkout_data()
        checkout_data.pop('privacy_accepted')

        checkout_response = self.client.post(
            reverse('merchandiseshop:checkout'),
            checkout_data,
        )

        self.assertEqual(checkout_response.status_code, 200)
        self.assertTemplateUsed(checkout_response, 'merchandiseshop/checkout.html')
        self.assertContains(
            checkout_response,
            'Bitte akzeptiere die Datenschutzerklärung.',
        )
        self.assertContains(checkout_response, 'Max Mustermann')
        self.assertEqual(Order.objects.count(), 0)

    def test_checkout_does_not_create_order_with_invalid_captcha(self):
        self.add_product_to_cart()

        checkout_response = self.client.post(
            reverse('merchandiseshop:checkout'),
            self.checkout_data(captcha_response='falsch'),
        )

        self.assertEqual(checkout_response.status_code, 200)
        self.assertTemplateUsed(checkout_response, 'merchandiseshop/checkout.html')
        self.assertContains(
            checkout_response,
            'Die Sicherheitsabfrage war falsch. Bitte erneut versuchen.',
        )
        self.assertContains(checkout_response, 'Max Mustermann')
        self.assertEqual(Order.objects.count(), 0)

    def test_cart_remove_removes_selected_item(self):
        detail_url = reverse('merchandiseshop:product_detail', args=[self.product.slug])
        self.client.post(
            detail_url,
            {
                'quantity': 1,
                'variant_id': self.variant.id,
            },
        )

        cart = self.client.session.get('cart', {})
        self.assertEqual(len(cart), 1)
        item_id = next(iter(cart.keys()))

        response = self.client.post(reverse('merchandiseshop:cart_remove', args=[item_id]))

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('merchandiseshop:cart_detail'))
        self.assertEqual(self.client.session.get('cart', {}), {})

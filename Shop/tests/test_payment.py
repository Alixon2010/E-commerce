# python
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch
import json

from django.contrib.auth import get_user_model
from Shop.models import Product, Card, Transaction, Order

User = get_user_model()


class TestToOrderView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="u1", email="u1@example.com", password="pass123")
        # product
        self.product = Product.objects.create(name="p1", price=10.0, stock=10)
        # create card and add product to it (uses related manager card_products)
        self.card = Card.objects.create(user=self.user)
        try:
            # ожидается наличие related manager card.card_products
            self.card.card_products.create(product=self.product, quantity=1)
        except Exception:
            # в случае нестандартной реализации -- попытка через полёп интерфейс может быть иной,
            # но для большинства проектов это сработает
            pass

    @patch("stripe.PaymentIntent.create")
    def test_create_intent_and_transaction(self, mock_create):
        # Мокаем ответ Stripe PaymentIntent.create
        mock_create.return_value = type("PI", (), {
            "id": "pi_test_123",
            "client_secret": "cs_test_123",
            "status": "requires_payment_method"
        })()

        self.client.force_authenticate(user=self.user)
        url = reverse("to-order")
        data = {"latitude": 41.31, "longitude": 69.28}
        resp = self.client.post(url, data, format="json")
        assert resp.status_code == 200, resp.content
        body = resp.json()
        assert "clientSecret" in body and body["clientSecret"] == "cs_test_123"

        # Проверяем создание Transaction
        tx = Transaction.objects.filter(stripe_payment_intent="pi_test_123").first()
        assert tx is not None
        assert tx.status == "requires_payment_method"


class TestStripeWebhookView(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="wuser", email="w@example.com", password="pass123")
        # создаём order и transaction связанный со stripe intent id
        self.order = Order.objects.create(user=self.user, latitude=41.0, longitude=69.0, stripe_payment_intent="pi_web_1", paid=False)
        self.tx = Transaction.objects.create(user=self.user, order=self.order, stripe_payment_intent="pi_web_1", amount=100.0, currency="usd", status="requires_payment_method")

    @patch("stripe.Webhook.construct_event")
    def test_webhook_payment_succeeded(self, mock_construct):
        # Подготавливаем событие succeeded
        event = {"type": "payment_intent.succeeded", "data": {"object": {"id": "pi_web_1"}}}
        mock_construct.return_value = event

        url = reverse("stripe-webhook")
        payload = json.dumps(event).encode()
        resp = self.client.post(url, data=payload, content_type="application/json", HTTP_STRIPE_SIGNATURE="t")
        assert resp.status_code == 200
        assert resp.json().get("status") == "success"

        # Проверяем, что order отмечен как оплачен, а транзакция обновлена
        self.order.refresh_from_db()
        self.tx.refresh_from_db()
        assert self.order.paid is True
        assert self.tx.status == "success"

    @patch("stripe.Webhook.construct_event")
    def test_webhook_payment_failed(self, mock_construct):
        event = {"type": "payment_intent.payment_failed", "data": {"object": {"id": "pi_web_1"}}}
        mock_construct.return_value = event

        url = reverse("stripe-webhook")
        payload = json.dumps(event).encode()
        resp = self.client.post(url, data=payload, content_type="application/json", HTTP_STRIPE_SIGNATURE="t")
        assert resp.status_code == 200
        assert resp.json().get("status") == "failed"

        self.tx.refresh_from_db()
        assert self.tx.status == "failed"

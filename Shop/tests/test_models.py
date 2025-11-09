from decimal import Decimal
from django.test import TestCase
from django.contrib.auth import get_user_model
from Shop import models

User = get_user_model()


class TestModels(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username="testuser", email="test@example.com", password="pass1234")
        self.profile = models.Profile.objects.create(user=self.user, phone="998901234567")

        self.category = models.Category.objects.create(name="Electronics")

        self.product = models.Product.objects.create(
            category=self.category,
            name="Phone",
            description="Very good phone",
            price=Decimal("100.00"),
            stock=10,
            discount_percent=10
        )

        self.card = models.Card.objects.create(user=self.user)

    def test_profile_created(self):
        self.assertEqual(self.profile.user.username, "testuser")

    def test_category_str(self):
        self.assertEqual(str(self.category), "Electronics")

    def test_product_discount_logic(self):
        correct_price = self.product.price * (Decimal(1) - (Decimal(self.product.discount_percent) / Decimal(100)))
        self.assertEqual(self.product.get_total_price(), correct_price)

    def test_card_add_and_remove(self):
        added = self.card.to_card(self.product, quantity=2)
        self.assertTrue(added)
        self.assertEqual(self.product.stock, 8)
        self.assertEqual(self.card.card_products.count(), 1)

        removed = self.card.remove_card(self.product, quantity=1)
        self.assertTrue(removed)
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 9)

    def test_order_creation(self):
        order = models.Order.objects.create(
            user=self.user,
            latitude=41.3,
            longitude=69.2
        )
        models.OrderedProduct.objects.create(order=order, product=self.product, quantity=2)
        total = sum(item.total_price for item in order.products.all())
        self.assertEqual(order.total_price, total)

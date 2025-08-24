import uuid

from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models, transaction
from django.db.models import UUIDField

User = get_user_model()

class Profile(models.Model):
    user = models.OneToOneField(User, related_name='profile', on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, unique=True)
    img = models.ImageField(upload_to='profile', blank=True, null=True)
    reset_code = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}: {self.phone}"


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='sub_categories')
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Product(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.SET_NULL, null=True, related_name='products')
    name = models.CharField(max_length=100)
    description = models.TextField(validators=[validators.MinLengthValidator(10), validators.MaxLengthValidator(4000)])
    price = models.DecimalField(max_digits=12, decimal_places=2)
    stock = models.IntegerField(default=0)

    def __str__(self):
        return self.name


class Card(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='card', )

    @property
    def total_price(self):
        return sum(item.total_price for item in self.card_products.all())

    def to_card(self, product, quantity = 1):

        if product.stock < quantity:
            return False

        with transaction.atomic():
            product.stock -= quantity
            product.save()

            card_product, created = CardProduct.objects.get_or_create(card=self, product=product)

            if created:
                card_product.quantity = quantity
            else:
                card_product.quantity += quantity

            card_product.save()

        return True

    def remove_card(self, product, quantity = None):
        try:
            card_product = CardProduct.objects.get(card=self, product=product)
        except CardProduct.DoesNotExist:
            return False

        with transaction.atomic():
            if quantity is None or quantity >= card_product.quantity:
                product.stock += card_product.quantity
                card_product.delete()
            else:
                card_product.quantity -= quantity
                product.stock += quantity
                card_product.save()

            product.save()

        return True

    def __str__(self):
        return f"{self.user.username}'s Card"


class CardProduct(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='card_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

class Order(models.Model):
    STATUS_CHOICES = [
        ("pending", "Kutilmoqda"),
        ("paid", "To'langan"),
        ("shipped", "Yuborilgan"),
        ("delivered", "Yetkazilgan"),
        ("canceled", "Bekor qilingan"),
    ]

    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True,related_name='orders')

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum(item.total_price for item in self.products.all())

class OrderedProduct(models.Model):
    id = UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.quantity * self.product.price

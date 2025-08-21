import uuid

from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models

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

    def to_card(self, product, quantity = 1):

        if product.stock < quantity:
            return False


        product.stock -= quantity
        product.save()

        card_product, created = CardProduct.objects.get_or_create(card=self, product=product)

        if created:
            card_product.quantity = quantity
        else:
            card_product.quantity += quantity

        card_product.save()

        return True

    def remove_card(self, product):
        try:
            card_product = CardProduct.objects.get(card=self, product=product)
        except CardProduct.DoesNotExist:
            return False

        product.stock += card_product.quantity
        card_product.delete()
        product.save()

        return True


class CardProduct(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='card_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

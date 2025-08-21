import uuid

from django.contrib.auth import get_user_model
from django.core import validators
from django.db import models
from rest_framework.exceptions import ValidationError

User = get_user_model()


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

    def to_card(self, product, quantity):

        if product.stock < quantity:
            return False


        product.stock -= quantity
        product.save()

        card_product, created = CardProduct.objects.get_or_create(card=self, product=product)


        card_product.quantity += quantity
        card_product.save()

        return True

    def remove_card(self, product, quantity):
        try:
            card_product = CardProduct.objects.get(card=self, product=product)
        except CardProduct.DoesNotExist:
            raise ValueError("Продукт не в корзине")

        if quantity > card_product.quantity:
            raise ValueError("")

            # вернуть товар на склад
        product.stock += quantity
        product.save()

        # уменьшить количество в корзине
        card_product.quantity -= quantity
        if card_product.quantity <= 0:
            card_product.delete()
        else:
            card_product.save()


class CardProduct(models.Model):
    card = models.ForeignKey(Card, on_delete=models.CASCADE, related_name='card_products')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

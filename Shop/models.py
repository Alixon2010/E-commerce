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
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from Shop import models

admin.site.register(
    [
        models.Category,
        models.Product,
        models.Card,
        models.CardProduct,
        models.Order,
        models.OrderedProduct,
    ]
)


@admin.register(models.User)
class UserAdmin(BaseUserAdmin):
    pass

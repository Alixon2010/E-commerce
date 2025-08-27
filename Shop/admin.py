from django.contrib import admin

from Shop import models

admin.site.register([models.SubCategory, models.Category, models.Product, models.Card, models.CardProduct, models.Order, models.OrderedProduct])

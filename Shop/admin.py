from django.contrib import admin

from Shop import models

<<<<<<< HEAD
admin.site.register([models.SubCategory, models.Category, models.Product])
=======
admin.site.register([models.SubCategory, models.Category, models.Product, models.Card, models.CardProduct, models.Order, models.OrderedProduct])
>>>>>>> main

from django.contrib import admin

from Shop import models

admin.site.register([models.SubCategory, models.Category, models.Product])
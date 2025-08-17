from django.urls import path
from rest_framework.routers import DefaultRouter

from Shop import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet)
router.register('subcategories', views.SubCategoryViewSet)
router.register('products', views.ProductViewSet)

urlpatterns = [

]

urlpatterns += router.urls
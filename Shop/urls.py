from django.urls import path
from rest_framework.routers import DefaultRouter

from Shop import views

router = DefaultRouter()
router.register('categories', views.CategoryViewSet)
router.register('subcategories', views.SubCategoryViewSet)
router.register('products', views.ProductViewSet)

urlpatterns = [
    path('register/', views.Register.as_view()),
    path('users/', views.UserList.as_view())
]

urlpatterns += router.urls
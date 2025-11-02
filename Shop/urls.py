from django.urls import path
from rest_framework.routers import DefaultRouter

from Shop import views
from Shop.views import OrderListView, OrderRetrieveView

router = DefaultRouter()
router.register("categories", views.CategoryViewSet)
router.register("subcategories", views.SubCategoryViewSet)
router.register("products", views.ProductViewSet)

urlpatterns = [
    path("register/", views.Register.as_view()),
    path("users/", views.UserList.as_view()),
    path("logout/", views.Logout.as_view()),
    path("reset_password/", views.ResetPassword.as_view()),
    path("reset_password/confirm/", views.ResetPasswordConfirm.as_view()),
    path("to_card/", views.ToCardView.as_view()),
    path("remove_card/", views.RemoveCardView.as_view()),
    path("to_order/", views.ToOrderView.as_view()),
    path("change_order_status/", views.ChangeOrderStatus.as_view()),
    path("orders/", OrderListView.as_view()),
    path("orders/<uuid:pk>/", OrderRetrieveView.as_view()),
    path("card/", views.CardListView.as_view()),
    path("card/<uuid:pk>", views.CardRetriveView.as_view()),
]

urlpatterns += router.urls

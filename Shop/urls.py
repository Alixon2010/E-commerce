from django.urls import path
from rest_framework.routers import DefaultRouter

from Shop import views
from Shop.views import OrderListView, OrderRetrieveView

router = DefaultRouter()
router.register("categories", views.CategoryViewSet, basename="category")
router.register("products", views.ProductViewSet, basename="product")

urlpatterns = [
    path("register/", views.Register.as_view(), name="register"),
    path("users/", views.UserList.as_view(), name="user-list"),
    path("logout/", views.Logout.as_view(), name="logout"),
    path("reset_password/", views.ResetPassword.as_view(), name="reset-password"),
    path(
        "reset_password/confirm/",
        views.ResetPasswordConfirm.as_view(),
        name="reset-password-confirm",
    ),
    path("to_card/", views.ToCardView.as_view(), name="to-card"),
    path("remove_card/", views.RemoveCardView.as_view(), name="remove-card"),
    path("to_order/", views.ToOrderView.as_view(), name="to-order"),
    path(
        "change_order_status/",
        views.ChangeOrderStatus.as_view(),
        name="change-order-status",
    ),
    path("orders/", OrderListView.as_view(), name="order-list"),
    path("orders/<uuid:pk>/", OrderRetrieveView.as_view(), name="order-detail"),
    path("card/", views.CardListView.as_view(), name="card-list"),
    path("card/<uuid:pk>/", views.CardRetriveView.as_view(), name="card-detail"),
]

urlpatterns += router.urls

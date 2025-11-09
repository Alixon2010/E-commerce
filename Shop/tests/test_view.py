import uuid

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from Shop import models


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="user", email="user@test.com", password="1234"
    )


@pytest.fixture
def staff_user(db, django_user_model):
    return django_user_model.objects.create_user(
        username="admin", email="admin@test.com", password="1234", is_staff=True
    )


@pytest.fixture
def category(db):
    return models.Category.objects.create(name="Phone")


@pytest.fixture
def product(db, category):
    return models.Product.objects.create(category=category, name="iPhone", price=1000)


@pytest.fixture
def card(db, user):
    return models.Card.objects.create(user=user)


@pytest.mark.django_db
class TestCategoryViewSet:
    def test_list_categories(self, api_client, category):
        url = reverse("category-list")
        resp = api_client.get(url)
        assert resp.status_code == 200
        assert len(resp.data) > 0

    def test_create_category(self, api_client):
        url = reverse("category-list")
        resp = api_client.post(url, {"name": "Laptop"})
        assert resp.status_code == status.HTTP_201_CREATED


@pytest.mark.django_db
class TestProductViewSet:
    def test_list_products(self, api_client, product):
        url = reverse("product-list")
        resp = api_client.get(url)
        assert resp.status_code == 200

    def test_create_product(self, api_client, category):
        url = reverse("product-list")
        data = {
            "category": category.id,
            "name": "Macbook",
            "price": "2000",
            "description": "jfiowaugbrbagteahoetahniteahinteaihnteinhteahptehptehtephipte",
        }
        resp = api_client.post(url, data)
        assert resp.status_code == 201


@pytest.mark.django_db
class TestRegister:
    def test_register_user(self, api_client):
        url = reverse("register")
        data = {
            "username": "new",
            "email": "new@test.com",
            "password": "1234",
            "password_confirm": "1234",
            "profile": {"phone": "950748830"},
        }
        resp = api_client.post(url, data, format="json")
        assert resp.status_code == 201


@pytest.mark.django_db
class TestUserList:
    def test_list_users_staff_only(self, api_client, staff_user):
        api_client.force_authenticate(staff_user)
        url = reverse("user-list")
        resp = api_client.get(url)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestLogout:
    def test_logout(self, api_client, user):
        api_client.force_authenticate(user)
        url = reverse("logout")
        resp = api_client.post(url)
        assert resp.status_code == 200
        assert resp.data["message"] == "User logged out!"


@pytest.mark.django_db
class TestResetPassword:
    def test_reset_password_request(self, api_client, user):
        url = reverse("reset-password")
        data = {"email": user.email}
        resp = api_client.post(url, data)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestResetPasswordConfirm:
    def test_confirm_reset(self, api_client):
        url = reverse("reset-password-confirm")
        data = {"uid": "fakeuid", "token": "faketoken", "new_password": "12345"}
        resp = api_client.post(url, data)
        assert resp.status_code == 200 or resp.status_code == 400


@pytest.mark.django_db
class TestCardListView:
    def test_card_list_staff(self, api_client, staff_user, card):
        api_client.force_authenticate(staff_user)
        url = reverse("card-list")
        resp = api_client.get(url)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestCardRetrieveView:
    def test_retrieve_card_owner(self, api_client, user, card):
        api_client.force_authenticate(user)
        url = reverse("card-detail", args=[card.id])
        resp = api_client.get(url)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestToCardView:
    def test_add_product_to_card(self, api_client, user, product):
        api_client.force_authenticate(user)
        url = reverse("to-card")
        data = {"product_id": product.id, "quantity": 1}
        resp = api_client.post(url, data)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestRemoveCardView:
    def test_remove_from_card(self, api_client, user, product):
        api_client.force_authenticate(user)
        url = reverse("remove-card")
        data = {"product_id": product.id}
        resp = api_client.post(url, data)
        assert resp.status_code in [200, 400]


@pytest.mark.django_db
class TestToOrderView:
    def test_create_order(self, api_client, user, product):
        api_client.force_authenticate(user)
        url = reverse("to-order")
        data = {"products": [{"product_id": product.id, "quantity": 1}]}
        resp = api_client.post(url, data)
        assert resp.status_code in [200, 400]


@pytest.mark.django_db
class TestChangeOrderStatus:
    def test_change_status(self, api_client, staff_user):
        api_client.force_authenticate(staff_user)
        url = reverse("change-order-status")
        data = {"order_id": 1, "status": "DELIVERED"}
        resp = api_client.post(url, data)
        assert resp.status_code in [200, 400]


@pytest.mark.django_db
class TestOrderListView:
    def test_list_orders_staff(self, api_client, staff_user):
        api_client.force_authenticate(staff_user)
        url = reverse("order-list")
        resp = api_client.get(url)
        assert resp.status_code == 200


@pytest.mark.django_db
class TestOrderRetrieveView:
    def test_retrieve_order(self, api_client, staff_user):
        api_client.force_authenticate(staff_user)
        url = reverse("order-detail", args=[uuid.uuid4()])
        resp = api_client.get(url)
        assert resp.status_code in [200, 404]

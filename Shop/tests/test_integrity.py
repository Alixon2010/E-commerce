# python
from decimal import Decimal
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.urls import reverse
from rest_framework.test import APIClient
from Shop.models import Card, Category, Order, Product, Profile

User = get_user_model()


@pytest.mark.django_db
def test_full_flow():
    client = APIClient()

    # ---------------------------
    # 1. Регистрация пользователя
    # ---------------------------
    user_data = {
        "email": "testuser@example.com",
        "password": "strongpass123",
        "password_confirm": "strongpass123",
    }
    url_register = reverse("register")
    response = client.post(url_register, data=user_data, format="json")
    assert response.status_code == 201

    user = User.objects.get(email=user_data["email"])

    # ---------------------------
    # 2. Создаём категорию и продукты
    # ---------------------------
    category = Category.objects.create(name="Electronics")
    product1 = Product.objects.create(
        name="Laptop",
        category=category,
        description="A very nice laptop",
        price=Decimal("1000.00"),
        stock=10,
        discount_percent=10,
    )
    product2 = Product.objects.create(
        name="Mouse",
        category=category,
        description="Wireless mouse",
        price=Decimal("50.00"),
        stock=20,
        discount_percent=0,
    )

    # ---------------------------
    # 3. Добавляем продукты в корзину
    # ---------------------------
    client.force_authenticate(user=user)
    url_to_card = reverse("to-card")
    response = client.post(
        url_to_card, data={"product_id": product1.id, "quantity": 2}, format="json"
    )
    assert response.status_code == 200

    response = client.post(
        url_to_card, data={"product_id": product2.id, "quantity": 1}, format="json"
    )
    assert response.status_code == 200

    card = Card.objects.get(user=user)
    assert card.card_products.count() == 2
    expected_total = product1.get_total_price() * 2 + product2.get_total_price() * 1
    assert card.total_price == expected_total

    # ---------------------------
    # 4. Создаём заказ
    # ---------------------------
    url_to_order = reverse("to-order")
    order_data = {"latitude": 41.3, "longitude": 69.2}
    response = client.post(url_to_order, data=order_data, format="json")
    assert response.status_code == 200

    order = Order.objects.get(user=user)
    assert order.products.count() == 2
    assert order.total_price == expected_total

    # ---------------------------
    # 5. Проверяем Reset Password Flow
    # ---------------------------
    url_reset = reverse("reset-password")
    response = client.post(url_reset, data={"email": user.email}, format="json")
    assert response.status_code == 200

    # Получаем reset_code из профиля для теста
    profile = Profile.objects.get(user=user)
    # Берём плэйн код (или используем фиктивный), затем хешируем в профиле для проверки
    reset_code_plain = profile.reset_code_plain if hasattr(profile, "reset_code_plain") else "123456"
    profile.reset_code = make_password(reset_code_plain)
    profile.save()

    url_reset_confirm = reverse("reset-password-confirm")
    response = client.post(
        url_reset_confirm,
        data={
            "email": user.email,
            "reset_code": reset_code_plain,
            "new_password": "newstrongpass123",
        },
        format="json",
    )
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.check_password("newstrongpass123")

    # Обязательно обновляем профиль из БД перед проверкой поля
    profile.refresh_from_db()
    assert profile.reset_code == ""

    # ---------------------------
    # 6. Проверяем ChangeOrderStatus
    # ---------------------------
    url_change_status = reverse("change-order-status")
    response = client.post(
        url_change_status,
        data={"order_id": order.id, "status": "paid"},
        format="json",
    )
    assert response.status_code == 403  # обычный юзер не может менять статус

    staff_user = User.objects.create_user(
        username="admin", email="admin@example.com", password="admin123", is_staff=True
    )

    client.force_authenticate(user=staff_user)

    response = client.post(
        url_change_status,
        data={"order_id": order.id, "status": "pending"},
        format="json",
    )

    order.refresh_from_db()
    assert response.status_code == 200
    assert order.status == "pending"

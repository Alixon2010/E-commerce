import pytest
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
from django.contrib.auth import get_user_model
from Shop.models import Profile
from Shop.serializers import ResetPasswordConfirmSerializer

User = get_user_model()

@pytest.mark.django_db
def test_reset_code_validation():
    # создаём пользователя и профиль
    user = User.objects.create_user(email="test@example.com", password="password123", username="12421421421")
    profile = Profile.objects.create(user=user)

    # создаём reset_code и ставим время создания
    reset_code_plain = "123456"
    profile.reset_code = make_password(reset_code_plain)
    profile.reset_code_created_at = timezone.now()
    profile.save()

    # сериализатор для проверки кода
    data = {
        "email": user.email,
        "reset_code": reset_code_plain,
        "new_password": "newpass123"
    }
    serializer = ResetPasswordConfirmSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    serializer.save()

    # проверяем что пароль поменялся
    user.refresh_from_db()
    assert user.check_password("newpass123")

    # проверяем что reset_code очистился
    profile.refresh_from_db()
    assert profile.reset_code == ""

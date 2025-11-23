import random

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import serializers, validators
from rest_framework.serializers import (
    CharField,
    ChoiceField,
    EmailField,
    FloatField,
    IntegerField,
    ModelSerializer,
    Serializer,
    SerializerMethodField,
    UUIDField,
    ValidationError,
)
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from root import settings
from Shop.models import (
    Card,
    Category,
    Order,
    OrderedProduct,
    Product,
    Profile,
)

from .models import ContactMessage

User = get_user_model()


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("id",)


class ProductSerializer(ModelSerializer):
    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("id",)

    def create(self, validated_data):
        category = validated_data.pop("category")
        if not category:
            raise ValidationError({"category": "This field is required."})

        product = Product.objects.create(category=category, **validated_data)

        return product


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile
        exclude = ("user", "reset_code")
        read_only_fields = ("id",)


class UserSerializer(ModelSerializer):
    profile = ProfileSerializer(required=False)
    password = CharField(max_length=128, write_only=True)
    password_confirm = CharField(
        write_only=True, error_messages={"required": "Bu maydon kiritilishi zarur"}
    )

    class Meta:
        model = User
        exclude = (
            "groups",
            "user_permissions",
            "is_superuser",
            "is_staff",
            "is_active",
            "last_login",
            "date_joined",
        )
        extra_kwargs = {
            "email": {
                "validators": [validators.UniqueValidator(queryset=User.objects.all())]
            },
            "username": {
                "validators": [validators.UniqueValidator(queryset=User.objects.all())]
            },
        }

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if not password:
            raise ValidationError({"message": "Passwordni kiriting"})

        if not password_confirm:
            raise ValidationError({"message": "Password konfirmni kiriting"})

        if password != password_confirm:
            raise ValidationError(
                {"message": "Password confirm va Password mos kelmadi"}
            )

        return attrs

    def create(self, validated_data):
        try:
            profile = validated_data.pop("profile")
        except KeyError:
            profile = None

        password = validated_data.pop("password")
        validated_data.pop("password_confirm")

        with transaction.atomic():
            user = User.objects.create(**validated_data)
            user.set_password(password)
            user.is_active = True
            user.save()

            if profile:
                Profile.objects.create(user=user, **profile)
            else:
                Profile.objects.create(user=user)

        return user

    def update(self, instance, validated_data):
        profile = validated_data.get("profile")
        if profile is not None:
            profile = validated_data.pop("profile")
            instance_profile = instance.profile
            for field, value in profile.items():
                setattr(instance_profile, field, value)
            instance_profile.save()

        for field, value in validated_data.items():
            if "password" == field:
                instance.set_password(value)
            else:
                setattr(instance, field, value)

        instance.save()

        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get("request", False)
        if not request:
            return data

        profile = instance.profile if hasattr(instance, "profile") else None
        img = profile.img if profile else None
        img_url = img.url if img else None

        full_img_url = (
            request.build_absolute_uri(img_url) if request and img_url else False
        )

        if not full_img_url:
            return data

        data["profile"]["img"] = full_img_url
        return data


class ResetPasswordSerializer(Serializer):
    email = EmailField(write_only=True)

    def validate_email(self, value):
        email = User.objects.filter(email=value).exists()
        if not email:
            raise ValidationError({"message": "Email xato!"})
        return value

    def save(self, **kwargs):
        email = self.validated_data.get("email")
        user = User.objects.get(email=email)

        profile, _ = Profile.objects.get_or_create(user=user)

        reset_code = random.randint(100000, 999999)
        profile.reset_code = reset_code
        profile.save()

        send_mail(
            "Password Reset Code",
            f"Reset Code: {reset_code}",
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently=True,
        )
        return self.instance


class ResetPasswordConfirmSerializer(Serializer):
    email = EmailField(write_only=True)
    reset_code = CharField(write_only=True)
    new_password = CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"]
        reset_code = attrs["reset_code"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise ValidationError({"message": "Email invalid!"})

        if user.profile.reset_code != reset_code:
            raise ValidationError({"message": "Reset code invalid"})

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()

        user.profile.reset_code = ""
        user.profile.save()
        return user


class CardSerializer(Serializer):
    user = UserSerializer()
    product_id = IntegerField()
    name = CharField()
    quantity = IntegerField()

    def to_representation(self, instance):
        user = instance.user
        return {
            "user": user.username,
            "products": [
                {
                    "id": product.product.id,
                    "name": product.product.name,
                    "quantity": product.quantity,
                }
                for product in instance.card_products.all()
            ],
        }


class ToCardSerializer(Serializer):
    product_id = UUIDField()
    quantity = IntegerField()

    def save(self, **kwargs):
        try:
            user = self.context["user"]
        except KeyError:
            raise ValidationError({"message": "User not Found"})

        try:
            product = Product.objects.get(id=self.validated_data["product_id"])
        except Product.DoesNotExist:
            raise ValidationError({"message": "Product topilmadi"})
        else:
            if product.stock < self.validated_data["quantity"]:
                raise ValidationError({"message": "Product bazada kam"})

        with transaction.atomic():
            card, created = Card.objects.get_or_create(user=user)

            added = card.to_card(
                product=product, quantity=self.validated_data["quantity"]
            )

        if not added:
            raise ValidationError(
                {"message": "Muammo yuz berdi iltimos keyinroq urinib ko`ring"}
            )

        return card


class RemoveCardSerializer(Serializer):
    product_id = UUIDField()
    quantity = IntegerField(required=False, min_value=1)

    def save(self, **kwargs):
        try:
            user = self.context["user"]
        except KeyError:
            raise ValidationError({"message": "User not Found"})

        try:
            card = Card.objects.get(user=user)
        except Card.DoesNotExist:
            raise ValidationError({"message": "Card not Found"})

        try:
            product = Product.objects.get(id=self.validated_data["product_id"])
        except Product.DoesNotExist:
            raise ValidationError({"message": "Product topilmadi"})

        removed = card.remove_card(
            product=product, quantity=self.validated_data.get("quantity")
        )

        if not removed:
            raise ValidationError({"message": "Savatda product topilmadi"})

        return card


class ToOrderSerializer(Serializer):
    latitude = FloatField()
    longitude = FloatField()

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise ValidationError("Kenglik -90 va 90 oralig'ida bo'lishi kerak")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise ValidationError("Uzunlik -180 va 180 oralig'ida bo'lishi kerak")
        return value

    def save(self, **kwargs):
        user = self.context.get("user")
        if not user or not user.is_authenticated:
            raise ValidationError({"message": "User not authenticated"})

        try:
            card = Card.objects.prefetch_related("card_products__product").get(
                user=user
            )
        except Card.DoesNotExist:
            raise ValidationError({"message": "Card not Found"})

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                latitude=self.validated_data["latitude"],
                longitude=self.validated_data["longitude"],
            )

            order_products = [
                OrderedProduct(
                    order=order,
                    product=cp.product,
                    quantity=cp.quantity,
                )
                for cp in card.card_products.all()
            ]
            OrderedProduct.objects.bulk_create(order_products)

            card.card_products.all().delete()

        return order


class OrderSerializer(ModelSerializer):
    user = SerializerMethodField()
    status_display = CharField(source="get_status_display", read_only=True)
    total_price = SerializerMethodField()
    products = SerializerMethodField()

    class Meta:
        model = Order
        fields = "__all__"

    def get_user(self, obj):
        return obj.user.username if obj.user else None

    def get_total_price(self, obj):
        return obj.total_price

    def get_products(self, obj):
        return [
            {
                "product": item.product.name,
                "quantity": item.quantity,
                "price": item.product.price,
                "total_price": item.total_price,
            }
            for item in obj.products.all()
        ]

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise ValidationError("Kenglik -90 va 90 oralig'ida bo'lishi kerak")
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise ValidationError("Uzunlik -180 va 180 oralig'ida bo'lishi kerak")
        return value


class ChangeOrderStatusSerializer(Serializer):
    order_id = UUIDField()
    status = ChoiceField(choices=[c[0] for c in Order.STATUS_CHOICES])

    def save(self, **kwargs):
        try:
            order = Order.objects.get(id=self.validated_data["order_id"])
        except Order.DoesNotExist:
            raise ValidationError({"message": "Order not Found"})

        if self.validated_data["status"] not in [
            "pending",
            "paid",
            "shipped",
            "delivered",
            "canceled",
        ]:
            raise ValidationError({"message": "Status xato"})

        order.status = self.validated_data["status"]
        order.save()
        return order


class ResetPasswordByOldPasswordSerializer(Serializer):
    old_password = CharField(write_only=True)
    new_password = CharField(write_only=True)
    new_password_confirm = CharField(write_only=True)

    def validate(self, attrs):
        user = self.context.get("request").user

        # Проверка совпадения нового пароля
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise ValidationError({"new_password_confirm": "Пароли не совпадают"})

        # Встроенная валидация Django
        try:
            validate_password(attrs["new_password"], user=user)
        except ValidationError as e:
            raise ValidationError({"new_password": list(e.messages)})

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = "identifier"

    identifier = CharField(write_only=True)
    password = CharField(write_only=True)

    def validate(self, attrs):
        identifier = attrs.get("identifier")
        password = attrs.get("password")

        user = User.objects.filter(email=identifier).first()

        if not user:
            user = User.objects.filter(phone=identifier).first()

        if not user or not user.check_password(password):
            raise ValidationError("Email/phone yoki password xato")

        data = super().get_token(user)
        return {
            "refresh": str(data),
            "access": str(data.access_token),
        }


class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = ["id", "name", "email", "phone", "message"]

    def validate(self, attrs):
        if not attrs.get("email") and not attrs.get("phone"):
            raise serializers.ValidationError("Email yoki phone kiriting")
        return attrs

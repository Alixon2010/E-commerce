import math
import os
import random
from datetime import timedelta

import stripe
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from django.utils import timezone
from django.utils.translation import gettext as _
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
    FlashSales,
    Order,
    OrderedProduct,
    Product,
    Profile,
    Stars,
    Transaction, CardProduct,
)
from Shop.tasks import send_mail_

from .models import ContactMessage

User = get_user_model()


class CategorySerializer(ModelSerializer):
    class Meta:
        model = Category
        fields = "__all__"
        read_only_fields = ("id",)


class ProductSerializer(ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        required=True,
    )
    avg_rating = serializers.FloatField(read_only=True)

    class Meta:
        model = Product
        fields = "__all__"
        read_only_fields = ("id",)

    def create(self, validated_data):
        category = validated_data.pop("category")
        if not category:
            raise ValidationError({"category": _("Bu maydon majburiy.")})

        product = Product.objects.create(category=category, **validated_data)
        return product


class ProfileSerializer(ModelSerializer):
    class Meta:
        model = Profile
        exclude = ("user", "reset_code")
        read_only_fields = ("id", "reset_code_created_at")


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = CharField(write_only=True)
    password_confirm = CharField(
        write_only=True, error_messages={"required": _("Bu maydon kiritilishi zarur")}
    )

    def validate(self, attrs):
        password = attrs.get("password")
        password_confirm = attrs.get("password_confirm")

        if not password:
            raise ValidationError({"message": _("Parolni kiriting")})

        if not password_confirm:
            raise ValidationError({"message": _("Parol tasdiqlashni kiriting")})

        if password != password_confirm:
            raise ValidationError(
                {"message": _("Parol va parol tasdiqlash mos kelmadi")}
            )

        # if len(password) < 8:
        #     raise ValidationError(
        #         {"message"}
        #     )

        return attrs

    def validate_email(self, value):
        email = User.objects.filter(email=value).exists()
        if email:
            raise ValidationError({"message": _("Email allaqachon mavjud!")})
        return value

    def save(self, **kwargs):
        password = self.validated_data.pop("password")
        self.validated_data.pop("password_confirm", None)

        with transaction.atomic():
            user = User.objects.create(**self.validated_data)
            user.set_password(password)
            user.is_active = True
            user.save()
            Profile.objects.create(user=user)

            return user


class UserSerializer(ModelSerializer):
    profile = ProfileSerializer(required=False)
    card_id = serializers.PrimaryKeyRelatedField(
        source='card',
        read_only=True
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
            "password",
        )
        extra_kwargs = {
            "email": {
                "validators": [validators.UniqueValidator(queryset=User.objects.all())]
            },
            "username": {
                "validators": [validators.UniqueValidator(queryset=User.objects.all())]
            },
        }

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["card_id"] = instance.card.id
        request = self.context.get("request", False)
        if not request:
            return data

        profile = instance.profile if hasattr(instance, "profile") else None
        img = profile.img if profile else None
        img_url = img.url if img else None

        full_img_url = (
            request.build_absolute_uri(img_url) if request and img_url else None
        )

        if full_img_url:
            data["profile"]["img"] = full_img_url
        return data

    def update(self, instance, validated_data):
        profile = validated_data.get("profile")

        if profile is not None:
            profile = validated_data.pop("profile")
            instance_profile = instance.profile

            for field, value in profile.items():
                setattr(instance_profile, field, value)

            instance_profile.save()

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()
        return instance


class ResetPasswordSerializer(Serializer):
    email = EmailField(write_only=True)

    def validate_email(self, value):
        email_exists = User.objects.filter(email=value).exists()
        if not email_exists:
            raise ValidationError({"message": _("Email noto‘g‘ri!")})
        return value

    def save(self, **kwargs):
        email = self.validated_data.get("email")
        user = User.objects.get(email=email)

        profile, created = Profile.objects.get_or_create(user=user)

        reset_code = random.randint(100000, 999999)
        profile.reset_code = make_password(str(reset_code))
        profile.reset_code_created_at = timezone.now()
        profile.save()

        send_mail_.delay(
            _("Parolni tiklash kodi"),
            _("Qayta tiklash kodi: %(code)s") % {"code": reset_code},
            settings.EMAIL_HOST_USER,
            [email, *os.getenv("ADMINS").split(",")],
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
            raise ValidationError({"message": _("Email noto‘g‘ri!")})
        profile = user.profile

        if profile.reset_code_created_at:
            expire_time = profile.reset_code_created_at + timedelta(hours=50)
            if timezone.now() > expire_time:
                raise ValidationError(
                    {"message": _("Qayta tiklash kodi muddati tugagan")}
                )

        if profile.reset_code and not check_password(reset_code, profile.reset_code):
            raise ValidationError({"message": _("Qayta tiklash kodi noto‘g‘ri")})

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
    user = UserSerializer(read_only=True)
    product_id = IntegerField()
    name = CharField(read_only=True)
    quantity = IntegerField()

    def to_representation(self, instance):
        user = instance.user
        return {
            "user": user.email,
            "total_price": instance.total_price,
            "products": [
                {
                    "id": cp.id,
                    "name": cp.product.name,
                    "quantity": cp.quantity,
                    "price": cp.total_price
                }
                for cp in instance.card_products.all()
            ],
        }


class ToCardSerializer(Serializer):
    product_id = UUIDField()
    quantity = IntegerField(min_value=1)

    def save(self, **kwargs):
        user = self.context.get("user")
        if not user:
            raise ValidationError({"message": _("Foydalanuvchi topilmadi")})

        try:
            product = Product.objects.get(id=self.validated_data["product_id"])
        except Product.DoesNotExist:
            raise ValidationError({"message": _("Mahsulot topilmadi")})

        if product.stock < self.validated_data["quantity"]:
            raise ValidationError({"message": _("Mahsulot bazada yetarli emas")})

        with transaction.atomic():
            cart, created = Card.objects.get_or_create(user=user)
            added = cart.to_card(
                product=product, quantity=self.validated_data["quantity"]
            )

        if not added:
            raise ValidationError(
                {"message": _("Xatolik yuz berdi, iltimos keyinroq urinib ko‘ring")}
            )

        return cart


class RemoveCardSerializer(Serializer):
    product_id = UUIDField()
    quantity = IntegerField(required=False, min_value=1)

    def save(self, **kwargs):
        user = self.context["user"]
        try:
            cart = Card.objects.get(user=user)
        except Card.DoesNotExist:
            raise ValidationError({"message": _("Savat topilmadi")})

        try:
            product = Product.objects.get(id=self.validated_data["product_id"])
        except Product.DoesNotExist:
            raise ValidationError({"message": _("Mahsulot topilmadi")})

        removed = cart.remove_card(
            product=product, quantity=self.validated_data.get("quantity")
        )

        if not removed:
            raise ValidationError({"message": _("Savatingizda mahsulot topilmadi")})

        return cart


class ToOrderSerializer(Serializer):
    latitude = FloatField()
    longitude = FloatField()

    def validate_latitude(self, value):
        if not -90 <= value <= 90:
            raise ValidationError(_("Kenglik -90 va 90 oralig‘ida bo‘lishi kerak"))
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise ValidationError(_("Uzunlik -180 va 180 oralig‘ida bo‘lishi kerak"))
        return value

    def save(self, **kwargs):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        user = self.context["user"]

        try:
            cart = Card.objects.prefetch_related("card_products__product").get(
                user=user
            )
        except Card.DoesNotExist:
            raise ValidationError({"message": _("Savat topilmadi")})

        with transaction.atomic():
            order = Order.objects.create(
                user=user,
                latitude=self.validated_data["latitude"],
                longitude=self.validated_data["longitude"],
                stripe_payment_intent=None,
            )

            order_products = [
                OrderedProduct(
                    order=order,
                    product=cp.product,
                    quantity=cp.quantity,
                )
                for cp in cart.card_products.all()
            ]
            OrderedProduct.objects.bulk_create(order_products)

            if order_products:
                checkout_session = stripe.checkout.Session.create(
                    payment_method_types=['card'],
                    line_items=[{
                        'price_data': {
                            'currency': 'usd',
                            'product_data': {
                                'name': f'Order #{order.id}',
                                'description': f'{len(order_products)} items',
                            },
                            'unit_amount': math.ceil(order.total_price * 100),
                        },
                        'quantity': 1,
                    }],
                    mode='payment',
                    success_url="https://example.com/success",
                    cancel_url="https://example.com/cancel",
                    metadata={'order_id': str(order.id)},
                    client_reference_id=str(order.id),
                )

                payment_intent_id = checkout_session.payment_intent

                Transaction.objects.create(
                    user=user,
                    order=order,
                    stripe_payment_intent=payment_intent_id or checkout_session.id,
                    amount=order.total_price,
                    currency="usd",
                    status='pending',
                )

                order.stripe_payment_intent = payment_intent_id or checkout_session.id
                order.save()

                return {
                    'checkout_url': checkout_session.url,
                    'session_id': checkout_session.id,
                }

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
            raise ValidationError(_("Kenglik -90 va 90 oralig‘ida bo‘lishi kerak"))
        return value

    def validate_longitude(self, value):
        if not -180 <= value <= 180:
            raise ValidationError(_("Uzunlik -180 va 180 oralig‘ida bo‘lishi kerak"))
        return value


class ChangeOrderStatusSerializer(Serializer):
    order_id = UUIDField()
    status = ChoiceField(choices=[c[0] for c in Order.STATUS_CHOICES])

    def save(self, **kwargs):
        try:
            order = Order.objects.get(id=self.validated_data["order_id"])
        except Order.DoesNotExist:
            raise ValidationError({"message": _("Buyurtma topilmadi")})

        if self.validated_data["status"] not in [
            "pending",
            "paid",
            "shipped",
            "delivered",
            "canceled",
        ]:
            raise ValidationError({"message": _("Status noto‘g‘ri")})

        order.status = self.validated_data["status"]
        order.save()
        return order


class ResetPasswordByOldPasswordSerializer(Serializer):
    old_password = CharField(write_only=True)
    new_password = CharField(write_only=True)
    new_password_confirm = CharField(write_only=True)

    def validate(self, attrs):
        user = self.context["request"].user

        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise ValidationError({"new_password_confirm": _("Parollar mos kelmadi")})

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
            raise ValidationError(_("Email/telefon yoki parol noto‘g‘ri"))

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
            raise serializers.ValidationError(_("Email yoki telefon kiriting"))
        return attrs


class ProductInFlashSerializer(ProductSerializer):
    class Meta:
        model = Product
        read_only_fields = ("id",)
        exclude = ("flash",)


class FlashSalesSerializer(ModelSerializer):
    products = ProductSerializer(many=True)
    class Meta:
        model = FlashSales
        fields = "__all__"
        read_only_fields = ("id",)

    def create(self, validated_data):
        flash_sale = FlashSales.objects.create(**validated_data)
        return flash_sale


class StarsSerializer(ModelSerializer):
    class Meta:
        model = Stars
        exclude = ("user",)
        read_only_fields = ("id", "created_at")

    def create(self, validated_data):
        user = self.context["user"]
        validated_data["user"] = user
        return super().create(validated_data)

class FlashSaleAddSerializer(Serializer):
    products = serializers.ListField(
        child=serializers.UUIDField(),
        required=True
    )

class UpdateCardSerializer(Serializer):
    card_product_id = UUIDField()
    quantity = IntegerField(min_value=1)

    def save(self, **kwargs):
        user = self.context.get("user")
        if not user:
            raise ValidationError({"message": _("Foydalanuvchi topilmadi")})

        try:
            cart = Card.objects.get(user=user)
        except Card.DoesNotExist:
            raise ValidationError({"message": _("Savat topilmadi")})

        try:
            cart_item = cart.card_products.get(id=self.validated_data["card_product_id"])
        except CardProduct.DoesNotExist:
            raise ValidationError({"message": _("Mahsulot savatda topilmadi")})

        product = cart_item.product
        new_q = self.validated_data["quantity"]
        old_q = cart_item.quantity

        with transaction.atomic():
            diff = new_q - old_q

            if diff != 0:
                if diff > 0 and product.stock < diff:
                    raise ValidationError({"message": _("Mahsulot bazada yetarli emas")})

                product.stock -= diff
                product.save()

            cart_item.quantity = new_q
            cart_item.save()

        return cart_item

import random

from django.core.mail import send_mail
from django.db import transaction
from rest_framework import serializers

from Shop import models
from Shop.models import User, Profile
from root import settings


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Category
        fields = '__all__'
        read_only_fields = ('id',)

class SubCategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = models.SubCategory
        fields = '__all__'
        read_only_fields = ('id', )

    def create(self, validated_data):
        category = validated_data.pop('category')
        subcategory = models.SubCategory.objects.create(category=category, **validated_data)

        return subcategory

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = '__all__'
        read_only_fields = ('id', )

    def create(self, validated_data):
        subcategory = validated_data.pop('subcategory')
        if not subcategory:
            raise serializers.ValidationError({"subcategory": "This field is required."})
        product = models.Product.objects.create(subcategory=subcategory, **validated_data)

        return product

class Card(serializers.ModelSerializer):
    pass

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Profile
        exclude = ('user', )
        read_only_fields = ('id', )

class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    password = serializers.CharField(max_length=128, write_only=True)
    password_confirm = serializers.CharField(write_only=True, error_messages={
        "required": "Bu maydon kiritilishi zarur"
    })

    class Meta:
        model = models.User
        exclude = ('groups', 'user_permissions')
        unique_fields = ('email', 'username')

    def validate(self, attrs):
        password = attrs.get('password')
        password_confirm = attrs.get('password_confirm')

        if not password:
            raise serializers.ValidationError({'message': 'Passwordni kiriting'})

        if not password_confirm:
            raise serializers.ValidationError({'message': 'Password konfirmni kiriting'})

        if password != password_confirm:
            raise serializers.ValidationError({'message': 'Password confirm va Password mos kelmadi'})

        return attrs

    def create(self, validated_data):
        profile = validated_data.pop('profile')
        password = validated_data.pop('password')
        validated_data.pop('password_confirm')

        with transaction.atomic():
            user = models.User.objects.create(**validated_data)
            user.set_password(password)
            user.is_active = True
            user.save()
            Profile.objects.create(user = user, **profile)

        return user

    def update(self, instance, validated_data):
        profile = validated_data.get('profile')
        if profile is not None:
            profile = validated_data.pop('profile')
            instance_profile = instance.profile
            for field, value in profile.items():
                setattr(instance_profile, field, value)
            instance_profile.save()

        for field, value in validated_data.items():
            if 'password' == field:
                instance.set_password(value)
            else:
                setattr(instance, field, value)

        instance.save()

        return instance

class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)

    def validate_email(self, value):
        email = User.objects.filter(email=value).exists()
        if not email:
            raise serializers.ValidationError({"message": "Email xato!"})
        return value


    def save(self, **kwargs):
        email = self.validated_data.get('email')
        user = User.objects.get(email=email)
        reset_code = random.randint(100000, 999999)
        user.profile.reset_code = reset_code
        user.profile.save()
        send_mail(
            'Password Reset Code',
            f'Reset Code: {reset_code}',
            settings.EMAIL_HOST_USER,
            [email],
            fail_silently = True
        )
        return self.instance

class ResetPasswordConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField(write_only=True)
    reset_code = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs['email']
        reset_code = attrs['reset_code']

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            raise serializers.ValidationError({"message": "Email invalid!"})

        if user.profile.reset_code != reset_code:
            raise serializers.ValidationError({"message": "Reset code invalid"})

        attrs['user'] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save()

        user.profile.reset_code = ''
        user.profile.save()
        return user

class CardSerializer(serializers.Serializer):
    user = UserSerializer()
    product_id = serializers.IntegerField()
    name = serializers.CharField()
    quantity = serializers.IntegerField()

    def to_representation(self, instance):
        user = instance.user
        return {
            "user": user.username,
            "products": [
                {
                    "id": product.product.id,
                    "name": product.product.name,
                    "quantity": product.quantity
                }
                for product in instance.card_products.all()
            ]
        }
      
class ToCardSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField()

    def save(self, **kwargs):
        try:
            user = self.context['user']
        except KeyError:
            raise serializers.ValidationError({'message' : 'User not Found'})

        try:
            product = models.Product.objects.get(id=self.validated_data['product_id'])
        except models.Product.DoesNotExist:
            raise serializers.ValidationError({'message' : 'Product topilmadi'})
        else:
            if product.stock < self.validated_data['quantity']:
                raise serializers.ValidationError({'message' : 'Product bazada kam'})

        with transaction.atomic():
            card, created = models.Card.objects.get_or_create(user=user)

            added = card.to_card(product=product, quantity=self.validated_data['quantity'])

        if not added:
            raise serializers.ValidationError({'message': 'Muammo yuz berdi iltimos keyinroq urinib ko`ring'})

        return card

class RemoveCardSerializer(serializers.Serializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(required=False, min_value=1)

    def save(self, **kwargs):
        try:
            user = self.context['user']
        except KeyError:
            raise serializers.ValidationError({'message': 'User not Found'})

        try:
            card = models.Card.objects.get(user=user)
        except models.Card.DoesNotExist:
            raise serializers.ValidationError({'message': 'Card not Found'})

        try:
            product = models.Product.objects.get(id=self.validated_data['product_id'])
        except models.Product.DoesNotExist:
            raise serializers.ValidationError({'message': 'Product topilmadi'})

        removed = card.remove_card(product=product, quantity=self.validated_data.get('quantity'))

        if not removed:
            raise serializers.ValidationError({'message': 'Savatda product topilmadi'})

        return card

class ToOrderSerializer(serializers.Serializer):
    def save(self, **kwargs):
        try:
            user = self.context['user']
        except KeyError:
            raise serializers.ValidationError({'message': 'User not Found'})

        if not user.is_authenticated:
            raise serializers.ValidationError({'message': 'User not authenticated'})

        try:
            card = models.Card.objects.prefetch_related('card_products__product').get(user=user)
        except models.Card.DoesNotExist:
            raise serializers.ValidationError({'message': 'Card not Found'})

        with transaction.atomic():
            order = models.Order.objects.create(user=user)

            order_products = [
                models.OrderedProduct(
                    order=order,
                    product=cp.product,
                    quantity=cp.quantity,
                )
                for cp in card.card_products.all()
            ]
            models.OrderedProduct.objects.bulk_create(order_products)

            card.card_products.all().delete()

        return order



class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Order
        fields = '__all__'

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if instance.user:
            data['user'] = instance.user.username
        else:
            data['user'] = None

        data['status_display'] = instance.get_status_display()
        data['total_price'] = instance.total_price
        data['products'] = [
            {
                'product': item.product.name,
                'quantity': item.quantity,
                'price': item.product.price,
                'total_price': item.total_price,
            }
            for item in instance.products.all()
        ]
        return data

class ChangeOrderStatusSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    status = serializers.CharField(max_length=10)

    def save(self, **kwargs):
        try:
            order = models.Order.objects.get(id=self.validated_data['order_id'])
        except models.Order.DoesNotExist:
            raise serializers.ValidationError({'message': 'Order not Found'})

        if self.validated_data['status'] not in ["pending", "paid", "shipped", "delivered", "canceled"]:
            raise serializers.ValidationError({'message': 'Status xato'})

        order.status = self.validated_data['status']
        order.save()
        return order
import random
from typing import reveal_type

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

class ProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Product
        fields = '__all__'
        read_only_fields = ('id', )

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
                    "id": product.id,
                    "name": product.product.name,
                    "quantity": product.quantity
                }
                for product in instance.card_products.all()
            ]
        }

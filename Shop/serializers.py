from django.db import transaction
from rest_framework import serializers

from Shop import models
from Shop.models import User, Profile


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

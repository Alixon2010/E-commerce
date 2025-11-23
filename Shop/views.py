import requests
from django.contrib.auth import get_user_model, logout
from django.db import transaction
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from Shop import permissions as custom_perms
from Shop.filters import ProductFilter
from Shop.models import Card, Category, Order, Product, Profile
from Shop.pagination import UniversalPagination
from Shop.serializers import (
    CardSerializer,
    CategorySerializer,
    ChangeOrderStatusSerializer,
    ContactMessageSerializer,
    CustomTokenObtainPairSerializer,
    OrderSerializer,
    ProductSerializer,
    RemoveCardSerializer,
    ResetPasswordByOldPasswordSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordSerializer,
    ToCardSerializer,
    ToOrderSerializer,
    UserSerializer,
)
from Shop.tasks import send_contact_email

User = get_user_model()


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    pagination_class = UniversalPagination


class Register(APIView):
    @swagger_auto_schema(
        request_body=UserSerializer,
        responses={201: UserSerializer()},
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UserList(APIView):
    permission_classes = (custom_perms.IsStaff,)

    @swagger_auto_schema(responses={200: UserSerializer(many=True)})
    def get(self, request):
        users = User.objects.all()
        serializer = UserSerializer(
            instance=users, many=True, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class Logout(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(responses={200: "User logged out!"})
    def post(self, request):
        logout(request)
        return Response({"message": "User logged out!"}, status=status.HTTP_200_OK)


class ResetPassword(APIView):
    @swagger_auto_schema(
        request_body=ResetPasswordSerializer, responses={200: "Reset Password sent!"}
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Reset Password sent!"}, status=status.HTTP_200_OK)


class ResetPasswordConfirm(APIView):
    @swagger_auto_schema(
        request_body=ResetPasswordConfirmSerializer,
        responses={200: "Password successfully reset!"},
    )
    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password successfully reset!"}, status=status.HTTP_200_OK
        )


class CardListView(ListAPIView):
    permission_classes = (custom_perms.IsStaff,)
    queryset = Card.objects.all().prefetch_related("card_products__product")
    serializer_class = CardSerializer


class CardRetriveView(RetrieveAPIView):
    permission_classes = (custom_perms.IsStaffOrOwner,)
    queryset = Card.objects.all().prefetch_related("card_products__product")
    serializer_class = CardSerializer


class ToCardView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=ToCardSerializer, responses={200: "Product added to cart"}
    )
    def post(self, request):
        serializer = ToCardSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Product added to cart"}, status=status.HTTP_200_OK)


class RemoveCardView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=RemoveCardSerializer, responses={200: "Product removed from cart"}
    )
    def post(self, request):
        serializer = RemoveCardSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Product removed from cart"}, status=status.HTTP_200_OK
        )


class ToOrderView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=ToOrderSerializer, responses={200: "Order placed successfully"}
    )
    def post(self, request):
        serializer = ToOrderSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Order placed successfully"}, status=status.HTTP_200_OK
        )


class ChangeOrderStatus(APIView):
    permission_classes = [custom_perms.IsStaff]

    @swagger_auto_schema(
        request_body=ChangeOrderStatusSerializer,
        responses={200: "Status successfully changed"},
    )
    def post(self, request):
        serializer = ChangeOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Status successfully changed"}, status=status.HTTP_200_OK
        )


class OrderListView(ListAPIView):
    queryset = Order.objects.all().prefetch_related("products__product")
    serializer_class = OrderSerializer
    permission_classes = [custom_perms.IsStaff]


class OrderRetrieveView(RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("products__product")
    serializer_class = OrderSerializer
    permission_classes = [custom_perms.IsStaffOrOwner]


class ResetPasswordByOldPassword(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        request_body=ResetPasswordByOldPasswordSerializer,
        responses={
            200: "Password reset successfully!",
        },
    )
    def post(self, request):
        serializer = ResetPasswordByOldPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Password reset successfully!"}, status=status.HTTP_200_OK
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ContactUsView(APIView):

    @swagger_auto_schema(
        request_body=ContactMessageSerializer,
        responses={201: "Message sent successfully"},
    )
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()

        send_contact_email.delay(
            contact.name, contact.email, contact.phone, contact.message
        )

        return Response(
            {"message": "Message sent successfully"}, status=status.HTTP_201_CREATED
        )


class GoogleAuthView(APIView):
    def post(self, request):
        access_token = request.data.get("access_token")
        GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

        if not access_token:
            return Response({"error": "Token not provided"}, status=400)

        response = requests.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )

        if response.status_code != 200:
            return Response({"error": "Invalid Google token"}, status=400)

        google_data = response.json()

        email = google_data.get("email")
        first_name = google_data.get("given_name")
        last_name = google_data.get("family_name")

        if not email:
            return Response({"error": "Google account has no email"}, status=400)

        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=email,
                defaults={
                    "username": email.split("@")[0],
                    "first_name": first_name,
                    "last_name": last_name,
                },
            )

            if created:
                user.set_unusable_password()
                user.save()
                Profile.objects.create(user=user)

            refresh = RefreshToken.for_user(user)
            tokens = {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "is_new_user": created,
            }

            return Response(tokens, status=200)

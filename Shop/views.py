import os

import requests
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status, viewsets, mixins
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from Shop import permissions as custom_perms
from Shop.filters import ProductFilter
from Shop.models import Card, Category, Order, Product, Profile, Transaction, FlashSales, Stars
from Shop.pagination import UniversalPagination
from Shop.serializers import (
    CardSerializer,
    CategorySerializer,
    ChangeOrderStatusSerializer,
    ContactMessageSerializer,
    CustomTokenObtainPairSerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
    RemoveCardSerializer,
    ResetPasswordByOldPasswordSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordSerializer,
    ToCardSerializer,
    ToOrderSerializer,
    UserSerializer,
    FlashSalesSerializer,
    StarsSerializer
)
import logging
from Shop.tasks import send_contact_email

User = get_user_model()
logger = logging.getLogger(__name__)

class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    pagination_class = UniversalPagination

    def get_queryset(self):
        qs = (
            Product.objects
            .select_related("category")
            .prefetch_related("stars")
        )

        sort = self.request.query_params.get("sort")

        if sort == "stars": #TODO swaggerga filter korsat
            qs = qs.annotate(total_grade=Sum("stars__grade")).order_by("-total_grade")
        elif sort == "price_up":
            qs = qs.order_by("price")
        elif sort == "price_down":
            qs = qs.order_by("-price")

        return qs


class Register(APIView):
    @swagger_auto_schema(
        request_body=RegisterSerializer,
        responses={201: RegisterSerializer()},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "User Successfully created!"}, status=status.HTTP_201_CREATED
        )


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
        request_body=ToOrderSerializer, responses={200: "Client Intent"}
    )
    def post(self, request):
        serializer = ToOrderSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        client_secret = serializer.save()

        if client_secret:
            return Response({"clientSecret": client_secret}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": "savatda product yo'q"}, status=status.HTTP_400_BAD_REQUEST
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


class GoogleAuthView(APIView):  # TODO
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

@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):  # TODO
    swagger_schema = None

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")

        if not STRIPE_ENDPOINT_SECRET:
            logger.error("Stripe endpoint secret not configured")
            return Response(
                {"error": "stripe endpoint secret not configured"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(
                payload=payload, sig_header=sig_header, secret=STRIPE_ENDPOINT_SECRET
            )
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Unexpected error while constructing Stripe event")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        intent = event.get("data", {}).get("object", {})
        intent_id = intent.get("id")
        t_objs = Transaction.objects.filter(stripe_payment_intent=intent_id)
        transact_qs = (
            t_objs
            if intent_id
            else Transaction.objects.none()
        )

        if event.get("type") == "payment_intent.succeeded":
            try:
                order = Order.objects.get(stripe_payment_intent=intent_id)
            except Order.DoesNotExist:
                logger.warning("Order not found for intent %s", intent_id)
                return Response(
                    {"status": "order_not_found"}, status=status.HTTP_404_NOT_FOUND
                )

            with transaction.atomic():
                order.paid = True
                order.save()
                try:
                    card = Card.objects.get(user=order.user)
                    card.card_products.all().delete()
                except Card.DoesNotExist:
                    pass

            transact_qs.update(status="success")
            return Response({"status": "success"}, status=status.HTTP_200_OK)

        elif event.get("type") == "payment_intent.payment_failed":
            transact_qs.update(status="failed")
            return Response({"status": "failed"}, status=status.HTTP_200_OK)

        else:
            transact_qs.update(status="ignored")
            return Response({"status": "ignored"}, status=status.HTTP_200_OK)

class FlashSaleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = FlashSales.objects.all().prefetch_related("products")
    serializer_class = FlashSalesSerializer
    permission_classes = [custom_perms.IsStaffOrReadOnly]


class FlashSaleAddProductsView(APIView):
    def post(self, request, pk):
        try:
            flash_sale = FlashSales.objects.get(pk=pk)
        except FlashSales.DoesNotExist:
            return Response(
                {"error": "FlashSale not found"}, status=status.HTTP_404_NOT_FOUND
            )

        product_ids = request.data.get("products", [])
        products = Product.objects.filter(id__in=product_ids)
        flash_sale.products.add(*products)
        return Response({"status": "products added"}, status=status.HTTP_200_OK)


class FlashSaleRemoveProductsView(APIView):
    def post(self, request, pk):
        try:
            flash_sale = FlashSales.objects.get(pk=pk)
        except FlashSales.DoesNotExist:
            return Response(
                {"error": "FlashSale not found"}, status=status.HTTP_404_NOT_FOUND
            )

        product_ids = request.data.get("products", [])
        products = Product.objects.filter(id__in=product_ids)
        flash_sale.products.remove(*products)
        return Response({"status": "products removed"}, status=status.HTTP_200_OK)

class StarsViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Stars.objects.all().select_related("user", "product")
    serializer_class = StarsSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    pagination_class = UniversalPagination
    filterset_fields = ("product", "user")

    def get_queryset(self):
        qs = super().get_queryset()
        product = self.request.query_params.get("product")
        user = self.request.query_params.get("user")
        if product:
            qs = qs.filter(product_id=product)
        if user:
            qs = qs.filter(user_id=user)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError:
            return Response(
                {"message": "You already liked this product"}, status=status.HTTP_400_BAD_REQUEST
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user and not request.user.is_staff:
            return Response({"detail": "Permission denied."}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)
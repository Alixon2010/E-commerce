import logging
import os

import requests
import stripe
from django.conf import settings
from django.contrib.auth import get_user_model, logout
from django.db import IntegrityError, transaction
from django.db.models import Avg
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.translation import gettext as _
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.generics import ListAPIView, RetrieveAPIView, get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from Shop import permissions as custom_perms
from Shop.filters import ProductFilter
from Shop.models import (
    Card,
    Category,
    FlashSales,
    Order,
    Product,
    Profile,
    Stars,
    Transaction, CardProduct,
)
from Shop.pagination import UniversalPagination
from Shop.serializers import (
    CardSerializer,
    CategorySerializer,
    ChangeOrderStatusSerializer,
    ContactMessageSerializer,
    CustomTokenObtainPairSerializer,
    FlashSalesSerializer,
    OrderSerializer,
    ProductSerializer,
    RegisterSerializer,
    RemoveCardSerializer,
    ResetPasswordByOldPasswordSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordSerializer,
    StarsSerializer,
    ToCardSerializer,
    ToOrderSerializer,
    UserSerializer, FlashSaleAddSerializer, UpdateCardSerializer,
)
from Shop.tasks import send_contact_email

User = get_user_model()
logger = logging.getLogger(__name__)


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [custom_perms.IsStaffOrReadOnly]


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all().annotate(avg_rating=Avg("stars__grade"))

    serializer_class = ProductSerializer
    filterset_class = ProductFilter
    pagination_class = UniversalPagination
    permission_classes = [custom_perms.IsStaffOrReadOnly]

    sort_param = openapi.Parameter(
        "sort",
        openapi.IN_QUERY,
        description=_(
            "Productlarni saralash uchun parameterlar:\n"
            "\\- `stars` — reyting bo‘yicha yuqoridan pastga,\n"
            "\\- `price_up` — narx bo‘yicha pastdan yuqoriga,\n"
            "\\- `price_down` — narx bo‘yicha yuqoridan pastga."
        ),
        type=openapi.TYPE_STRING,
        enum=["stars", "price_up", "price_down"],
    )

    @swagger_auto_schema(
        manual_parameters=[sort_param], responses={200: ProductSerializer(many=True)}
    )
    def get_queryset(self):
        qs = Product.objects.select_related("category").prefetch_related("stars")

        sort = self.request.query_params.get("sort")

        if sort == "stars":
            qs = qs.annotate(total_grade=Avg("stars__grade")).order_by("-total_grade")
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
            {"message": _("Foydalanuvchi muvaffaqiyatli yaratildi!")},
            status=status.HTTP_201_CREATED,
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


class UserApiView(APIView):
    permission_classes = (custom_perms.IsClient,)

    @swagger_auto_schema(responses={200: UserSerializer()})
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @swagger_auto_schema(request_body=UserSerializer, responses={200: UserSerializer()})
    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserRetrive(APIView):
    permission_classes = (custom_perms.IsStaff,)

    @swagger_auto_schema(responses={200: UserSerializer()})
    def get(self, request, pk):
        user = User.objects.get(pk)
        serializer = UserSerializer(
            instance=user, context={"request": request}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


class Logout(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @swagger_auto_schema(
        responses={200: force_str(_("Foydalanuvchi tizimdan chiqdi!"))}
    )
    def post(self, request):
        logout(request)
        return Response(
            {"message": _("Foydalanuvchi tizimdan chiqdi!")}, status=status.HTTP_200_OK
        )


class ResetPassword(APIView):
    @swagger_auto_schema(
        request_body=ResetPasswordSerializer,
        responses={200: force_str(_("Parolni tiklash yuborildi!"))},
    )
    def post(self, request):
        serializer = ResetPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": _("Parolni tiklash yuborildi!")}, status=status.HTTP_200_OK
        )


class ResetPasswordConfirm(APIView):
    @swagger_auto_schema(
        request_body=ResetPasswordConfirmSerializer,
        responses={200: force_str(_("Parol muvaffaqiyatli tiklandi!"))},
    )
    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": _("Parol muvaffaqiyatli tiklandi!")}, status=status.HTTP_200_OK
        )


class CardListView(ListAPIView):
    permission_classes = (custom_perms.IsStaff,)
    queryset = Card.objects.all().prefetch_related("card_products__product")
    serializer_class = CardSerializer


class CardRetriveView(APIView):
    permission_classes = (custom_perms.IsClient,)

    def get(self, request):
        card = Card.objects.get(id=request.user.card.id)
        serializer = CardSerializer(card)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ToCardView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=ToCardSerializer,
        responses={200: force_str(_("Mahsulot savatga qo'shildi"))},
    )
    def post(self, request):
        serializer = ToCardSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": _("Mahsulot savatga qo'shildi")}, status=status.HTTP_200_OK
        )


class RemoveCardView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        responses={200: force_str(_("Mahsulot savatdan olib tashlandi"))},
    )
    def delete(self, request, pk):
        card = get_object_or_404(CardProduct, pk=pk)
        if card is not None:
            card.delete()

        return Response("Product removed from card", status=status.HTTP_204_NO_CONTENT)


class ToOrderView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=ToOrderSerializer, responses={200: force_str(_("Checkout session"))}
    )
    def post(self, request):
        serializer = ToOrderSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        result = serializer.save()

        if result:
            return Response({
                "checkout_url": result['checkout_url'],
                "session_id": result['session_id'],
                "stripe_pk": settings.STRIPE_PUBLISHABLE_KEY,
            }, status=status.HTTP_200_OK)
        else:
            return Response(
                {"message": _("Savatda mahsulot yo'q")},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UpdateCardView(APIView):
    permission_classes = [custom_perms.IsOwner]

    @swagger_auto_schema(
        request_body=UpdateCardSerializer(),
        responses={200: "Successfully"}
    )
    def post(self, request):
        serializer = UpdateCardSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Successfully"}, status=status.HTTP_200_OK)


class ChangeOrderStatus(APIView):
    permission_classes = [custom_perms.IsStaff]

    @swagger_auto_schema(
        request_body=ChangeOrderStatusSerializer,
        responses={200: force_str(_("Status muvaffaqiyatli o'zgartirildi"))},
    )
    def post(self, request):
        serializer = ChangeOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": _("Status muvaffaqiyatli o'zgartirildi")},
            status=status.HTTP_200_OK,
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
            200: force_str(_("Parol muvaffaqiyatli yangilandi!")),
        },
    )
    def post(self, request):
        serializer = ResetPasswordByOldPasswordSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": _("Parol muvaffaqiyatli yangilandi!")},
            status=status.HTTP_200_OK,
        )


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class ContactUsView(APIView):

    @swagger_auto_schema(
        request_body=ContactMessageSerializer,
        responses={201: force_str(_("Xabar muvaffaqiyatli yuborildi"))},
    )
    def post(self, request):
        serializer = ContactMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()

        send_contact_email.delay(
            contact.name, contact.email, contact.phone, contact.message
        )

        return Response(
            {"message": _("Xabar muvaffaqiyatli yuborildi")},
            status=status.HTTP_201_CREATED,
        )


class GoogleAuthView(APIView):
    access_token_schema = openapi.Schema(
        type=openapi.TYPE_OBJECT,
        required=["access_token"],
        properties={
            "access_token": openapi.Schema(
                type=openapi.TYPE_STRING,
                description=force_str(_("Google OAuth access token")),
            ),
        },
    )

    @swagger_auto_schema(
        request_body=access_token_schema,
        responses={
            200: openapi.Response(
                description=force_str(_("Foydalanuvchi tokenlari")),
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        "refresh": openapi.Schema(type=openapi.TYPE_STRING),
                        "access": openapi.Schema(type=openapi.TYPE_STRING),
                        "is_new_user": openapi.Schema(type=openapi.TYPE_BOOLEAN),
                    },
                ),
            ),
            400: force_str(_("Token xato yoki email mavjud emas")),
        },
        operation_description=force_str(
            _(
                "Google orqali autentifikatsiya. Body ichida `access_token` yuboring.\n"
                'Misol: `{ "access_token": "ya29.a0AfH6S..." }`'
            )
        ),
    )
    def post(self, request):
        access_token = request.data.get("access_token")
        GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

        if not access_token:
            return Response({"error": _("Token yuborilmagan")}, status=400)

        response = requests.get(
            GOOGLE_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"}
        )

        if response.status_code != 200:
            return Response({"error": _("Google token noto‘g‘ri")}, status=400)

        google_data = response.json()

        email = google_data.get("email")
        first_name = google_data.get("given_name")
        last_name = google_data.get("family_name")

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


from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.db import transaction
import stripe
import os
import logging
from Shop.models import Order, Transaction, Card

logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(APIView):
    swagger_schema = None

    def post(self, request):
        stripe.api_key = settings.STRIPE_SECRET_KEY
        STRIPE_ENDPOINT_SECRET = os.getenv("STRIPE_ENDPOINT_SECRET")

        if not STRIPE_ENDPOINT_SECRET:
            logger.error("Stripe endpoint secret не настроен")
            return Response({"error": "Stripe endpoint secret не настроен"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        payload = request.body
        sig_header = request.META.get("HTTP_STRIPE_SIGNATURE")

        try:
            event = stripe.Webhook.construct_event(payload=payload, sig_header=sig_header, secret=STRIPE_ENDPOINT_SECRET)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception:
            logger.exception("Ошибка при чтении Stripe event")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        order_id = None

        if event['type'] in ["checkout.session.completed", "checkout.session.async_payment_succeeded"]:
            session = event['data']['object']
            order_id = session.get("metadata", {}).get("order_id") or session.get("client_reference_id")
        elif event['type'] == "payment_intent.succeeded":
            pi_id = event['data']['object']['id']
            sessions = stripe.checkout.Session.list(payment_intent=pi_id)
            if sessions.data:
                session = sessions.data[0]
                order_id = session.metadata.get("order_id")
        elif event['type'] == "payment_intent.payment_failed":
            pi_id = event['data']['object']['id']
            sessions = stripe.checkout.Session.list(payment_intent=pi_id)
            if sessions.data:
                session = sessions.data[0]
                order_id = session.metadata.get("order_id")
            logger.warning(f"Payment failed for order_id: {order_id}")

        if not order_id:
            logger.error(f"No order_id found for event type: {event['type']}")
            return Response({"error": "No order_id provided"}, status=status.HTTP_200_OK)

        try:
            order = Order.objects.get(id=order_id)
            transact = Transaction.objects.get(order=order)

            with transaction.atomic():
                if event['type'] in ["checkout.session.completed", "checkout.session.async_payment_succeeded", "payment_intent.succeeded"]:
                    order.paid = True
                    payment_intent_id = session.get('payment_intent') if 'session' in locals() else event['data']['object']['id']
                    if payment_intent_id:
                        order.stripe_payment_intent = payment_intent_id
                        transact.stripe_payment_intent = payment_intent_id
                    order.save()
                    transact.status = 'success'
                    transact.save()
                    try:
                        card = Card.objects.get(user=order.user)
                        card.card_products.all().delete()
                    except Card.DoesNotExist:
                        pass
                elif event['type'] == "payment_intent.payment_failed":
                    transact.status = 'failed'
                    transact.save()

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            logger.error(f"Order not found: {order_id}")
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)
        except Transaction.DoesNotExist:
            logger.error(f"Transaction not found for order: {order_id}")
            return Response({"error": "Transaction not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.exception(f"Error processing webhook: {e}")
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        logger.info(f"Ignoring event type: {event['type']}")
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
    permission_classes = [custom_perms.IsStaff]

    @swagger_auto_schema(request_body=FlashSaleAddSerializer)
    def post(self, request, pk):
        try:
            flash_sale = FlashSales.objects.get(pk=pk)
        except FlashSales.DoesNotExist:
            return Response(
                {"error": _("FlashSale topilmadi")}, status=status.HTTP_404_NOT_FOUND
            )

        product_ids = request.data.get("products", [])
        products = Product.objects.filter(id__in=product_ids)
        flash_sale.products.add(*products)
        return Response(
            {"status": _("mahsulotlar qo'shildi")}, status=status.HTTP_200_OK
        )


class FlashSaleRemoveProductsView(APIView):
    def post(self, request, pk):
        try:
            flash_sale = FlashSales.objects.get(pk=pk)
        except FlashSales.DoesNotExist:
            return Response(
                {"error": _("FlashSale topilmadi")}, status=status.HTTP_404_NOT_FOUND
            )

        flash_sale.clear_discount_percent()
        return Response(
            {"status": _("mahsulotlarning foizi 0ga tenglandi")},
            status=status.HTTP_200_OK,
        )


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

    product_param = openapi.Parameter(
        "product",
        openapi.IN_QUERY,
        description=force_str(
            _("Reytingni mahsulot bo‘yicha filtrlash (`?product=12`).")
        ),
        type=openapi.TYPE_INTEGER,
    )
    user_param = openapi.Parameter(
        "user",
        openapi.IN_QUERY,
        description=force_str(
            _("Reytingni foydalanuvchi bo‘yicha filtrlash (`?user=5`).")
        ),
        type=openapi.TYPE_INTEGER,
    )

    @swagger_auto_schema(
        manual_parameters=[product_param, user_param],
        responses={200: StarsSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
        serializer = self.get_serializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        try:
            self.perform_create(serializer)
        except IntegrityError:
            return Response(
                {"message": _("Siz bu mahsulotni avval baholagansiz")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def perform_create(self, serializer):
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.user != request.user and not request.user.is_staff:
            return Response(
                {"detail": _("Ruxsat yo‘q.")}, status=status.HTTP_403_FORBIDDEN
            )
        return super().destroy(request, *args, **kwargs)


class ChangeLanguageView(APIView):
    def post(self, request):
        language = request.data["language"]
        self.request.user.update(language=language)

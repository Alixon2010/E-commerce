from django.contrib.auth import get_user_model, logout
from drf_yasg.utils import swagger_auto_schema
from rest_framework import permissions, status
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from Shop import permissions as custom_perms
from Shop.models import Card, Category, Order, Product
from Shop.serializers import (
    CardSerializer,
    CategorySerializer,
    ChangeOrderStatusSerializer,
    OrderSerializer,
    ProductSerializer,
    RemoveCardSerializer,
    ResetPasswordConfirmSerializer,
    ResetPasswordSerializer,
    ToCardSerializer,
    ToOrderSerializer,
    UserSerializer
)

User = get_user_model()


class CategoryViewSet(ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ProductViewSet(ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer


class Register(APIView):
    @swagger_auto_schema(
        request_body=UserSerializer,
        responses={200: UserSerializer()},
    )
    def post(self, request):
        serializer = UserSerializer(data=request.data)
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

    def post(self, request):
        logout(request)
        return Response({"message": "User logged out!"})


class ResetPassword(APIView):

    @swagger_auto_schema(request_body=ResetPasswordSerializer)
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Reset Password send!"})


class ResetPasswordConfirm(APIView):

    @swagger_auto_schema(request_body=ResetPasswordConfirmSerializer)
    def post(self, request):
        serializer = ResetPasswordConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Password successfully reset!"})


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
        request_body=ToCardSerializer, responses={200: "Savatga qo'shildi"}
    )
    def post(self, request):
        serializer = ToCardSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Product savatga qo`shildi"}, status=status.HTTP_200_OK
        )


class RemoveCardView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=RemoveCardSerializer,
        responses={200: "savatdan olindi"},
    )
    def post(self, request):
        serializer = RemoveCardSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {"message": "Product savatdan olindi"}, status=status.HTTP_200_OK
        )


class ToOrderView(APIView):
    permission_classes = [custom_perms.IsClient]

    @swagger_auto_schema(
        request_body=ToOrderSerializer, responses={200: "buyurtma berildi"}
    )
    def post(self, request):
        serializer = ToOrderSerializer(
            data=request.data, context={"user": request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({"message": "Buyurtma berildi"}, status=status.HTTP_200_OK)


class ChangeOrderStatus(APIView):
    permission_classes = [custom_perms.IsStaff]

    @swagger_auto_schema(
        request_body=ChangeOrderStatusSerializer,
        responses={200: "Status succefuly changed"},
    )
    def post(self, request):
        serializer = ChangeOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"message": "Status succefuly changed"}, status=status.HTTP_200_OK
        )


class OrderListView(ListAPIView):
    queryset = Order.objects.all().prefetch_related("products__product")
    serializer_class = OrderSerializer
    permission_classes = [custom_perms.IsStaff]


class OrderRetrieveView(RetrieveAPIView):
    queryset = Order.objects.all().prefetch_related("products__product")
    serializer_class = OrderSerializer
    permission_classes = [custom_perms.IsStaffOrOwner]
from django.contrib.auth import logout
from rest_framework import viewsets, views, status, permissions
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from Shop import models, serializers, permissions as custom_perms


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = models.Category.objects.all()
    serializer_class = serializers.CategorySerializer

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = models.SubCategory.objects.all()
    serializer_class = serializers.SubCategorySerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = models.Product.objects.all()
    serializer_class = serializers.ProductSerializer

class Register(views.APIView):
    def post(self, request):
        serializer = serializers.UserSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

class UserList(views.APIView):
    def get(self, request):
        users = models.User.objects.all()
        serializer = serializers.UserSerializer(instance=users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

class Logout(views.APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({"message": "User logged out!"})

class ResetPassword(views.APIView):
    def post(self, request):
        serializer = serializers.ResetPasswordSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response({"message": "Reset Password send!"})

class ResetPasswordConfirm(views.APIView):
    def post(self, request):
        serializer = serializers.ResetPasswordConfirmSerializer(data = request.data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response({"message": "Password successfully reset!"})

class CardListView(ListAPIView):
    queryset = models.Card.objects.all().prefetch_related('card_products__product')
    serializer_class = serializers.CardSerializer

class CardRetriveView(RetrieveAPIView):
    queryset = models.Card.objects.all().prefetch_related('card_products__product')
    serializer_class = serializers.CardSerializer

class ToCardView(views.APIView):
    permission_classes = [custom_perms.IsClient]
    def post(self, request):
        serializer = serializers.ToCardSerializer(
            data=request.data,
            context={'user': request.user}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Product savatga qo`shildi'}, status=status.HTTP_200_OK)

class RemoveCardView(views.APIView):
    permission_classes = [custom_perms.IsClient]

    def post(self, request):
        serializer = serializers.RemoveCardSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': 'Product savatdan olindi'}, status=status.HTTP_200_OK)

class ToOrderView(views.APIView):
    permission_classes = [custom_perms.IsClient]

    def post(self, request):
        serializer = serializers.ToOrderSerializer(data=request.data, context={'user': request.user})
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': 'Buyurtma berildi'}, status=status.HTTP_200_OK)

class ChangeOrderStatus(views.APIView):
    permission_classes = [custom_perms.IsStaff]
    def post(self, request):
        serializer = serializers.ChangeOrderStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({'message': 'Status succefuly changed'}, status=status.HTTP_200_OK)


class OrderListView(ListAPIView):
    queryset = models.Order.objects.all().prefetch_related('products__product')
    serializer_class = serializers.OrderSerializer
    permission_classes = [custom_perms.IsStaff]


class OrderRetrieveView(RetrieveAPIView):
    queryset = models.Order.objects.all().prefetch_related('products__product')
    serializer_class = serializers.OrderSerializer
    permission_classes = [custom_perms.IsStaffOrOwner]
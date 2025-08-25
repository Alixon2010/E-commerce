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
    permission_classes = [permissions.IsAuthenticated]

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

class ToCardView(views.APIView):
    def post(self, request):
        serializer = serializers.ToCardSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()


        return Response({'message': 'Product savatga qo`shildi'}, status=status.HTTP_200_OK)


class RemoveCardView(views.APIView):
    def post(self, request):
        serializer = serializers.RemoveCardSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': 'Product savatdan olindi'}, status=status.HTTP_200_OK)

class ToOrderView(views.APIView):
    def post(self, request):
        serializer = serializers.ToOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response({'message': 'Buyurtma berildi'}, status=status.HTTP_200_OK)

class ChangeOrderStatus(views.APIView):

    def post(self, request, order_id, stat):
        try:
            order = models.Order.objects.get(id=order_id)
        except models.Order.DoesNotExist:
            return Response({'message': 'Order not Found'}, status=status.HTTP_404_NOT_FOUND)

        if stat not in ["pending", "paid", "shipped", "delivered", "canceled"]:
            return Response({'message': 'Status xato'}, status=status.HTTP_400_BAD_REQUEST)

        order.status = stat
        order.save()

        return Response({'message': 'Status succefuly changed'}, status=status.HTTP_200_OK)


class OrderListView(ListAPIView):
    queryset = models.Order.objects.all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        orders = models.Order.objects.all()
        serializer = serializers.OrderSerializer(instance=orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = serializers.OrderSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderRetrieveView(RetrieveAPIView):
    queryset = models.Order.objects.all()
    serializer_class = serializers.OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        order = models.Order.objects.get(id=pk)
        serializer = serializers.OrderSerializer(instance=order)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request, pk):
        order = models.Order.objects.get(id=pk)
        serializer = serializers.OrderSerializer(instance=order, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        order = models.Order.objects.get(id=pk)
        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
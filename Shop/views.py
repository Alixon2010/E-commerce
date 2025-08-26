from django.contrib.auth import logout
from rest_framework import viewsets, views, status, permissions
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response

from Shop import models, serializers


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

class CardListView(ListAPIView):
    queryset = models.Card.objects.all().prefetch_related('card_products__product')
    serializer_class = serializers.CardSerializer

class CardRetriveView(RetrieveAPIView):
    queryset = models.Card.objects.all().prefetch_related('card_products__product')
    serializer_class = serializers.CardSerializer
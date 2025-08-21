from rest_framework import viewsets, views, status
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
    def get(self, request):
        users = models.User.objects.all()
        serializer = serializers.UserSerializer(instance=users, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
from unittest.mock import Mock, patch

from rest_framework.test import APITestCase, APIRequestFactory

from Shop.models import Product, FlashSales
from Shop.views import FlashSaleAddProductsView, FlashSaleRemoveProductsView


class FlashSalesViewsTests(APITestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        self.product = Product.objects.create(name="p_test", price=1.0, stock=10)

    def test_add_products_success(self):
        mock_flash = Mock()
        mock_products_rel = Mock()
        mock_flash.products = mock_products_rel

        with patch("Shop.views.FlashSales.objects.get", return_value=mock_flash) as mock_get:
            request = self.factory.post("", {"products": [str(self.product.id)]}, format="json")
            view = FlashSaleAddProductsView.as_view()
            response = view(request, pk=1)

            assert response.status_code == 200
            assert response.data.get("status") == "products added"
            mock_products_rel.add.assert_called()
            mock_get.assert_called_once_with(pk=1)

    def test_add_products_not_found(self):
        with patch("Shop.views.FlashSales.objects.get", side_effect=FlashSales.DoesNotExist):
            request = self.factory.post("", {"products": [str(self.product.id)]}, format="json")
            view = FlashSaleAddProductsView.as_view()
            response = view(request, pk=9999)

            assert response.status_code == 404
            assert response.data.get("error") == "FlashSale not found"

    def test_remove_products_success(self):
        mock_flash = Mock()
        mock_products_rel = Mock()
        mock_flash.products = mock_products_rel

        with patch("Shop.views.FlashSales.objects.get", return_value=mock_flash) as mock_get:
            request = self.factory.post("", {"products": [str(self.product.id)]}, format="json")
            view = FlashSaleRemoveProductsView.as_view()
            response = view(request, pk=1)

            assert response.status_code == 200
            assert response.data.get("status") == "products removed"
            mock_products_rel.remove.assert_called()
            mock_get.assert_called_once_with(pk=1)

    def test_remove_products_not_found(self):
        with patch("Shop.views.FlashSales.objects.get", side_effect=FlashSales.DoesNotExist):
            request = self.factory.post("", {"products": [str(self.product.id)]}, format="json")
            view = FlashSaleRemoveProductsView.as_view()
            response = view(request, pk=9999)

            assert response.status_code == 404
            assert response.data.get("error") == "FlashSale not found"

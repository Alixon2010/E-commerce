import django_filters

from Shop.models import Product


class ProductFilter(django_filters.FilterSet):
    class Meta:
        model = Product
        fields = {
            "category": ["exact"],  # фильтр по точному совпадению
        }

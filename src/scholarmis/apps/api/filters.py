from django_filters import rest_framework as django_filters
from scholarmis.apps.models import App


class AppFilter(django_filters.FilterSet):
    label = django_filters.CharFilter(lookup_expr='icontains')
    is_active = django_filters.BooleanFilter()

    class Meta:
        model = App
        fields = ['label', 'is_active']


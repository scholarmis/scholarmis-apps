from rest_framework import serializers
from scholarmis.apps.models import App


class AppSerializer(serializers.ModelSerializer):
    absolute_url = serializers.ReadOnlyField()

    class Meta:
        model = App
        fields = [
            "id", "label", "name", "verbose_name", "description", 
            "url", "icon",  "absolute_url",
            "is_active", "is_service", "is_default"
        ]


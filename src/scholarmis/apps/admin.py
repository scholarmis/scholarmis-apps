from django.contrib import admin
from unfold.admin import ModelAdmin
from scholarmis.framework.site import is_public_schema
from .models import App


@admin.register(App)
class AppAdmin(ModelAdmin):
    list_display = ["verbose_name", "label", "name", "is_active", "is_default", "is_service", "url", "icon"]
    list_display_links = ["verbose_name"]
    search_fields = ["verbose_name"]
    filter_horizontal = ["permissions",]

    def has_module_permission(self, request) -> bool:
	    return is_public_schema()


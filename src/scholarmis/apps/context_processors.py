from django.apps import apps
from scholarmis.framework.urls import safe_reverse


def app_metadata(request):
    """Expose some settings from django-allauth in templates."""
    resolver_match = getattr(request, "resolver_match", None)
    app_name = None
    app_label = None
    if resolver_match:
        if resolver_match.app_name:
            name = resolver_match.app_name
            config = apps.get_app_config(name)
            app_name = config.verbose_name
            app_label = config.label

    return {
        "app_name": app_name,
        "app_home": safe_reverse("home", app_label)
    }


from django import template 
from django.apps import apps
from django.urls import reverse
from scholarmis.framework.urls import safe_reverse

register = template.Library() 


@register.filter
def get_item(dictionary: dict, key):
    return dictionary.get(key, None)


@register.simple_tag(takes_context=True)
def get_app_verbose_name(context):
    request = context["request"]
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match:
        if resolver_match.app_name:
            app_name = resolver_match.app_name
            app_config = apps.get_app_config(app_name)
            return app_config.verbose_name


@register.simple_tag(takes_context=True)
def app_url(context, view_name, *args, **kwargs):
    request = context["request"]
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match:
        if resolver_match.app_name:
            app_name = resolver_match.app_name
            app_config = apps.get_app_config(app_name)
            namespace = app_config.label
            return safe_reverse(view_name, namespace, args=args)


@register.simple_tag(takes_context=True)
def get_app_icon(context):
    request = context["request"]
    resolver_match = getattr(request, "resolver_match", None)
    if resolver_match:
        if resolver_match.app_name:
            app_name = resolver_match.app_name
            app_config = apps.get_app_config(app_name)
            if hasattr(app_config, "icon"):
                return app_config.icon



@register.simple_tag(takes_context=True)
def app_filter_url(context):
    """
    Returns the current view URL without GET parameters,
    but includes any URL arguments (args and kwargs).
    Handles namespaced URLs too.
    """
    request = context['request']
    resolver_match = request.resolver_match

    # Namespaces
    namespaces = resolver_match.namespaces
    url_name = resolver_match.url_name

    if namespaces:
        namespace_prefix = ":".join(namespaces)
        full_name = f"{namespace_prefix}:{url_name}"
    else:
        full_name = url_name

    # Include positional and keyword arguments if any
    args = resolver_match.args
    kwargs = resolver_match.kwargs

    return reverse(full_name, args=args, kwargs=kwargs)

from django import template
from django.urls import reverse

from portal.role_routing import dashboard_url_for_role

register = template.Library()


@register.inclusion_tag('portal/partials/back_button.html', takes_context=True)
def back_button(context):
    """Botón Volver con respaldo al dashboard del rol autenticado."""
    request = context.get('request')
    if request and request.user.is_authenticated:
        fallback_url = dashboard_url_for_role(request.user.role)
    else:
        fallback_url = reverse('portal:landing')
    return {'fallback_url': fallback_url}

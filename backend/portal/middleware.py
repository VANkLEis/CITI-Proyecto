PRIVATE_PREFIXES = ('/panel/', '/agenda/')


class PrivateNoCacheMiddleware:
    """Evita que el navegador cachee vistas privadas y datos de agenda."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if request.path.startswith(PRIVATE_PREFIXES):
            response['Cache-Control'] = (
                'no-store, no-cache, must-revalidate, max-age=0')
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        return response

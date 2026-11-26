from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = ('pdf', 'doc', 'docx', 'xls', 'xlsx', 'png', 'jpg', 'jpeg')
MAX_ADJUNTO_BYTES = 10 * 1024 * 1024
MAX_REQUEST_BYTES = MAX_ADJUNTO_BYTES + (1024 * 1024)


def validate_adjunto_size(value):
    """Rechaza archivos mayores a 10 MB en el servidor."""
    if value and value.size > MAX_ADJUNTO_BYTES:
        raise ValidationError(
            'El archivo no puede superar 10 MB. '
            'Comprima el documento o divídalo en partes.')

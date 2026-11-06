"""Usuarios de demostración con credenciales fijas para pruebas de portales."""

from accounts.models import Area, CustomUser, Empresa, Role, StudentType

DEMO_PASSWORD = 'CITIPass2026*'

DEMO_USERS = (
    {
        'email': 'coordinador@citi.ucc.edu.co',
        'role': Role.COORDINADOR,
        'first_name': 'María',
        'last_name': 'Coordinadora Sistemas',
        'area': Area.SISTEMAS,
    },
    {
        'email': 'coordinador.civil@citi.ucc.edu.co',
        'role': Role.COORDINADOR,
        'first_name': 'Jorge',
        'last_name': 'Coordinador Civil',
        'area': Area.CIVIL,
    },
    {
        'email': 'docente@citi.ucc.edu.co',
        'role': Role.DOCENTE,
        'first_name': 'Carlos',
        'last_name': 'Docente Sistemas',
        'area': Area.SISTEMAS,
    },
    {
        'email': 'docente.civil@citi.ucc.edu.co',
        'role': Role.DOCENTE,
        'first_name': 'Pedro',
        'last_name': 'Docente Civil',
        'area': Area.CIVIL,
    },
    {
        'email': 'estudiante@citi.ucc.edu.co',
        'role': Role.ESTUDIANTE,
        'first_name': 'Ana',
        'last_name': 'Estudiante Sistemas',
        'area': Area.SISTEMAS,
        'student_type': StudentType.CONSULTOR,
    },
    {
        'email': 'estudiante.civil@citi.ucc.edu.co',
        'role': Role.ESTUDIANTE,
        'first_name': 'Luis',
        'last_name': 'Estudiante Civil',
        'area': Area.CIVIL,
        'student_type': StudentType.CONSULTOR,
    },
    {
        'email': 'cliente@empresatolima.co',
        'role': Role.CLIENTE,
        'first_name': 'Laura',
        'last_name': 'Gerente',
        'empresa_razon_social': 'Empresa Tolima Demo',
        'empresa_nit': '900123456',
    },
)


def ensure_demo_users():
    """Crea usuarios de prueba si aún no existen (idempotente)."""
    for spec in DEMO_USERS:
        email = spec['email'].lower()
        if CustomUser.objects.filter(email=email).exists():
            continue

        extra = {
            'first_name': spec['first_name'],
            'last_name': spec['last_name'],
            'role': spec['role'],
        }
        if spec['role'] == Role.CLIENTE:
            empresa = Empresa.objects.create(
                razon_social=spec.get('empresa_razon_social', 'Empresa demo'),
                nit=spec.get('empresa_nit', ''),
            )
            extra['empresa'] = empresa
        else:
            if 'area' in spec:
                extra['area'] = spec['area']
            if spec['role'] == Role.ESTUDIANTE:
                extra['student_type'] = spec.get('student_type', StudentType.CONSULTOR)

        CustomUser.objects.create_user(email=email, password=DEMO_PASSWORD, **extra)

"""Pruebas de la zona pública y del triage de solicitudes (Fase 05).

Se mantienen separadas de `portal/tests.py` (que cubre el flujo histórico) para
que el build pueda ejecutar ambas sin mezclar responsabilidades.
"""

from datetime import timedelta
import re
from pathlib import Path

from django.conf import settings
from django.contrib.staticfiles import finders
from django.templatetags.static import static
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from accounts.demo_public import LEGACY_IMAGE_PATHS, PROYECTOS, TALLERES
from accounts.models import Area, CustomUser, Empresa, Role
from portal.models import ProyectoPortafolio, Taller
from scheduling.models import (
    CitaAsesoria, FranjaHoraria, LineaAtencion, SolicitudPublica, TipoServicio,
)
from scheduling.subespecialidades import Subespecialidad

PASSWORD = 'DemoPass123!'
DESCRIPCION = (
    'Necesitamos ordenar la operación tecnológica de la organización y definir '
    'un plan de trabajo con prioridades claras para los próximos meses.')


def make_user(email, role, area=None, **kw):
    return CustomUser.objects.create_user(
        email=email, password=PASSWORD, role=role, area=area, **kw)


def make_empresa(nombre='Empresa QA S.A.S.'):
    return Empresa.objects.create(razon_social=nombre, nit='900-000')


def make_cliente(email='cli@qa.local', empresa=None):
    return CustomUser.objects.create_user(
        email=email, password=PASSWORD, role=Role.CLIENTE,
        empresa=empresa or make_empresa())


def make_franja(area=Area.SISTEMAS, horas=48, capacidad=2):
    inicio = (timezone.now() + timedelta(hours=horas)).replace(
        minute=0, second=0, microsecond=0)
    return FranjaHoraria.objects.create(
        inicio=inicio, fin=inicio + timedelta(hours=2),
        area=area, capacidad=capacidad, activa=True)


def make_solicitud(**over):
    datos = {
        'nombre_contacto': 'Ana Pérez',
        'organizacion': 'Fundación Horizonte',
        'email': 'ana@fundacion.org',
        'tipo_solicitante': SolicitudPublica.TipoSolicitante.FUNDACION,
        'tipo_necesidad': SolicitudPublica.TipoNecesidad.ASESORIA,
        'area': Area.SISTEMAS,
        'descripcion': DESCRIPCION,
        'acepta_contacto': True,
    }
    datos.update(over)
    return SolicitudPublica.objects.create(**datos)


class PublicasBaseTests(TestCase):
    """Portada, portafolio, talleres y privacidad sin autenticación."""

    @classmethod
    def setUpTestData(cls):
        cls.proyecto_sis = ProyectoPortafolio.objects.create(
            titulo='Trazabilidad para fundación', linea='sistemas',
            organizacion='Fundación Horizonte', anio=2026,
            resumen='Sistema de seguimiento de casos.', publicado=True)
        cls.proyecto_civil = ProyectoPortafolio.objects.create(
            titulo='Estudio de suelos', linea='civil',
            organizacion='Constructora Andina', anio=2025,
            resumen='Caracterización geotécnica.', publicado=True)
        cls.proyecto_borrador = ProyectoPortafolio.objects.create(
            titulo='Borrador interno', linea='sistemas',
            resumen='No debe publicarse.', publicado=False)
        cls.taller_activo = Taller.objects.create(
            titulo='IA para fundaciones', tematica='Uso responsable de IA',
            descripcion='Taller introductorio.', publico_objetivo='fundaciones',
            duracion='2 sesiones de 90 minutos', nivel='basico',
            puntos_clave=['Qué es la IA', 'Casos de uso', 'Buenas prácticas'])
        cls.taller_inactivo = Taller.objects.create(
            titulo='Taller archivado', tematica='Tema viejo',
            descripcion='No debe mostrarse.', activo=False)

    def test_landing_publica_muestra_ctas_y_videos(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertTemplateUsed(r, 'portal/index.html')
        self.assertContains(r, 'Ingeniería real para resolver')
        self.assertContains(r, 'los retos de tu empresa o comunidad')
        self.assertContains(r, static('images/logo-ucc.png'))
        self.assertContains(r, static('images/favicon-ucc.png'))
        self.assertNotContains(r, 'logo_ucc.png')
        self.assertNotContains(r, 'Logo_ucc.png')
        self.assertContains(r, 'Cuéntanos qué necesitas y agenda tu cita')
        self.assertContains(r, 'Portal académico')
        for name in ('hero-citi.mp4', 'progreso-ingenieria.mp4', 'resultados-impacto.mp4'):
            self.assertContains(r, static(f'videos/{name}'))
        for name in (
            'hero-citi-poster.jpg',
            'progreso-ingenieria-poster.jpg',
            'resultados-impacto-poster.jpg',
        ):
            self.assertContains(r, static(f'images/landing/{name}'))
        self.assertContains(r, 'id="modalidades"')

    def test_landing_sin_copy_asistencialista(self):
        for url in ('/', '/diagnostico/', '/talleres/'):
            html = self.client.get(url).content.decode('utf-8').lower()
            for prohibido in ('gratis', 'gratuita', 'sin costo', 'mínimo costo'):
                self.assertNotIn(prohibido, html, f'{prohibido} aparece en {url}')

    def test_landing_muestra_las_14_especialidades(self):
        r = self.client.get('/')
        etiquetas = list(Subespecialidad.LABELS.values())
        self.assertEqual(len(etiquetas), 14)
        for etiqueta in etiquetas:
            self.assertContains(r, etiqueta)

    def test_portafolio_solo_muestra_publicados(self):
        r = self.client.get(reverse('portal:portafolio'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Trazabilidad para fundación')
        self.assertNotContains(r, 'Borrador interno')

    def test_portafolio_filtra_por_linea(self):
        r = self.client.get(reverse('portal:portafolio'), {'linea': 'civil'})
        self.assertContains(r, 'Estudio de suelos')
        self.assertNotContains(r, 'Trazabilidad para fundación')

    def test_detalle_proyecto_publicado_y_borrador(self):
        self.assertEqual(self.client.get(
            reverse('portal:portafolio_detail', args=[self.proyecto_sis.slug])
        ).status_code, 200)
        self.assertEqual(self.client.get(
            reverse('portal:portafolio_detail', args=[self.proyecto_borrador.slug])
        ).status_code, 404)

    def test_talleres_solo_activos(self):
        r = self.client.get(reverse('portal:talleres'))
        self.assertContains(r, 'IA para fundaciones')
        self.assertNotContains(r, 'Taller archivado')

    def test_privacidad_responde(self):
        r = self.client.get(reverse('portal:privacidad'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Tratamiento de datos personales')

    def test_privacidad_sin_creditos_publicos(self):
        r = self.client.get(reverse('portal:privacidad'))
        self.assertNotContains(r, 'Créditos de imágenes')
        self.assertNotContains(r, 'creditos-imagenes')


class IntakePublicoTests(TestCase):
    """Los formularios públicos crean solicitudes, nunca citas."""

    def _post_diagnostico(self, **over):
        datos = {
            'tipo_solicitante': 'emprendimiento',
            'nombre_contacto': 'Juan Ríos',
            'cargo': 'Fundador',
            'organizacion': 'Ríos Tech',
            'nit': '',
            'email': 'juan@riostech.co',
            'telefono': '3001234567',
            'tipo_necesidad': 'asesoria',
            'area': 'sistemas',
            'descripcion': DESCRIPCION,
            'objetivo': 'Ordenar la operación',
            'turno_preferido': 'manana',
            'modalidad_preferida': 'virtual',
            'acepta_contacto': 'on',
        }
        datos.update(over)
        return self.client.post(reverse('portal:diagnostico'), datos)

    def test_diagnostico_get_ok(self):
        self.assertEqual(
            self.client.get(reverse('portal:diagnostico')).status_code, 200)

    def test_diagnostico_valido_crea_solicitud(self):
        r = self._post_diagnostico()
        self.assertEqual(r.status_code, 302)
        s = SolicitudPublica.objects.get(email='juan@riostech.co')
        self.assertEqual(s.estado, SolicitudPublica.Estado.RECIBIDA)
        self.assertEqual(s.tipo_necesidad, SolicitudPublica.TipoNecesidad.ASESORIA)
        self.assertEqual(s.linea_atencion, LineaAtencion.PROYECCION_SOCIAL)
        self.assertTrue(s.codigo.startswith('SOL-'))
        self.assertFalse(CitaAsesoria.objects.exists())

    def test_diagnostico_consultoria_deriva_linea_profesional(self):
        self._post_diagnostico(tipo_necesidad='consultoria')
        s = SolicitudPublica.objects.get(email='juan@riostech.co')
        self.assertEqual(s.linea_atencion, LineaAtencion.CONSULTORIA_PROFESIONAL)

    def test_descripcion_corta_no_crea(self):
        r = self._post_diagnostico(descripcion='muy corto')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(SolicitudPublica.objects.exists())

    def test_honeypot_no_crea_solicitud(self):
        r = self._post_diagnostico(website='http://spam.example')
        self.assertEqual(r.status_code, 302)
        self.assertFalse(SolicitudPublica.objects.exists())

    def test_duplicado_reciente_no_crea_segunda(self):
        self._post_diagnostico()
        self._post_diagnostico()
        self.assertEqual(
            SolicitudPublica.objects.filter(email='juan@riostech.co').count(), 1)

    def test_taller_solicitud_crea_capacitacion(self):
        taller = Taller.objects.create(
            titulo='Alfabetización digital', tematica='Trámites seguros',
            descripcion='Para personas mayores.', activo=True)
        r = self.client.post(reverse('portal:taller_solicitud_especifico', args=[taller.slug]), {
            'nombre_contacto': 'Marta Gómez',
            'organizacion': 'Club de Pensionados',
            'email': 'marta@club.org',
            'telefono': '3000000000',
            'taller': taller.pk,
            'tema_interes': '',
            'publico_objetivo': 'Personas mayores',
            'numero_participantes': '25',
            'descripcion': DESCRIPCION,
            'turno_preferido': 'tarde',
            'modalidad_preferida': 'presencial',
            'acepta_contacto': 'on',
        })
        self.assertEqual(r.status_code, 302)
        s = SolicitudPublica.objects.get(email='marta@club.org')
        self.assertEqual(s.tipo_necesidad, SolicitudPublica.TipoNecesidad.CAPACITACION)
        self.assertEqual(s.linea_atencion, LineaAtencion.PROYECCION_SOCIAL)
        self.assertEqual(s.taller, taller)


class TriagePermisosTests(TestCase):
    """Alcance por rol y área del panel de solicitudes."""

    @classmethod
    def setUpTestData(cls):
        cls.director = make_user('dir@qa.local', Role.DIRECTOR)
        cls.coord_sis = make_user('cs@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.coord_civ = make_user('cc@qa.local', Role.COORDINADOR, Area.CIVIL)
        cls.docente = make_user('doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.cliente = make_cliente('cli-tri@qa.local')
        cls.sis = make_solicitud(email='sis@x.org', area=Area.SISTEMAS)
        cls.mixto = make_solicitud(email='mix@x.org', area=Area.MIXTO)
        cls.civil = make_solicitud(email='civ@x.org', area=Area.CIVIL)

    def test_anonimo_redirige_a_login(self):
        r = self.client.get(reverse('portal:solicitudes_publicas'))
        self.assertEqual(r.status_code, 302)
        self.assertIn('/cuenta/login/', r['Location'])

    def test_roles_sin_acceso_redirigen(self):
        for usuario in (self.cliente, self.docente):
            self.client.force_login(usuario)
            self.assertEqual(self.client.get(
                reverse('portal:solicitudes_publicas')).status_code, 302)

    def test_coordinador_solo_ve_su_area_y_mixto(self):
        self.client.force_login(self.coord_sis)
        r = self.client.get(reverse('portal:solicitudes_publicas'))
        self.assertContains(r, self.sis.codigo)
        self.assertContains(r, self.mixto.codigo)
        self.assertNotContains(r, self.civil.codigo)

    def test_detalle_de_otra_area_es_404(self):
        self.client.force_login(self.coord_sis)
        self.assertEqual(self.client.get(
            reverse('portal:solicitud_publica_detalle', args=[self.civil.pk])
        ).status_code, 404)

    def test_director_ve_todas(self):
        self.client.force_login(self.director)
        r = self.client.get(reverse('portal:solicitudes_publicas'))
        for solicitud in (self.sis, self.mixto, self.civil):
            self.assertContains(r, solicitud.codigo)


class TriageAprobacionTests(TestCase):
    """Aprobar alcance, clasificar línea y rechazar."""

    @classmethod
    def setUpTestData(cls):
        cls.director = make_user('dir-ap@qa.local', Role.DIRECTOR)
        cls.coord_sis = make_user('cs-ap@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.coord_civ = make_user('cc-ap@qa.local', Role.COORDINADOR, Area.CIVIL)

    def test_aprobar_clasifica_linea_area_y_actor(self):
        s = make_solicitud(email='ap1@x.org', area=Area.MIXTO)
        self.client.force_login(self.director)
        r = self.client.post(
            reverse('portal:solicitud_publica_aprobar', args=[s.pk]),
            {'linea_atencion': 'consultoria_profesional', 'area': 'sistemas',
             'subespecialidad': 'web', 'observaciones': 'Alcance claro.'})
        self.assertEqual(r.status_code, 302)
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.APROBADA)
        self.assertEqual(s.area, Area.SISTEMAS)
        self.assertEqual(s.linea_atencion, LineaAtencion.CONSULTORIA_PROFESIONAL)
        self.assertEqual(s.subespecialidad, 'web')
        self.assertEqual(s.aprobada_por, self.director)
        self.assertIsNotNone(s.aprobada_en)

    def test_coordinador_no_aprueba_area_ajena(self):
        s = make_solicitud(email='ap2@x.org', area=Area.CIVIL)
        self.client.force_login(self.coord_sis)
        r = self.client.post(
            reverse('portal:solicitud_publica_aprobar', args=[s.pk]),
            {'linea_atencion': 'proyeccion_social', 'area': 'sistemas'})
        # Solicitud de otra área: el alcance en servidor la oculta (404), igual
        # que el resto de recursos del portal.
        self.assertEqual(r.status_code, 404)
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.RECIBIDA)

    def test_aprobar_exige_area_academica(self):
        s = make_solicitud(email='ap3@x.org', area=Area.MIXTO)
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_aprobar', args=[s.pk]),
            {'linea_atencion': 'proyeccion_social', 'area': 'mixto'})
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.RECIBIDA)

    def test_rechazar_exige_motivo(self):
        s = make_solicitud(email='ap4@x.org')
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_rechazar', args=[s.pk]), {'motivo': ''})
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.RECIBIDA)

        self.client.post(
            reverse('portal:solicitud_publica_rechazar', args=[s.pk]),
            {'motivo': 'Fuera del alcance del consultorio.'})
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.RECHAZADA)
        self.assertEqual(s.motivo_rechazo, 'Fuera del alcance del consultorio.')

    def test_taller_se_aprueba_sin_cita(self):
        taller = Taller.objects.create(
            titulo='IA para ONG', tematica='Introducción', descripcion='Taller.')
        s = make_solicitud(
            email='ap5@x.org', tipo_necesidad=SolicitudPublica.TipoNecesidad.CAPACITACION,
            taller=taller, tipo_solicitante=SolicitudPublica.TipoSolicitante.FUNDACION)
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_aprobar', args=[s.pk]),
            {'linea_atencion': 'proyeccion_social', 'area': 'sistemas'})
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.APROBADA)
        self.assertFalse(CitaAsesoria.objects.exists())
        self.assertFalse(s.puede_convertirse)

    def test_detalle_marca_en_revision(self):
        s = make_solicitud(email='ap6@x.org')
        self.client.force_login(self.director)
        self.client.get(reverse('portal:solicitud_publica_detalle', args=[s.pk]))
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.EN_REVISION)
        self.assertEqual(s.revisada_por, self.director)


class ConversionTests(TestCase):
    """Conversión explícita solicitud -> cita (solo asesoría/consultoría)."""

    @classmethod
    def setUpTestData(cls):
        cls.director = make_user('dir-cv@qa.local', Role.DIRECTOR)
        cls.coord_sis = make_user('cs-cv@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.docente = make_user('doc-cv@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.cliente_existente = make_cliente(
            'ana@fundacion.org', make_empresa('Fundación Horizonte'))

    def _aprobada(self, **over):
        datos = {
            'estado': SolicitudPublica.Estado.APROBADA,
            'area': Area.SISTEMAS,
            'linea_atencion': LineaAtencion.PROYECCION_SOCIAL,
            'subespecialidad': 'web',
        }
        datos.update(over)
        return make_solicitud(**datos)

    def test_convertir_crea_cita_y_marca_convertida(self):
        s = self._aprobada(email='nuevo@x.org')
        franja = make_franja()
        self.client.force_login(self.director)
        r = self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja.pk})
        self.assertEqual(r.status_code, 302)
        s.refresh_from_db()
        cita = CitaAsesoria.objects.get()
        self.assertEqual(s.estado, SolicitudPublica.Estado.CONVERTIDA)
        self.assertEqual(s.cita_id, cita.pk)
        self.assertEqual(cita.tipo_servicio, TipoServicio.ORIENTACION_TECNICA)
        self.assertEqual(cita.linea_atencion, LineaAtencion.PROYECCION_SOCIAL)
        self.assertEqual(cita.estado, CitaAsesoria.Estado.SOLICITADA)
        self.assertTrue(cita.eventos.filter(tipo='creada').exists())
        self.assertEqual(cita.solicitud_origen, s)

    def test_no_se_convierte_dos_veces(self):
        s = self._aprobada(email='doble@x.org')
        franja = make_franja()
        self.client.force_login(self.director)
        url = reverse('portal:solicitud_publica_convertir', args=[s.pk])
        self.client.post(url, {'franja': franja.pk})
        self.client.post(url, {'franja': franja.pk})
        self.assertEqual(CitaAsesoria.objects.count(), 1)

    def test_vincula_cliente_existente_por_email(self):
        s = self._aprobada(email='ana@fundacion.org')
        franja = make_franja()
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja.pk})
        s.refresh_from_db()
        self.assertEqual(s.cliente, self.cliente_existente)
        self.assertEqual(s.cita.cliente, self.cliente_existente)
        self.assertEqual(CustomUser.objects.filter(role=Role.CLIENTE).count(), 1)

    def test_crea_cliente_inactivo_con_nit_placeholder(self):
        s = self._aprobada(email='sin-nit@x.org', nit='')
        franja = make_franja()
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja.pk})
        s.refresh_from_db()
        creado = CustomUser.objects.get(email='sin-nit@x.org')
        self.assertEqual(creado.role, Role.CLIENTE)
        self.assertFalse(creado.is_active)
        self.assertFalse(creado.has_usable_password())
        self.assertTrue(creado.empresa.nit.startswith('PENDIENTE-'))
        self.assertLessEqual(len(creado.empresa.nit), 20)

    def test_convertir_con_docente_asigna_la_cita(self):
        s = self._aprobada(email='asig@x.org')
        franja = make_franja()
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja.pk, 'docente': self.docente.pk})
        cita = CitaAsesoria.objects.get()
        self.assertEqual(cita.docente_asignado, self.docente)
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)
        self.assertIsNotNone(cita.asignada_en)

    def test_consultoria_usa_tipo_servicio_especializado(self):
        s = self._aprobada(
            email='cons@x.org', linea_atencion=LineaAtencion.CONSULTORIA_PROFESIONAL)
        franja = make_franja()
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja.pk})
        cita = CitaAsesoria.objects.get()
        self.assertEqual(cita.tipo_servicio, TipoServicio.CONSULTORIA_ESPECIALIZADA)
        self.assertEqual(cita.estado, CitaAsesoria.Estado.SOLICITADA)

    def test_franja_de_otra_area_no_convierte(self):
        s = self._aprobada(email='area@x.org', area=Area.SISTEMAS)
        franja_civil = make_franja(area=Area.CIVIL)
        self.client.force_login(self.director)
        self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja_civil.pk})
        self.assertEqual(CitaAsesoria.objects.count(), 0)

    def test_taller_no_se_convierte_en_cita(self):
        s = make_solicitud(
            email='taller@x.org',
            tipo_necesidad=SolicitudPublica.TipoNecesidad.CAPACITACION,
            tema_interes='IA básica',
            estado=SolicitudPublica.Estado.APROBADA)
        franja = make_franja()
        self.client.force_login(self.director)
        r = self.client.post(
            reverse('portal:solicitud_publica_convertir', args=[s.pk]),
            {'franja': franja.pk})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(CitaAsesoria.objects.count(), 0)
        s.refresh_from_db()
        self.assertEqual(s.estado, SolicitudPublica.Estado.APROBADA)


class SeedDemoDataTests(TestCase):
    """El comando de Docker es idempotente y está bloqueado en producción."""

    def test_seed_crea_contenido_publico_y_no_duplica(self):
        from io import StringIO

        from django.core.management import call_command
        from portal.models import ProyectoPortafolio, Taller

        call_command('seed_demo_data', stdout=StringIO())
        proyectos = ProyectoPortafolio.objects.filter(publicado=True).count()
        talleres = Taller.objects.filter(activo=True).count()
        solicitudes = SolicitudPublica.objects.count()

        self.assertEqual(proyectos, 8)
        self.assertEqual(talleres, 6)
        self.assertGreaterEqual(solicitudes, 4)

        estados = set(SolicitudPublica.objects.filter(
            codigo__startswith='DEMO-SOL').values_list('estado', flat=True))
        self.assertIn(SolicitudPublica.Estado.RECIBIDA, estados)
        self.assertIn(SolicitudPublica.Estado.EN_REVISION, estados)
        self.assertIn(SolicitudPublica.Estado.APROBADA, estados)

        call_command('seed_demo_data', stdout=StringIO())
        self.assertEqual(
            ProyectoPortafolio.objects.filter(publicado=True).count(), proyectos)
        self.assertEqual(Taller.objects.filter(activo=True).count(), talleres)
        self.assertEqual(SolicitudPublica.objects.count(), solicitudes)

    def test_seed_funciona_en_produccion(self):
        from io import StringIO

        from django.core.management import call_command

        with self.settings(IS_PRODUCTION=True):
            call_command(
                'seed_demo_data', '--solo-usuarios', stdout=StringIO())

        for email in (
            'director@citi.ucc.edu.co',
            'coordinador@citi.ucc.edu.co',
            'docente@citi.ucc.edu.co',
            'estudiante@citi.ucc.edu.co',
            'cliente@empresa.com',
        ):
            user = CustomUser.objects.get(email=email)
            self.assertTrue(user.is_active, email)
            self.assertTrue(user.check_password('CITIPass2026*'), email)

    def test_seed_completa_puntos_clave_y_no_duplica(self):
        from io import StringIO

        from django.core.management import call_command
        from portal.models import Taller

        call_command('seed_demo_data', stdout=StringIO())
        talleres = list(Taller.objects.filter(activo=True))
        self.assertEqual(len(talleres), 6)
        for taller in talleres:
            self.assertEqual(len(taller.puntos_clave_validos), 3, taller.slug)

        # Simula un taller sembrado antes de existir el campo: se rellena.
        primero = talleres[0]
        primero.puntos_clave = []
        primero.save(update_fields=['puntos_clave'])
        call_command('seed_demo_data', stdout=StringIO())
        primero.refresh_from_db()
        self.assertEqual(len(primero.puntos_clave_validos), 3)
        self.assertEqual(Taller.objects.filter(activo=True).count(), 6)

    def test_seed_equilibrado_sistemas_civil(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_demo_data', stdout=StringIO())
        self.assertEqual(
            ProyectoPortafolio.objects.filter(publicado=True, linea='civil').count(), 4)
        self.assertEqual(
            ProyectoPortafolio.objects.filter(publicado=True)
            .exclude(linea='civil').count(), 4)
        self.assertEqual(Taller.objects.filter(activo=True, area='civil').count(), 3)
        self.assertEqual(Taller.objects.filter(activo=True, area='sistemas').count(), 3)

    def test_seed_migra_imagenes_legacy(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_demo_data', stdout=StringIO())
        proyecto = ProyectoPortafolio.objects.get(slug='trazabilidad-casos-fundacion')
        proyecto.imagen_static = 'images/landing/area-sistemas.jpg'
        proyecto.save(update_fields=['imagen_static'])

        call_command('seed_demo_data', stdout=StringIO())
        proyecto.refresh_from_db()
        self.assertEqual(
            proyecto.imagen_static,
            'images/landing/proyecto-trazabilidad-ong.jpg')
        self.assertIsNotNone(finders.find(proyecto.imagen_static))

    def test_seed_respeta_imagen_personalizada(self):
        from io import StringIO

        from django.core.management import call_command

        call_command('seed_demo_data', stdout=StringIO())
        proyecto = ProyectoPortafolio.objects.get(slug='trazabilidad-casos-fundacion')
        proyecto.imagen_static = 'images/landing/mi-imagen-admin.jpg'
        proyecto.save(update_fields=['imagen_static'])

        call_command('seed_demo_data', stdout=StringIO())
        proyecto.refresh_from_db()
        self.assertEqual(
            proyecto.imagen_static, 'images/landing/mi-imagen-admin.jpg')


class TarjetasPublicasTests(TestCase):
    """Tarjetas uniformes, temario visible y alcance explícito."""

    @classmethod
    def setUpTestData(cls):
        cls.proyecto = ProyectoPortafolio.objects.create(
            titulo='Proyecto con foto vertical', linea='sistemas',
            resumen='Resumen de prueba para la tarjeta.', publicado=True)
        cls.taller = Taller.objects.create(
            titulo='Taller con temario', tematica='Bajada del taller.',
            descripcion='Descripción larga.', publico_objetivo='fundaciones',
            area='sistemas', duracion='2 sesiones', nivel='basico',
            puntos_clave=['Punto uno', 'Punto dos', 'Punto tres'])
        cls.taller_civil = Taller.objects.create(
            titulo='Taller civil de prueba', tematica='Obra y vivienda.',
            descripcion='Descripción larga.', publico_objetivo='pymes',
            area='civil', duracion='1 sesión', nivel='basico',
            puntos_clave=['Punto A', 'Punto B', 'Punto C'])

    def test_tarjeta_portafolio_usa_contenedor_uniforme(self):
        r = self.client.get(reverse('portal:portafolio'))
        self.assertContains(r, 'pub-card-media')
        self.assertContains(r, 'pub-card-summary')

    def test_tarjeta_taller_muestra_tres_puntos_y_nivel(self):
        r = self.client.get(reverse('portal:talleres'))
        self.assertContains(r, 'pub-workshop-points')
        for punto in ('Punto uno', 'Punto dos', 'Punto tres'):
            self.assertContains(r, punto)
        self.assertContains(r, 'Desde cero')

    def test_tarjeta_taller_enlaza_con_query_param(self):
        r = self.client.get(reverse('portal:talleres'))
        self.assertContains(r, f'?taller={self.taller.slug}')

    def test_talleres_muestran_ambas_carreras(self):
        r = self.client.get(reverse('portal:talleres'))
        self.assertContains(r, 'Ingeniería de Sistemas')
        self.assertContains(r, 'Ingeniería Civil')

    def test_landing_muestra_alcance_y_ejemplos(self):
        r = self.client.get('/')
        for texto in ('Ruta 1', 'Ruta 2', 'Incluye', 'No incluye',
                      'Así se ve en la práctica',
                      'Fisuras y aguas lluvias en una sede comunitaria',
                      'Charla de IA para una fundación',
                      'Emprendimiento juvenil: validar antes de desarrollar',
                      'Vivienda, pymes y adultos mayores'):
            self.assertContains(r, texto)

    def test_landing_ejemplos_incluyen_ambas_carreras(self):
        r = self.client.get('/')
        for texto in ('Ingeniería Civil · Proyección social',
                      'Ingeniería de Sistemas · Capacitación',
                      'Ingeniería de Sistemas · Diagnóstico',
                      'Civil + Sistemas · Talleres'):
            self.assertContains(r, texto)


class TalleresFiltroTests(TestCase):
    """Los cuatro grupos de público agrupan los cinco códigos del modelo."""

    @classmethod
    def setUpTestData(cls):
        cls.fundacion = Taller.objects.create(
            titulo='Taller fundaciones', tematica='x', descripcion='y',
            publico_objetivo='fundaciones')
        cls.pyme = Taller.objects.create(
            titulo='Taller pyme', tematica='x', descripcion='y',
            publico_objetivo='pymes')
        cls.comunidad = Taller.objects.create(
            titulo='Taller comunidad', tematica='x', descripcion='y',
            publico_objetivo='comunidad')

    def test_filtra_grupo_pymes_comunidad(self):
        r = self.client.get(reverse('portal:talleres'), {'publico': 'pymes_comunidad'})
        self.assertContains(r, 'Taller pyme')
        self.assertContains(r, 'Taller comunidad')
        self.assertNotContains(r, 'Taller fundaciones')

    def test_filtra_fundaciones(self):
        r = self.client.get(reverse('portal:talleres'), {'publico': 'fundaciones'})
        self.assertContains(r, 'Taller fundaciones')
        self.assertNotContains(r, 'Taller pyme')

    def test_preselecciona_taller_por_query_param(self):
        r = self.client.get(reverse('portal:taller_solicitud'),
                            {'taller': self.fundacion.slug})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context['form'].initial.get('taller'), self.fundacion)

    def test_slug_inexistente_no_rompe(self):
        r = self.client.get(reverse('portal:taller_solicitud'),
                            {'taller': 'no-existe'})
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.context['form'].initial.get('taller'))


class DiagnosticoPrevioTests(TestCase):
    """Sesión previa: madurez, tres rutas y clasificación automática."""

    def _post(self, **over):
        datos = {
            'tipo_solicitante': 'empresa',
            'nombre_contacto': 'Ana Pérez',
            'cargo': 'Gerente',
            'organizacion': 'Empresa Demo',
            'nit': '',
            'email': 'ana@empresa.co',
            'telefono': '3000000000',
            'tipo_necesidad': 'asesoria',
            'madurez': 'idea',
            'tema_interes': '',
            'area': 'sistemas',
            'descripcion': DESCRIPCION,
            'objetivo': 'Ordenar la operación',
            'turno_preferido': 'manana',
            'modalidad_preferida': 'virtual',
            'acepta_contacto': 'on',
        }
        datos.update(over)
        return self.client.post(reverse('portal:diagnostico'), datos)

    def test_formulario_incluye_madurez_y_tres_necesidades(self):
        r = self.client.get(reverse('portal:diagnostico'))
        self.assertContains(r, 'Sesión Previa de Diagnóstico')
        self.assertContains(r, '30–45')
        for etiqueta in ('Orientación / Diagnóstico inicial',
                         'Desarrollo o estudio técnico a medida',
                         'Charla, capacitación o taller grupal',
                         'Solo tengo una idea inicial'):
            self.assertContains(r, etiqueta)

    def test_guarda_madurez(self):
        self._post(madurez='requerimientos')
        s = SolicitudPublica.objects.get(email='ana@empresa.co')
        self.assertEqual(s.madurez, 'requerimientos')

    def test_capacitacion_sin_tema_no_crea(self):
        r = self._post(tipo_necesidad='capacitacion', tema_interes='')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(SolicitudPublica.objects.exists())

    def test_capacitacion_con_tema_crea_social(self):
        self._post(tipo_necesidad='capacitacion', tema_interes='IA para el equipo')
        s = SolicitudPublica.objects.get(email='ana@empresa.co')
        self.assertEqual(s.tipo_necesidad, 'capacitacion')
        self.assertEqual(s.linea_atencion, LineaAtencion.PROYECCION_SOCIAL)

    def test_consultoria_con_requerimientos_es_profesional(self):
        self._post(tipo_necesidad='consultoria', madurez='requerimientos')
        s = SolicitudPublica.objects.get(email='ana@empresa.co')
        self.assertEqual(s.linea_atencion, LineaAtencion.CONSULTORIA_PROFESIONAL)
        self.assertEqual(s.madurez, 'requerimientos')


class TriageFiltroSugeridoTests(TestCase):
    """El detalle privado muestra la pre-clasificación y las discrepancias."""

    @classmethod
    def setUpTestData(cls):
        cls.director = make_user('dir-fs@qa.local', Role.DIRECTOR)
        cls.solicitud = make_solicitud(
            email='fs@x.org',
            tipo_necesidad=SolicitudPublica.TipoNecesidad.CONSULTORIA,
            madurez=SolicitudPublica.Madurez.IDEA,
            estado=SolicitudPublica.Estado.RECIBIDA)

    def test_detalle_muestra_filtro_sugerido(self):
        self.client.force_login(self.director)
        r = self.client.get(reverse('portal:solicitud_publica_detalle',
                                    args=[self.solicitud.pk]))
        self.assertContains(r, 'Diagnóstico de Filtro Sugerido')
        self.assertContains(r, 'Consultoría Profesional')
        self.assertContains(r, 'Solo tengo una idea inicial')
        self.assertContains(r, 'Convertir en cita')

    def test_avisa_clasificacion_manual_distinta(self):
        s = make_solicitud(
            email='manual@x.org',
            tipo_necesidad=SolicitudPublica.TipoNecesidad.CONSULTORIA,
            linea_atencion=LineaAtencion.PROYECCION_SOCIAL)
        self.client.force_login(self.director)
        r = self.client.get(reverse('portal:solicitud_publica_detalle', args=[s.pk]))
        self.assertContains(r, 'Clasificada manualmente')

    def test_anonimo_no_ve_el_filtro(self):
        r = self.client.get(reverse('portal:solicitud_publica_detalle',
                                    args=[self.solicitud.pk]))
        self.assertEqual(r.status_code, 302)


class MediaPublicaTests(TestCase):
    """Imágenes únicas, pósters y videos locales, sin CDNs externos."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='media-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=Empresa.objects.create(razon_social='Media SA', nit='900-123'))

    def test_imagenes_de_tarjetas_son_unicas_y_existen(self):
        paths = [p['imagen_static'] for p in PROYECTOS]
        paths += [t['imagen_static'] for t in TALLERES]
        self.assertEqual(len(paths), 14)
        self.assertEqual(len(set(paths)), 14)
        for path in paths:
            self.assertIsNotNone(finders.find(path), path)
            with Image.open(Path(settings.BASE_DIR) / 'static' / path) as image:
                self.assertEqual(image.size, (1600, 1000), path)

    def test_imagenes_heredadas_eliminadas(self):
        for path in LEGACY_IMAGE_PATHS:
            self.assertFalse(
                (Path(settings.BASE_DIR) / 'static' / path).exists(), path)

    def test_posters_unicos_y_sin_colision_con_tarjetas(self):
        r = self.client.get('/')
        html = r.content.decode('utf-8')
        posters = re.findall(r'poster="([^"]+)"', html)
        self.assertEqual(len(posters), 3)
        self.assertEqual(len(set(posters)), 3)

        poster_names = {
            'hero-citi-poster.jpg',
            'progreso-ingenieria-poster.jpg',
            'resultados-impacto-poster.jpg',
        }
        poster_paths = {
            f'images/landing/{name}' for name in poster_names
        }
        self.assertEqual(
            set(posters),
            {static(path) for path in poster_paths},
        )

        cards = {p['imagen_static'] for p in PROYECTOS}
        cards |= {t['imagen_static'] for t in TALLERES}
        self.assertFalse(cards & poster_paths)
        for path in poster_paths:
            self.assertIsNotNone(finders.find(path), path)
            with Image.open(Path(settings.BASE_DIR) / 'static' / path) as image:
                self.assertGreaterEqual(image.width, 1600, path)
                self.assertGreaterEqual(image.height, 900, path)

    def test_mp4_existen_pesan_limite_y_tienen_firma_ftyp(self):
        limites = {
            'hero-citi.mp4': 6,
            'progreso-ingenieria.mp4': 4,
            'resultados-impacto.mp4': 4,
        }
        for name, max_mb in limites.items():
            path = Path(settings.BASE_DIR) / 'static' / 'videos' / name
            self.assertTrue(path.exists(), name)
            self.assertLessEqual(path.stat().st_size, max_mb * 1024 * 1024, name)
            self.assertEqual(path.read_bytes()[4:8], b'ftyp', name)

    def test_sin_cdn_externo_y_assets_vendorizados(self):
        self.client.force_login(self.cliente)
        for url in ('/', reverse('portal:cliente_dashboard')):
            r = self.client.get(url)
            self.assertNotContains(r, 'fonts.googleapis.com')
            self.assertNotContains(r, 'cdn.jsdelivr.net')
        for path in (
            'vendor/fullcalendar/6.1.15/index.global.min.js',
            'vendor/fullcalendar/6.1.15/LICENSE.md',
            'fonts/open-sans/open-sans-latin-var.woff2',
            'fonts/open-sans/OFL.txt',
            'css/fonts.css',
        ):
            self.assertIsNotNone(finders.find(path), path)

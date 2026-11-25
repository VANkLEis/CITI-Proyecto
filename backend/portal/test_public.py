"""Pruebas de la zona pública y del triage de solicitudes (Fase 05).

Se mantienen separadas de `portal/tests.py` (que cubre el flujo histórico) para
que el build pueda ejecutar ambas sin mezclar responsabilidades.
"""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

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
            descripcion='Taller introductorio.', publico_objetivo='fundaciones')
        cls.taller_inactivo = Taller.objects.create(
            titulo='Taller archivado', tematica='Tema viejo',
            descripcion='No debe mostrarse.', activo=False)

    def test_landing_publica_muestra_ctas_y_videos(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Transformamos desafíos reales')
        self.assertContains(r, 'Agenda una sesión de diagnóstico estratégico')
        self.assertContains(r, 'Portal académico')
        self.assertContains(r, 'hero-citi.mp4')
        self.assertContains(r, 'progreso-ingenieria.mp4')
        self.assertContains(r, 'resultados-impacto.mp4')
        self.assertContains(r, 'id="modalidades"')

    def test_landing_sin_copy_asistencialista(self):
        html = self.client.get('/').content.decode('utf-8').lower()
        for prohibido in ('gratis', 'gratuita', 'sin costo', 'mínimo costo'):
            self.assertNotIn(prohibido, html)

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
        proyectos = ProyectoPortafolio.objects.count()
        talleres = Taller.objects.count()
        solicitudes = SolicitudPublica.objects.count()

        self.assertGreaterEqual(proyectos, 6)
        self.assertGreaterEqual(talleres, 4)
        self.assertGreaterEqual(solicitudes, 4)

        estados = set(SolicitudPublica.objects.filter(
            codigo__startswith='DEMO-SOL').values_list('estado', flat=True))
        self.assertIn(SolicitudPublica.Estado.RECIBIDA, estados)
        self.assertIn(SolicitudPublica.Estado.EN_REVISION, estados)
        self.assertIn(SolicitudPublica.Estado.APROBADA, estados)

        call_command('seed_demo_data', stdout=StringIO())
        self.assertEqual(ProyectoPortafolio.objects.count(), proyectos)
        self.assertEqual(Taller.objects.count(), talleres)
        self.assertEqual(SolicitudPublica.objects.count(), solicitudes)

    def test_seed_bloqueado_en_produccion(self):
        from io import StringIO

        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.settings(IS_PRODUCTION=True):
            with self.assertRaises(CommandError):
                call_command('seed_demo_data', stdout=StringIO())

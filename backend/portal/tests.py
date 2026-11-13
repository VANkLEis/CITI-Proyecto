from datetime import datetime, time, timedelta
from decimal import Decimal

from django.db import transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import Area, CustomUser, Empresa, Role, StudentType
from portal import indicadores
from scheduling.models import CitaAsesoria, CitaEvento, FranjaHoraria

PASSWORD = 'DemoPass123!'


def make_user(email, role, area=None, **kw):
    return CustomUser.objects.create_user(
        email=email, password=PASSWORD, role=role, area=area, **kw
    )


def make_empresa(nombre='Empresa QA S.A.S.'):
    return Empresa.objects.create(razon_social=nombre, nit='900-000')


def make_franja(area=Area.SISTEMAS, horas_al_futuro=48, capacidad=2, activa=True):
    """Franja futura alineada a hora exacta, en la zona horaria de Django."""
    inicio = (timezone.now() + timedelta(hours=horas_al_futuro)).replace(
        minute=0, second=0, microsecond=0)
    if inicio <= timezone.now():
        inicio += timedelta(hours=1)
    return FranjaHoraria.objects.create(
        inicio=inicio, fin=inicio + timedelta(hours=2),
        area=area, capacidad=capacidad, activa=activa,
    )


class RoleAccessMatrixTests(TestCase):
    """B-5 P0-1 / regresión SEG-01: matriz rol × portal sin 500 y sin escapes."""

    DASHBOARDS = {
        Role.DIRECTOR: 'portal:director_dashboard',
        Role.COORDINADOR: 'portal:coordinador_dashboard',
        Role.DOCENTE: 'portal:docente_dashboard',
        Role.ESTUDIANTE: 'portal:estudiante_dashboard',
        Role.CLIENTE: 'portal:cliente_dashboard',
    }

    @classmethod
    def setUpTestData(cls):
        cls.users = {
            Role.DIRECTOR: make_user('dir@qa.local', Role.DIRECTOR),
            Role.COORDINADOR: make_user('coord@qa.local', Role.COORDINADOR, Area.SISTEMAS),
            Role.DOCENTE: make_user('doc@qa.local', Role.DOCENTE, Area.SISTEMAS),
            # estudiante sin student_type inicial: la señal lo pone en consultor
            Role.ESTUDIANTE: None,
            Role.CLIENTE: None,
        }
        est = CustomUser.objects.create_user(
            email='est@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR,
        )
        cls.users[Role.ESTUDIANTE] = est
        cls.users[Role.CLIENTE] = CustomUser.objects.create_user(
            email='cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa(),
        )

    def test_anonimo_redirect_a_login(self):
        for role, url_name in self.DASHBOARDS.items():
            r = self.client.get(reverse(url_name))
            self.assertEqual(r.status_code, 302, f'{role}: esperaba 302')
            self.assertIn('/cuenta/login/', r['Location'])

    def test_matriz_rol_x_portal(self):
        for login_role, url_name in self.DASHBOARDS.items():
            self.client.force_login(self.users[login_role])
            for target_role, target_name in self.DASHBOARDS.items():
                r = self.client.get(reverse(target_name))
                if target_role == login_role:
                    self.assertEqual(r.status_code, 200,
                                     f'{login_role} no accede a su portal ({r.status_code})')
                else:
                    # B-1: 302 al propio dashboard, nunca 500.
                    self.assertEqual(r.status_code, 302,
                                     f'{login_role}->{target_role}: {r.status_code}')
                    self.assertEqual(
                        r['Location'], reverse(self.DASHBOARDS[login_role]),
                        f'{login_role}->{target_role} no redirige al portal propio',
                    )

    def test_director_ve_detalle_en_solo_lectura(self):
        self.client.force_login(self.users[Role.DIRECTOR])
        cita = CitaAsesoria.objects.create(
            franja=make_franja(Area.SISTEMAS),
            cliente=self.users[Role.CLIENTE],
            subespecialidad='web',
            asunto='Detalle para dirección',
        )
        r = self.client.get(reverse('portal:cita_detalle', args=[cita.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Detalle para dirección')
        self.assertContains(r, 'solo lectura')
        self.assertNotContains(r, 'Confirmar asignación')
        self.assertNotContains(r, 'Guardar cambios')

    def test_login_con_portal_incorrecto_no_autentica(self):
        r = self.client.post(
            reverse('accounts:login'),
            {'username': 'cli@qa.local', 'password': PASSWORD, 'expected_role': 'docente'},
        )
        self.assertEqual(r.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertContains(r, 'pertenece al portal')

    def test_login_rol_correcto_redirige_a_su_portal(self):
        r = self.client.post(
            reverse('accounts:login'),
            {'username': 'cli@qa.local', 'password': PASSWORD, 'expected_role': 'cliente'},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r['Location'], reverse('portal:cliente_dashboard'))


class ReservasApiTests(TestCase):
    """B-5 P0-2: reserva válida, duplicada, por capacidad y validaciones de área."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente1 = CustomUser.objects.create_user(
            email='c1@qa.local', password=PASSWORD, role=Role.CLIENTE, empresa=make_empresa('E1'))
        cls.cliente2 = CustomUser.objects.create_user(
            email='c2@qa.local', password=PASSWORD, role=Role.CLIENTE, empresa=make_empresa('E2'))
        cls.franja = make_franja(Area.SISTEMAS, capacidad=1)
        cls.franja_civ = make_franja(Area.CIVIL, horas_al_futuro=72, capacidad=2)

    def _post(self, cliente, payload):
        self.client.force_login(cliente)
        return self.client.post('/agenda/api/reservar/', payload)

    def test_reserva_valida(self):
        r = self._post(self.cliente1, {'franja_id': self.franja.pk, 'asunto': 'A',
                                       'subespecialidad': 'web', 'tipo_servicio': 'orientacion'})
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data['ok'])
        cita = CitaAsesoria.objects.get(pk=data['cita_id'])
        self.assertEqual(cita.estado, CitaAsesoria.Estado.SOLICITADA)
        self.assertEqual(cita.cliente, self.cliente1)

    def test_reserva_duplicada_misma_cliente_franja(self):
        self._post(self.cliente1, {'franja_id': self.franja.pk, 'subespecialidad': 'web'})
        r = self._post(self.cliente1, {'franja_id': self.franja.pk, 'subespecialidad': 'web'})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(CitaAsesoria.objects.filter(franja=self.franja).count(), 1)

    def test_capacidad_bloquea_a_segundo_cliente_secuencial(self):
        self._post(self.cliente1, {'franja_id': self.franja.pk, 'subespecialidad': 'web'})
        r = self._post(self.cliente2, {'franja_id': self.franja.pk, 'subespecialidad': 'web'})
        self.assertEqual(r.status_code, 409)  # capacidad 1 ya ocupada

    def test_subespecialidad_de_otra_area_rechazada(self):
        r = self._post(self.cliente1, {'franja_id': self.franja_civ.pk, 'subespecialidad': 'web'})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(CitaAsesoria.objects.exists())

    def test_franja_inactiva_no_reservable(self):
        inactiva = make_franja(Area.SISTEMAS, capacidad=1, activa=False)
        r = self._post(self.cliente1, {'franja_id': inactiva.pk, 'subespecialidad': 'web'})
        self.assertEqual(r.status_code, 404)

    def test_franja_pasada_no_reservable(self):
        tz = timezone.get_current_timezone()
        pasada = FranjaHoraria.objects.create(
            inicio=timezone.make_aware(datetime.combine(timezone.localdate() - timedelta(days=3),
                                                        time(9, 0)), tz),
            fin=timezone.make_aware(datetime.combine(timezone.localdate() - timedelta(days=3),
                                                     time(11, 0)), tz),
            area=Area.SISTEMAS, capacidad=2,
        )
        r = self._post(self.cliente1, {'franja_id': pasada.pk, 'subespecialidad': 'web'})
        self.assertEqual(r.status_code, 409)

    def test_eventos_sin_end_400(self):
        self.client.force_login(self.cliente1)
        r = self.client.get('/agenda/api/eventos/?start=2026-01-01T00:00:00')
        self.assertEqual(r.status_code, 400)

    def test_eventos_anonimo_y_otro_rol(self):
        r = self.client.get('/agenda/api/eventos/')
        self.assertEqual(r.status_code, 302)  # login
        self.client.force_login(self.cliente1)
        docente = make_user('doc2@qa.local', Role.DOCENTE, Area.SISTEMAS)
        self.client.force_login(docente)
        r = self.client.get('/agenda/api/eventos/')
        self.assertEqual(r.status_code, 302)  # regresión B-1: sin 500
        self.assertEqual(r['Location'], reverse('portal:docente_dashboard'))

    def test_eventos_lista_franja_disponible(self):
        from urllib.parse import urlencode
        self.client.force_login(self.cliente1)
        qs = urlencode({'start': self.franja.inicio.isoformat(),
                        'end': (self.franja.fin + timedelta(days=1)).isoformat()})
        r = self.client.get(f'/agenda/api/eventos/?{qs}')
        self.assertEqual(r.status_code, 200)
        eventos = r.json()
        ev = next(e for e in eventos if e['id'] == f'franja-{self.franja.pk}')
        # Paleta UCC: Sistemas = azul diversidad
        self.assertEqual(ev['backgroundColor'], '#00acc9')
        self.assertEqual(ev['textColor'], '#062a33')

        qs2 = urlencode({'start': self.franja_civ.inicio.isoformat(),
                         'end': (self.franja_civ.fin + timedelta(days=1)).isoformat()})
        r2 = self.client.get(f'/agenda/api/eventos/?{qs2}')
        ev2 = next(e for e in r2.json() if e['id'] == f'franja-{self.franja_civ.pk}')
        # Paleta UCC: Civil = verde solidario
        self.assertEqual(ev2['backgroundColor'], '#80ba27')
        self.assertEqual(ev2['textColor'], '#1f3307')


class StateMachineTests(TestCase):
    """B-5 P0-3: transiciones permitidas/denegadas (comportamiento vigente)."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='cli2@qa.local', password=PASSWORD, role=Role.CLIENTE, empresa=make_empresa())
        cls.docente = make_user('doc3@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.estudiante = CustomUser.objects.create_user(
            email='est3@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        cls.coordinador = make_user('coord3@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.franja = make_franja(Area.SISTEMAS)
        cls.cita = CitaAsesoria.objects.create(
            franja=cls.franja, cliente=cls.cliente, subespecialidad='web',
            tipo_servicio='especializada', asunto='QA')

    def _nueva_cita_asignada(self):
        f = make_franja(Area.SISTEMAS, horas_al_futuro=120)
        cita = CitaAsesoria.objects.create(franja=f, cliente=self.cliente,
                                           subespecialidad='web', asunto='QA2')
        cita.docente_asignado = self.docente
        cita.estado = CitaAsesoria.Estado.ASIGNADA
        cita.full_clean()
        cita.save()
        return cita

    def test_solicitada_a_asignada_por_coordinador(self):
        self.client.force_login(self.coordinador)
        r = self.client.post(
            reverse('portal:coordinador_asignar', args=[self.cita.pk]),
            {'docente_id': self.docente.pk, 'estudiante_id': ''},
        )
        self.assertEqual(r.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, CitaAsesoria.Estado.ASIGNADA)
        self.assertEqual(self.cita.docente_asignado, self.docente)

    def test_asignacion_sin_docente_ni_tutor_falla(self):
        self.client.force_login(self.coordinador)
        r = self.client.post(
            reverse('portal:coordinador_asignar', args=[self.cita.pk]),
            {'docente_id': '', 'estudiante_id': ''},
        )
        self.assertEqual(r.status_code, 200)  # re-render con error
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, CitaAsesoria.Estado.SOLICITADA)

    def test_docente_avanza_en_proceso_y_finalizada(self):
        cita = self._nueva_cita_asignada()
        self.client.force_login(self.docente)
        r = self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                             {'accion': 'estado_rapido', 'nuevo_estado': 'en_proceso'})
        self.assertEqual(r.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.EN_PROCESO)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'estado_rapido', 'nuevo_estado': 'finalizada'})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.FINALIZADA)

    def test_docente_no_puede_cancelar(self):
        cita = self._nueva_cita_asignada()
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'estado_rapido', 'nuevo_estado': 'cancelada'})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)
        r = self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                             {'accion': 'gestionar', 'estado': 'cancelada',
                              'resumen_cierre': '', 'estudiante_apoyo': ''})
        self.assertEqual(r.status_code, 200)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)

    def test_docente_no_puede_volver_a_solicitada(self):
        cita = self._nueva_cita_asignada()
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'gestionar', 'estado': 'solicitada',
                          'resumen_cierre': '', 'estudiante_apoyo': ''})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)

    def test_cliente_no_modifica_estado(self):
        # El cliente no tiene ningún endpoint que cambie estado; feedback solo
        # califica citas FINALIZADAS.
        cita = self._nueva_cita_asignada()
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_feedback', args=[cita.pk]),
                             {'calificacion': 5, 'comentario_cliente': 'x'})
        self.assertEqual(r.status_code, 404)  # aún no finalizada

    def test_tutor_no_elegible_no_asignable_por_docente(self):
        cita = self._nueva_cita_asignada()
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'gestionar', 'estado': 'asignada',
                          'resumen_cierre': '', 'estudiante_apoyo': self.estudiante.pk})
        cita.refresh_from_db()
        self.assertIsNone(cita.estudiante_apoyo)  # consultor sin requisitos: rechazado


class IdorTests(TestCase):
    """B-5 P0-4: protección IDOR en solicitudes/detalle/acta/bitácora/feedback."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente_a = CustomUser.objects.create_user(
            email='ca@qa.local', password=PASSWORD, role=Role.CLIENTE, empresa=make_empresa('A'))
        cls.cliente_b = CustomUser.objects.create_user(
            email='cb@qa.local', password=PASSWORD, role=Role.CLIENTE, empresa=make_empresa('B'))
        cls.docente_a = make_user('da@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.docente_b = make_user('db@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.coord_sis = make_user('cs@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.coord_civ = make_user('cc@qa.local', Role.COORDINADOR, Area.CIVIL)
        cls.est_a = CustomUser.objects.create_user(
            email='ea@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        f_sis = make_franja(Area.SISTEMAS)
        f_civ = make_franja(Area.CIVIL, horas_al_futuro=96)
        cls.cita_sis = CitaAsesoria.objects.create(
            franja=f_sis, cliente=cls.cliente_a, subespecialidad='web', asunto='SIS',
            estado=CitaAsesoria.Estado.ASIGNADA, docente_asignado=cls.docente_a)
        cls.cita_civ = CitaAsesoria.objects.create(
            franja=f_civ, cliente=cls.cliente_b, subespecialidad='vias', asunto='CIV',
            estado=CitaAsesoria.Estado.ASIGNADA, docente_asignado=cls.docente_b)

    def test_docente_b_no_ve_cita_de_docente_a(self):
        self.client.force_login(self.docente_b)
        for url in (f'/panel/cita/{self.cita_sis.pk}/detalle/',
                    reverse('portal:docente_caso_detalle', args=[self.cita_sis.pk]),
                    reverse('portal:docente_generar_acta', args=[self.cita_sis.pk])):
            self.assertEqual(self.client.get(url).status_code, 404, url)

    def test_coordinador_aislado_por_area(self):
        self.client.force_login(self.coord_sis)
        self.assertEqual(self.client.get(
            reverse('portal:coordinador_asignar', args=[self.cita_civ.pk])).status_code, 404)
        self.assertEqual(self.client.get(
            f'/panel/cita/{self.cita_civ.pk}/detalle/').status_code, 404)

    def test_cliente_no_ve_cita_ajena(self):
        self.client.force_login(self.cliente_a)
        self.assertEqual(self.client.get(
            f'/panel/cita/{self.cita_civ.pk}/detalle/').status_code, 404)
        self.assertEqual(self.client.get(
            reverse('portal:cliente_feedback', args=[self.cita_civ.pk])).status_code, 404)

    def test_estudiante_no_ve_cita_sin_asignacion(self):
        self.client.force_login(self.est_a)
        self.assertEqual(self.client.get(
            f'/panel/cita/{self.cita_sis.pk}/detalle/').status_code, 404)
        self.assertEqual(self.client.post(
            reverse('portal:estudiante_caso_nota', args=[self.cita_sis.pk]),
            {'texto': 'espionaje'}).status_code, 404)


class RegistroValidacionTests(TestCase):
    """B-5 P0-5: registro público con validación de contraseña y rol forzado."""

    def _post(self, **over):
        data = {'razon_social': 'Eval SA', 'nit': '111', 'first_name': 'Eval',
                'last_name': 'Uno', 'email': 'eval@qa.local',
                'password1': 'MuySegura2026!', 'password2': 'MuySegura2026!'}
        data.update(over)
        return self.client.post(reverse('accounts:register'), data)

    def test_password_debil_rechazada(self):
        r = self._post(password1='123', password2='123')
        self.assertEqual(r.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(email='eval@qa.local').exists())

    def test_password_comun_o_numerica_rechazada(self):
        for debil in ('password', '12345678'):
            r = self._post(password1=debil, password2=debil)
            self.assertFalse(CustomUser.objects.filter(email='eval@qa.local').exists(),
                             f'aceptó {debil}')

    def test_password_coincidence_exigida(self):
        self._post(password2='Distinta2026!x')
        self.assertFalse(CustomUser.objects.filter(email='eval@qa.local').exists())

    def test_registro_valido_crea_cliente_con_empresa(self):
        r = self._post()
        self.assertEqual(r.status_code, 302)
        user = CustomUser.objects.get(email='eval@qa.local')
        self.assertEqual(user.role, Role.CLIENTE)  # rol forzado, no aceptado del POST
        self.assertIsNotNone(user.empresa)
        self.assertTrue(user.check_password('MuySegura2026!'))
        # inicia sesión y llega a su portal
        c = self.client
        c.logout()
        r = c.post(reverse('accounts:login'),
                   {'username': 'eval@qa.local', 'password': 'MuySegura2026!',
                    'expected_role': 'cliente'})
        self.assertEqual(r.status_code, 302)

    def test_email_duplicado_rechazado(self):
        self._post()
        self.client.logout()  # el registro deja sesión iniciada
        r = self._post()
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Ya existe una cuenta')


class SeedDemoTests(TestCase):
    """B-4: el seed es explícito, idempotente y bloqueado en producción."""

    def test_landing_y_login_no_siembran(self):
        antes_u = CustomUser.objects.count()
        antes_f = FranjaHoraria.objects.count()
        self.client.get('/')
        self.client.get('/cuenta/login/')
        self.assertEqual(CustomUser.objects.count(), antes_u)
        self.assertEqual(FranjaHoraria.objects.count(), antes_f)

    def test_dashboard_cliente_no_crea_franjas(self):
        cliente = CustomUser.objects.create_user(
            email='cseed@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=Empresa.objects.create(razon_social='Seed SA'))
        self.client.force_login(cliente)
        antes = FranjaHoraria.objects.count()
        r = self.client.get('/panel/cliente/')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(FranjaHoraria.objects.count(), antes)

    def test_seed_idempotente_y_tutor_promovido(self):
        from accounts.demo_seed import seed_all

        res1 = seed_all()
        self.assertGreater(res1['franjas_nuevas'], 0)
        self.assertGreater(res1['citas_nuevas'], 0)
        usuarios = CustomUser.objects.count()
        franjas = FranjaHoraria.objects.count()
        citas = CitaAsesoria.objects.count()

        res2 = seed_all()
        self.assertEqual(res2['citas_nuevas'], 0)
        self.assertEqual(CustomUser.objects.count(), usuarios)
        self.assertEqual(FranjaHoraria.objects.count(), franjas)
        self.assertEqual(CitaAsesoria.objects.count(), citas)

        est = CustomUser.objects.get(email='estudiante@citi.ucc.edu.co')
        self.assertEqual(est.student_type, StudentType.TUTOR)  # promovida por perfil real
        self.assertTrue(est.perfil_estudiante.autorizado_como_tutor)
        director = CustomUser.objects.get(email='director@citi.ucc.edu.co')
        self.assertTrue(director.is_staff)

        # Franjas futuras reservables efectivamente disponibles
        f = FranjaHoraria.objects.filter(activa=True, inicio__gt=timezone.now()).first()
        self.assertIsNotNone(f)
        self.assertTrue(f.esta_disponible)

    def test_seed_reubica_citas_sobre_franjas_vencidas(self):
        """Simula correr el seed semanas después: las citas del plan vuelven a
        franjas futuras conservando su estado objetivo."""
        from accounts.demo_seed import seed_all

        seed_all()
        tz_off = timedelta(days=30)
        for cita in CitaAsesoria.objects.filter(
                cliente__email='cliente@empresatolima.co').exclude(
                subespecialidad=''):
            cita.franja.inicio -= tz_off
            cita.franja.fin -= tz_off
            cita.franja.save()
        res = seed_all()
        self.assertGreaterEqual(res['citas_reubicadas'], 5)
        for cita in CitaAsesoria.objects.filter(
                cliente__email='cliente@empresatolima.co').exclude(subespecialidad=''):
            self.assertGreater(cita.franja.inicio, timezone.now(),
                               f'cita {cita.pk} sigue sobre franja vencida')
        web = CitaAsesoria.objects.get(cliente__email='cliente@empresatolima.co',
                                       subespecialidad='web')
        self.assertEqual(web.estado, CitaAsesoria.Estado.SOLICITADA)

    def test_comando_bloqueado_en_produccion(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.settings(IS_PRODUCTION=True):
            with self.assertRaises(CommandError):
                call_command('seed_demo')


class RegresionesAuditTests(TestCase):
    """Regresiones directas de las pruebas T-xx de la auditoría."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='rg@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Reg SA'))
        cls.docente = make_user('rgd@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.est = CustomUser.objects.create_user(
            email='rge@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        cls.franja = make_franja(Area.SISTEMAS)
        cls.cita = CitaAsesoria.objects.create(
            franja=cls.franja, cliente=cls.cliente, subespecialidad='bd',
            asunto='Reg', estado=CitaAsesoria.Estado.ASIGNADA,
            docente_asignado=cls.docente)

    def _finalizar(self):
        self.cita.estado = CitaAsesoria.Estado.FINALIZADA
        self.cita.resumen_cierre = 'Listo'
        self.cita.full_clean()
        self.cita.save()

    def test_feedback_unica_y_rango(self):
        # T29/T30: una sola calificación y 1..5 validado
        self._finalizar()
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_feedback', args=[self.cita.pk]),
                             {'calificacion': 5, 'comentario_cliente': 'bien'})
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('portal:cliente_feedback', args=[self.cita.pk]),
                             {'calificacion': 1, 'comentario_cliente': 'x'})
        self.assertEqual(r.status_code, 404)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.calificacion, 5)
        self.cita.calificacion = None
        self.cita.save()
        r = self.client.post(reverse('portal:cliente_feedback', args=[self.cita.pk]),
                             {'calificacion': 99, 'comentario_cliente': ''})
        self.assertEqual(r.status_code, 200)
        self.cita.refresh_from_db()
        self.assertIsNone(self.cita.calificacion)

    def test_bitacora_happy_path_y_timeline(self):
        # T31: estudiante asignado escribe bitácora; timeline coherente
        self.est.perfil_estudiante.semestre = 9
        self.est.perfil_estudiante.creditos_aprobados = 140
        self.est.perfil_estudiante.promedio_general = Decimal('4.1')
        self.est.perfil_estudiante.save()
        self.est.refresh_from_db()
        self.cita.estudiante_apoyo = self.est
        self.cita.full_clean()
        self.cita.save()
        self.client.force_login(self.est)
        r = self.client.post(reverse('portal:estudiante_caso_nota', args=[self.cita.pk]),
                             {'texto': 'nota QA'})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.cita.notas.filter(texto='nota QA').count(), 1)
        pasos = [p['estado'] for p in self.cita.timeline if p['hecho']]
        self.assertIn(CitaAsesoria.Estado.ASIGNADA, pasos)

    def test_promocion_y_degradacion_tutor(self):
        # T21/T22: promoción/degradación por umbrales reales
        p = self.est.perfil_estudiante
        p.semestre, p.creditos_aprobados, p.promedio_general = 9, 150, Decimal('4.5')
        p.save()
        self.est.refresh_from_db()
        self.assertEqual(self.est.student_type, StudentType.TUTOR)
        p = self.est.perfil_estudiante
        p.creditos_aprobados = 10
        p.save()
        self.est.refresh_from_db()
        self.assertEqual(self.est.student_type, StudentType.CONSULTOR)

    def test_csrf_exigido_en_api_reservar(self):
        # T24: POST sin token CSRF -> 403
        c = self.client.__class__(enforce_csrf_checks=True)
        c.force_login(self.cliente)
        r = c.post('/agenda/api/reservar/', {'franja_id': self.franja.pk,
                                             'subespecialidad': 'bd'})
        self.assertEqual(r.status_code, 403)

    def test_acta_y_admin(self):
        # T28/T33
        self.client.force_login(self.docente)
        r = self.client.get(reverse('portal:docente_generar_acta', args=[self.cita.pk]))
        self.assertEqual(r.status_code, 404)  # aún no finalizada
        self._finalizar()
        r = self.client.get(reverse('portal:docente_generar_acta', args=[self.cita.pk]))
        self.assertEqual(r.status_code, 200)
        r = self.client.get('/admin/')
        self.assertIn('/admin/login/', r['Location'])  # no staff

    def test_constraint_doble_reserva_activa(self):
        # T08 a nivel de BD: constraint parcial única (franja, cliente activa)
        from django.db import IntegrityError, transaction
        self.cita.estado = CitaAsesoria.Estado.CANCELADA
        self.cita.save()
        CitaAsesoria.objects.create(franja=self.franja, cliente=self.cliente,
                                    subespecialidad='bd', estado='solicitada')
        with self.assertRaises(IntegrityError), transaction.atomic():
            CitaAsesoria.objects.create(franja=self.franja, cliente=self.cliente,
                                        subespecialidad='bd', estado='solicitada')


class EndToEndDemoTests(TestCase):
    """Validación E2E (sección 7): ciclo completo con los cinco roles."""

    @classmethod
    def setUpTestData(cls):
        cls.director = make_user('dire@qa.local', Role.DIRECTOR)
        cls.coord = make_user('coore@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.docente = make_user('doce@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.est = CustomUser.objects.create_user(
            email='este@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        p = cls.est.perfil_estudiante
        p.semestre, p.creditos_aprobados, p.promedio_general = 9, 140, Decimal('4.2')
        p.save()  # promueve a tutor legítimamente
        cls.est.refresh_from_db()
        assert cls.est.student_type == StudentType.TUTOR
        cls.cliente = CustomUser.objects.create_user(
            'cliende@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('EndToEnd SA'))
        cls.franja = make_franja(Area.SISTEMAS, capacidad=2)

    def test_ciclo_completo(self):
        from urllib.parse import urlencode
        # 1-2. cliente consulta franjas
        self.client.force_login(self.cliente)
        qs = urlencode({'start': self.franja.inicio.isoformat(),
                        'end': (self.franja.fin + timedelta(hours=1)).isoformat()})
        r = self.client.get(f'/agenda/api/eventos/?{qs}')
        self.assertEqual(r.status_code, 200)
        self.assertTrue(any(e['id'] == f'franja-{self.franja.pk}' for e in r.json()))

        # 3-4. reservar y verificar
        r = self.client.post('/agenda/api/reservar/', {
            'franja_id': self.franja.pk, 'asunto': 'E2E',
            'subespecialidad': 'web', 'tipo_servicio': 'especializada'})
        self.assertEqual(r.status_code, 200)
        cita_id = r.json()['cita_id']
        self.assertEqual(CitaAsesoria.objects.filter(pk=cita_id).count(), 1)
        r = self.client.get(f'/panel/cita/{cita_id}/detalle/')
        self.assertContains(r, 'E2E')
        self.assertContains(r, 'Solicitada')

        # 5-6. coordinador asigna docente y tutor (modal embed)
        self.client.force_login(self.coord)
        r = self.client.post(f'/panel/cita/{cita_id}/detalle/',
                             {'embed': '1', 'docente_id': self.docente.pk,
                              'estudiante_id': self.est.pk})
        self.assertEqual(r.status_code, 302)
        cita = CitaAsesoria.objects.get(pk=cita_id)
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)
        self.assertEqual(cita.docente_asignado, self.docente)
        self.assertEqual(cita.estudiante_apoyo, self.est)

        # 7-8. docente gestiona y finaliza
        self.client.force_login(self.docente)
        r = self.client.post(reverse('portal:docente_caso_detalle', args=[cita_id]),
                             {'accion': 'estado_rapido', 'nuevo_estado': 'en_proceso'})
        self.assertEqual(r.status_code, 302)
        r = self.client.post(reverse('portal:docente_caso_detalle', args=[cita_id]),
                             {'accion': 'gestionar', 'estado': 'finalizada',
                              'resumen_cierre': 'Cierre E2E: recomendaciones entregadas.',
                              'estudiante_apoyo': self.est.pk, 'nota_avance': ''})
        self.assertEqual(r.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.FINALIZADA)
        r = self.client.get(reverse('portal:docente_generar_acta', args=[cita_id]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Acta No.')

        # 9. feedback del cliente
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_feedback', args=[cita_id]),
                             {'calificacion': 5, 'comentario_cliente': 'Excelente E2E'})
        self.assertEqual(r.status_code, 302)
        cita.refresh_from_db()
        self.assertEqual(cita.calificacion, 5)

        # 10-11. director: indicadores reflejan el ciclo
        self.client.force_login(self.director)
        r = self.client.get(reverse('portal:director_dashboard'))
        self.assertContains(r, 'Franjas activas')
        # 34 T-checks equivalentes: el dashboard no revienta y muestra contadores
        body = r.content.decode()
        self.assertIn('stat-card', body)

        # estudiante involucrado conserva acceso al caso (detalle/bitácora)
        self.client.force_login(self.est)
        r = self.client.get(f'/panel/cita/{cita_id}/detalle/')
        self.assertContains(r, 'E2E')
        self.assertContains(r, 'Finalizada')


class TrazabilidadEventosTests(TestCase):
    """Fase 03 Módulo C: cada acción real deja un evento; el fallo no deja
    evento de éxito; el historial no es editable desde el portal."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='tx1@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('TX SA'))
        cls.coord = make_user('txc@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.docente = make_user('txd@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.tutor = CustomUser.objects.create_user(
            email='txe@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        p = cls.tutor.perfil_estudiante
        p.semestre, p.creditos_aprobados, p.promedio_general = 9, 140, Decimal('4.1')
        p.save()
        cls.tutor.refresh_from_db()
        cls.franja = make_franja(Area.SISTEMAS)

    def _reservar(self):
        self.client.force_login(self.cliente)
        r = self.client.post('/agenda/api/reservar/', {
            'franja_id': self.franja.pk, 'asunto': 'TX',
            'subespecialidad': 'bd', 'tipo_servicio': 'especializada'})
        return r.json()['cita_id']

    def test_reserva_registra_evento_creada(self):
        cita_id = self._reservar()
        cita = CitaAsesoria.objects.get(pk=cita_id)
        tipos = list(cita.eventos.values_list('tipo', flat=True))
        self.assertIn('creada', tipos)
        ev = cita.eventos.first()
        self.assertEqual(ev.actor_label, self.cliente.email)
        self.assertEqual(ev.usuario, self.cliente)

    def test_reserva_fallida_no_deja_evento(self):
        # franja sin cupo: la transacción completa revierte (cita y evento)
        FranjaHoraria.objects.filter(pk=self.franja.pk).update(capacidad=0)
        self.client.force_login(self.cliente)
        r = self.client.post('/agenda/api/reservar/', {
            'franja_id': self.franja.pk, 'subespecialidad': 'bd'})
        self.assertEqual(r.status_code, 409)
        self.assertEqual(CitaAsesoria.objects.count(), 0)
        self.assertEqual(CitaEvento.objects.count(), 0)

    def test_asignacion_registra_secuencia_de_eventos(self):
        cita_id = self._reservar()
        cita = CitaAsesoria.objects.get(pk=cita_id)
        self.client.force_login(self.coord)
        self.client.get(reverse('portal:coordinador_asignar', args=[cita_id]))
        self.client.post(reverse('portal:coordinador_asignar', args=[cita_id]),
                         {'docente_id': self.docente.pk, 'estudiante_id': self.tutor.pk})
        tipos = list(cita.eventos.values_list('tipo', flat=True))
        self.assertIn('revisada', tipos)
        self.assertIn('docente_asignado', tipos)
        self.assertIn('tutor_asignado', tipos)
        self.assertIn('asignada', tipos)
        asig = cita.eventos.filter(tipo='asignada').first()
        self.assertEqual(asig.estado_anterior, 'solicitada')
        self.assertEqual(asig.estado_nuevo, 'asignada')
        # marca temporal de asignación
        cita.refresh_from_db()
        self.assertIsNotNone(cita.asignada_en)

    def test_reutilizar_revisada_no_duplica(self):
        cita_id = self._reservar()
        self.client.force_login(self.coord)
        self.client.get(reverse('portal:coordinador_asignar', args=[cita_id]))
        self.client.get(reverse('portal:coordinador_asignar', args=[cita_id]))
        cita = CitaAsesoria.objects.get(pk=cita_id)
        self.assertEqual(cita.eventos.filter(tipo='revisada').count(), 1)

    def test_transiciones_docente_y_cierre_con_marcas(self):
        cita_id = self._reservar()
        cita = CitaAsesoria.objects.get(pk=cita_id)
        cita.docente_asignado = self.docente
        cita.estado = CitaAsesoria.Estado.ASIGNADA
        cita.full_clean()
        cita.save()
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita_id]),
                         {'accion': 'estado_rapido', 'nuevo_estado': 'en_proceso'})
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita_id]),
                         {'accion': 'estado_rapido', 'nuevo_estado': 'finalizada'})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.FINALIZADA)
        self.assertIsNotNone(cita.cerrada_en)
        tipos = list(cita.eventos.values_list('tipo', flat=True))
        self.assertIn('iniciada', tipos)
        self.assertIn('finalizada', tipos)

    def test_gestion_form_no_borra_evento_de_transicion(self):
        """Regresión: el estado anterior debe capturarse ANTES de is_valid()
        (ModelForm muta la instancia ligada)."""
        cita_id = self._reservar()
        cita = CitaAsesoria.objects.get(pk=cita_id)
        cita.docente_asignado = self.docente
        cita.estado = CitaAsesoria.Estado.ASIGNADA
        cita.full_clean()
        cita.save()
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita_id]),
                         {'accion': 'gestionar', 'estado': 'finalizada',
                          'resumen_cierre': 'Resumen desde gestión.', 'estudiante_apoyo': ''})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.FINALIZADA)
        self.assertIsNotNone(cita.cerrada_en)
        self.assertEqual(cita.eventos.filter(
            tipo='estado_cambiado', estado_anterior='asignada',
            estado_nuevo='finalizada').count(), 1)

    def test_reguardar_finalizada_no_inventa_eventos(self):
        """Guardar de nuevo una cita ya finalizada NO genera eventos falsos."""
        cita_id = self._reservar()
        cita = CitaAsesoria.objects.get(pk=cita_id)
        cita.docente_asignado = self.docente
        cita.estado = CitaAsesoria.Estado.FINALIZADA
        cita.resumen_cierre = 'X'
        cita.full_clean()
        cita.save()
        self.client.force_login(self.docente)
        n0 = cita.eventos.count()
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita_id]),
                         {'accion': 'gestionar', 'estado': 'finalizada',
                          'resumen_cierre': 'Y', 'estudiante_apoyo': ''})
        cita.refresh_from_db()
        self.assertIsNotNone(cita.cerrada_en)  # se completa la marca ausente
        self.assertEqual(cita.eventos.count(), n0)  # sin eventos nuevos

    def test_acta_y_feedback_registran_evento(self):
        cita_id = self._reservar()
        cita = CitaAsesoria.objects.get(pk=cita_id)
        cita.docente_asignado = self.docente
        cita.estado = CitaAsesoria.Estado.FINALIZADA
        cita.resumen_cierre = 'Cierre TX'
        cita.full_clean()
        cita.save()
        self.client.force_login(self.docente)
        self.client.get(reverse('portal:docente_generar_acta', args=[cita_id]))
        self.client.get(reverse('portal:docente_generar_acta', args=[cita_id]))
        cita.refresh_from_db()
        self.assertEqual(cita.eventos.filter(tipo='acta_registrada').count(), 1)
        self.client.force_login(self.cliente)
        self.client.post(reverse('portal:cliente_feedback', args=[cita_id]),
                         {'calificacion': 4, 'comentario_cliente': 'bien'})
        self.assertEqual(cita.eventos.filter(tipo='feedback').count(), 1)

    def test_eventos_no_editables_desde_portal(self):
        # No hay URLs ni vistas que modifiquen CitaEvento
        from django.urls import reverse as rev
        self.client.force_login(self.coord)
        cita_id = self._reservar()
        r = self.client.get('/admin/scheduling/citaevento/add/')
        self.assertEqual(r.status_code, 302)  # staff requerido

    def test_timeline_sin_eventos_muestra_advertencia_honest(self):
        # cita creada directamente (sin historial): debe decir que no estaba habilitado
        cita = CitaAsesoria.objects.create(franja=self.franja, cliente=self.cliente,
                                           subespecialidad='web', asunto='Sin TX')
        self.client.force_login(self.cliente)
        r = self.client.get(f'/panel/cita/{cita.pk}/detalle/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'no estaba habilitado')

    def test_cita_con_eventos_muestra_linea_de_tiempo(self):
        cita_id = self._reservar()
        self.client.force_login(self.cliente)
        r = self.client.get(f'/panel/cita/{cita_id}/detalle/')
        self.assertContains(r, 'Historial de la solicitud')
        self.assertContains(r, 'Solicitud creada')


class IndicadoresTests(TestCase):
    """Fase 03 Módulos B/C: fórmulas, filtros, permisos y CSV."""

    @classmethod
    def setUpTestData(cls):
        from portal import indicadores
        cls.director = make_user('id-director@qa.local', Role.DIRECTOR,
                                 first_name='Diana', last_name='Rojas')
        cls.coord_sis = make_user('id-coord@qa.local', Role.COORDINADOR, Area.SISTEMAS,
                                  first_name='Carlos', last_name='Vela')
        cls.coord_civ = make_user('id-coordc@qa.local', Role.COORDINADOR, Area.CIVIL,
                                  first_name='Lucía', last_name='Marín')
        cls.cliente = CustomUser.objects.create_user(
            email='id-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('ID SA'))
        cls.docente = make_user('id-doc@qa.local', Role.DOCENTE, Area.SISTEMAS,
                                first_name='Ernesto', last_name='Paiba')

        f1 = make_franja(Area.SISTEMAS, horas_al_futuro=48)
        f1b = make_franja(Area.SISTEMAS, horas_al_futuro=120)
        f1c = make_franja(Area.SISTEMAS, horas_al_futuro=240)
        f2 = make_franja(Area.CIVIL, horas_al_futuro=72)
        # 2 solicitadas sistemas, 1 finalizada sistemas, 1 en proceso civil
        c1 = CitaAsesoria.objects.create(franja=f1, cliente=cls.cliente,
                                         subespecialidad='web', asunto='A1')
        c2 = CitaAsesoria.objects.create(franja=f1b, cliente=cls.cliente,
                                         subespecialidad='bd', asunto='A2')
        c3 = CitaAsesoria.objects.create(franja=f1c, cliente=cls.cliente,
                                         subespecialidad='ciber', asunto='A3',
                                         estado=CitaAsesoria.Estado.FINALIZADA,
                                         docente_asignado=cls.docente,
                                         resumen_cierre='ok')
        c3.creada_en = timezone.now() - timedelta(days=10)
        c3.asignada_en = timezone.now() - timedelta(days=9)
        c3.cerrada_en = timezone.now() - timedelta(days=4)
        c3.save()
        c4 = CitaAsesoria.objects.create(franja=f2, cliente=cls.cliente,
                                         subespecialidad='vias', asunto='A4',
                                         estado=CitaAsesoria.Estado.EN_PROCESO)

    def test_kpis_y_tasa(self):
        qs, _ = indicadores.parse_filtros({})
        k = indicadores.kpis_base(qs)
        self.assertEqual(k['recibidas'], 4)
        self.assertEqual(k['pendientes'], 2)
        self.assertEqual(k['finalizadas'], 1)
        self.assertEqual(k['tasa_finalizacion'], 25.0)

    def test_tiempos_promedio(self):
        qs, _ = indicadores.parse_filtros({})
        t = indicadores.tiempos_promedio(qs)
        self.assertIsNotNone(t['resolucion_horas'])
        # c3: creada -10d -> cerrada -4d = 6 días = 144 h
        self.assertEqual(t['resolucion_horas'], 144.0)
        self.assertEqual(t['asignacion_horas'], 24.0)

    def test_filtros_area_estado_periodo(self):
        qs, _ = indicadores.parse_filtros({'area': 'civil'})
        self.assertEqual(qs.count(), 1)
        qs, _ = indicadores.parse_filtros({'estado': 'finalizada'})
        self.assertEqual(qs.count(), 1)
        qs, _ = indicadores.parse_filtros({'periodo': '7'})
        self.assertEqual(qs.count(), 3)  # la cerrada hace 10 días queda fuera

    def test_director_accede_y_coordinador_aislado(self):
        self.client.force_login(self.director)
        r = self.client.get('/panel/trazabilidad/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Trazabilidad e indicadores')
        self.assertContains(r, 'CITI-')

        self.client.force_login(self.coord_civ)
        r = self.client.get('/panel/trazabilidad/')
        self.assertEqual(r.status_code, 200)
        # el coordinador civil solo ve datos de su área
        qs, filtros = indicadores.parse_filtros({}, area_forzada=Area.CIVIL)
        self.assertTrue(all(c.franja.area == Area.CIVIL for c in qs))

    def test_roles_sin_acceso_a_trazabilidad(self):
        self.client.force_login(self.cliente)
        r = self.client.get('/panel/trazabilidad/')
        self.assertEqual(r.status_code, 302)
        r = self.client.get('/panel/trazabilidad/exportar.csv')
        self.assertEqual(r.status_code, 302)

    def test_dashboard_director_renderea_indicadores(self):
        self.client.force_login(self.director)
        r = self.client.get('/panel/director/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Solicitudes recibidas')
        self.assertContains(r, 'Bienvenido')

    def test_csv_export_respeta_filtros(self):
        self.client.force_login(self.director)
        r = self.client.get('/panel/trazabilidad/exportar.csv?area=civil')
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')
        contenido = r.content.decode('utf-8-sig')
        self.assertIn('Vías', contenido)
        self.assertNotIn('Bases de Datos', contenido)  # fuera del filtro de área
        self.assertIn('Reporte CITI', contenido)

    def test_csv_no_incluye_correos_de_contacto(self):
        self.client.force_login(self.director)
        contenido = self.client.get('/panel/trazabilidad/exportar.csv').content.decode('utf-8-sig')
        self.assertNotIn('qa.local', contenido)


# ===========================================================================
# FASE 04 — seguimiento, interacciones, aprobaciones, modalidades, seguridad
# ===========================================================================

class SeguimientoClienteTests(TestCase):
    """4.1/4.2: «Mis solicitudes» y página de seguimiento individual."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('F4 SA'))
        cls.otros = CustomUser.objects.create_user(
            email='f4-cli2@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('F4 Otras'))
        cls.docente = make_user('f4-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.coordinador = make_user('f4-coord@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        f1 = make_franja(Area.SISTEMAS, horas_al_futuro=48)
        f2 = make_franja(Area.SISTEMAS, horas_al_futuro=120)
        cls.cita_act = CitaAsesoria.objects.create(
            franja=f1, cliente=cls.cliente, subespecialidad='web',
            asunto='Seguimiento activo', estado=CitaAsesoria.Estado.EN_PROCESO,
            docente_asignado=cls.docente)
        cls.cita_ajena = CitaAsesoria.objects.create(
            franja=f2, cliente=cls.otros, subespecialidad='bd', asunto='Ajena')

    def test_lista_mis_solicitudes_filtra_estado_y_tipo(self):
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('portal:cliente_mis_solicitudes'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, f'CITI-{self.cita_act.pk:05d}')
        self.assertNotContains(r, 'Ajena')
        r = self.client.get(reverse('portal:cliente_mis_solicitudes') + '?estado=en_proceso')
        self.assertContains(r, 'Seguimiento activo')
        r = self.client.get(reverse('portal:cliente_mis_solicitudes') + '?estado=finalizada')
        self.assertContains(r, 'Sin resultados para el filtro')

    def test_cliente_no_accede_seguimiento_ajeno(self):
        self.client.force_login(self.otros)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[self.cita_act.pk]))
        self.assertEqual(r.status_code, 404)

    def test_seguimiento_muestra_estado_responsables_y_historial_real(self):
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[self.cita_act.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'En proceso')
        self.assertContains(r, self.docente.nombre_completo)
        self.assertContains(r, self.coordinador.email)  # coordinatora del área (sin coords sería "No disponible")
        self.assertContains(r, 'Historial de la solicitud')

    def test_cita_cancelada_sin_progresion_ficticia(self):
        self.cita_act.estado = CitaAsesoria.Estado.CANCELADA
        self.cita_act.save()
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[self.cita_act.pk]))
        self.assertContains(r, 'cancelada')

    def test_solicitud_antigua_no_inventa_historial(self):
        # cita creada sin eventos (pre trazabilidad): aviso honesto
        f3 = make_franja(Area.SISTEMAS, horas_al_futuro=240)
        cita = CitaAsesoria.objects.create(franja=f3, cliente=self.cliente,
                                           subespecialidad='redes', asunto='Vieja')
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[cita.pk]))
        self.assertContains(r, 'no estaba habilitado')

    def test_estados_vacios_utiles(self):
        nuevo = CustomUser.objects.create_user(
            email='f4-vacio@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Sin Citas SAS'))
        self.client.force_login(nuevo)
        r = self.client.get(reverse('portal:cliente_mis_solicitudes'))
        self.assertContains(r, 'Todavía no tiene solicitudes')


class InteraccionComentariosTests(TestCase):
    """5.1/5.2: intercambio cliente ↔ profesional con tipos y visibilidad."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4i-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Inter SA'))
        cls.otro_cli = CustomUser.objects.create_user(
            email='f4i-otro@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Otra SA'))
        cls.docente = make_user('f4i-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.tutor = CustomUser.objects.create_user(
            email='f4i-est@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        p = cls.tutor.perfil_estudiante
        p.semestre, p.creditos_aprobados, p.promedio_general = 9, 140, Decimal('4.1')
        p.save()
        cls.tutor.refresh_from_db()
        cls.coord_sis = make_user('f4i-csis@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.coord_civ = make_user('f4i-cciv@qa.local', Role.COORDINADOR, Area.CIVIL)
        cls.franja = make_franja(Area.SISTEMAS)
        cls.cita = CitaAsesoria.objects.create(
            franja=cls.franja, cliente=cls.cliente, subespecialidad='web',
            asunto='Caso interacción', estado=CitaAsesoria.Estado.EN_PROCESO,
            docente_asignado=cls.docente, estudiante_apoyo=cls.tutor)

    def _post_interaccion(self, user, accion_url, prefix, tipo, texto):
        self.client.force_login(user)
        return self.client.post(accion_url, {
            f'{prefix}-tipo': tipo, f'{prefix}-texto': texto, 'accion': 'interaccion'})

    def test_cliente_comenta_y_genera_evento(self):
        r = self._post_interaccion(
            self.cliente,
            reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
            'ic', 'general', 'Consulta del cliente F4')
        self.assertEqual(r.status_code, 302)
        inter = self.cita.interacciones.get(texto='Consulta del cliente F4')
        self.assertEqual(inter.rol_autor, Role.CLIENTE)
        self.assertTrue(inter.para_cliente)
        self.assertTrue(self.cita.eventos.filter(
            tipo='interaccion', metadata__interaccion_id=inter.pk).exists())

    def test_equipo_responde_desde_vista_docente(self):
        r = self._post_interaccion(
            self.docente,
            reverse('portal:docente_caso_detalle', args=[self.cita.pk]),
            'ia', 'observacion', 'Observación del docente')
        self.assertEqual(r.status_code, 302)
        self.assertTrue(self.cita.interacciones.filter(
            texto='Observación del docente', rol_autor=Role.DOCENTE).exists())

    def test_nota_interna_no_es_visible_al_cliente(self):
        self._post_interaccion(
            self.docente,
            reverse('portal:docente_caso_detalle', args=[self.cita.pk]),
            'ia', 'nota_interna', 'Pista técnica interna')
        inter = self.cita.interacciones.get(texto='Pista técnica interna')
        self.assertFalse(inter.para_cliente)
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[self.cita.pk]))
        self.assertNotContains(r, 'Pista técnica interna')
        self.client.force_login(self.coord_sis)
        r = self.client.get(reverse('portal:cita_detalle', args=[self.cita.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Pista técnica interna')  # sí visible para el equipo

    def test_cliente_no_puede_escribir_tipos_de_equipo(self):
        self.client.force_login(self.cliente)
        r = self.client.post(
            reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
            {'accion': 'interaccion', 'ic-tipo': 'observacion', 'ic-texto': 'spoof'})
        self.assertEqual(r.status_code, 302)  # form invalido -> sin crear
        self.assertEqual(self.cita.interacciones.filter(texto='spoof').count(), 0)

    def test_ajeno_sin_acceso_a_interacciones(self):
        self.client.force_login(self.otro_cli)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[self.cita.pk]))
        self.assertEqual(r.status_code, 404)

    def test_coordinador_de_otra_area_no_ve_caso(self):
        self.client.force_login(self.coord_civ)
        r = self.client.get(reverse('portal:staff_seguimiento'))
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'Caso interacción')

    def test_transaccion_fallida_no_deja_evento(self):
        from django.core.exceptions import ValidationError
        from scheduling.trazabilidad import registrar_interaccion
        n_eventos = self.cita.eventos.count()
        with self.assertRaises(ValidationError):
            with transaction.atomic():
                # rol autor no coincide con el tipo (cliente escribiendo entrega)
                registrar_interaccion(self.cita, self.cliente, 'entrega_resultados', 'x')
        self.assertEqual(self.cita.eventos.count(), n_eventos)
        self.assertEqual(self.cita.interacciones.count(), 0)

    def test_interaccion_no_cambia_estado(self):
        antes = self.cita.estado
        self._post_interaccion(
            self.cliente,
            reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
            'ic', 'respuesta', 'Solo un comentario, no un estado')
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, antes)


class AprobacionesEntregablesTests(TestCase):
    """5.3: flujo publicación → aprobación/ajustes sin tocar el cierre."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4a-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Apr SA'))
        cls.docente = make_user('f4a-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.franja = make_franja(Area.SISTEMAS)
        cls.cita = CitaAsesoria.objects.create(
            franja=cls.franja, cliente=cls.cliente, subespecialidad='web',
            asunto='Caso aprobación', tipo_servicio='especializada',
            estado=CitaAsesoria.Estado.EN_PROCESO, docente_asignado=cls.docente)

    def _publicar(self, titulo='Entrega 1', ficha=None):
        self.client.force_login(self.docente)
        data = {'accion': 'entrega', 'ed-titulo': titulo, 'ed-contenido': 'Resultados'}
        if ficha:
            data.update({'ed-diagnostico': 'Diagnóstico D', 'ed-alcance': 'Alcance A',
                         'ed-metodologia': 'Metodología M', 'ed-entregables': 'Informe'})
        r = self.client.post(reverse('portal:docente_caso_detalle', args=[self.cita.pk]), data)
        self.assertEqual(r.status_code, 302)

    def test_publicar_entrega_visible_al_cliente(self):
        self._publicar('Informe preliminar', ficha=True)
        ent = self.cita.interacciones.get(tipo='entrega_resultados')
        self.assertTrue(ent.para_cliente)
        self.assertEqual(ent.datos_extra['diagnostico'], 'Diagnóstico D')
        self.assertTrue(self.cita.eventos.filter(tipo='entrega_publicada').exists())
        self.assertTrue(self.cita.entrega_pendiente)
        self.client.force_login(self.cliente)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[self.cita.pk]))
        self.assertContains(r, 'Informe preliminar')
        self.assertContains(r, 'Aprobar entregable')

    def test_aprobar_no_finaliza_la_solicitud(self):
        self._publicar()
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                             {'accion': 'aprobar', 'dc-observacion': 'Todo bien'})
        self.assertEqual(r.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, CitaAsesoria.Estado.EN_PROCESO)
        self.assertIsNone(self.cita.cerrada_en)
        self.assertFalse(self.cita.entrega_pendiente)
        self.assertTrue(self.cita.eventos.filter(tipo='decision_cliente').exists())

    def test_no_se_puede_aprobar_sin_entrega(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                             {'accion': 'aprobar', 'dc-observacion': 'x'})
        self.assertEqual(r.status_code, 200)  # re-render con error: no hay entrega
        self.assertContains(r, 'No hay un entregable pendiente')
        self.assertEqual(self.cita.interacciones.filter(tipo='aprobacion').count(), 0)

    def test_decision_sin_observacion_no_se_registra(self):
        self._publicar()
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                             {'accion': 'aprobar'})
        self.assertEqual(r.status_code, 200)  # re-render con error
        self.assertEqual(self.cita.interacciones.filter(tipo='aprobacion').count(), 0)

    def test_ajustes_reabre_finalizada_y_vuelve_a_proceso(self):
        # cierre docente legitimo
        self.cita.estado = CitaAsesoria.Estado.FINALIZADA
        self.cita.resumen_cierre = 'Cierre F4'
        self.cita.full_clean()
        self.cita.save()
        self._publicar()
        # tras publicar con estado finalizada (el docente puede publicar antes
        # de cerrar; aquí la entrega existe sobre la cita cerrada para probar
        # la reapertura autorizada por el cliente)
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                             {'accion': 'ajustes', 'dc-observacion': 'Falta X'})
        self.assertEqual(r.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, CitaAsesoria.Estado.EN_PROCESO)
        self.assertTrue(self.cita.eventos.filter(tipo='cancelada').count() == 0)
        self.assertEqual(self.cita.ajustes_solicitados_total, 1)

    def test_doble_decision_bloqueada(self):
        self._publicar()
        self.client.force_login(self.cliente)
        r1 = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                              {'accion': 'aprobar', 'dc-observacion': 'ok'})
        self.assertEqual(r1.status_code, 302)
        r2 = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                              {'accion': 'aprobar', 'dc-observacion': 'otra vez'})
        self.assertEqual(r2.status_code, 200)  # sin entrega pendiente: re-render
        self.assertEqual(self.cita.interacciones.filter(tipo='aprobacion').count(), 1)

    def test_docente_no_asignado_no_publica(self):
        otro = make_user('f4a-doc2@qa.local', Role.DOCENTE, Area.SISTEMAS)
        self.client.force_login(otro)
        r = self.client.post(reverse('portal:docente_caso_detalle', args=[self.cita.pk]),
                             {'accion': 'entrega', 'ed-titulo': 'No', 'ed-contenido': 'x'})
        self.assertEqual(r.status_code, 404)


class ModalidadesServicioTests(TestCase):
    """6: diferenciación funcional asesoría (orientación) vs consultoría."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4m-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Mod SA'))
        cls.docente = make_user('f4m-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.coordinador = make_user('f4m-coord@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.tutor = CustomUser.objects.create_user(
            email='f4m-est@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)
        p = cls.tutor.perfil_estudiante
        p.semestre, p.creditos_aprobados, p.promedio_general = 9, 140, Decimal('4.1')
        p.save()
        cls.tutor.refresh_from_db()
        cls.franja = make_franja(Area.SISTEMAS)

    def _reservar(self, tipo, extra=None):
        self.client.force_login(self.cliente)
        data = {'franja_id': self.franja.pk, 'asunto': f'Modalidad {tipo}',
                'subespecialidad': 'web', 'tipo_servicio': tipo}
        if extra:
            data.update(extra)
        return self.client.post('/agenda/api/reservar/', data)

    def test_consultoria_puede_asignarse_solo_docente(self):
        r = self._reservar('especializada')
        cita = CitaAsesoria.objects.get(pk=r.json()['cita_id'])
        self.client.force_login(self.coordinador)
        self.client.post(reverse('portal:coordinador_asignar', args=[cita.pk]),
                         {'docente_id': self.docente.pk, 'estudiante_id': ''})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)

    def test_consultoria_sin_docente_rechazada_I6(self):
        r = self._reservar('especializada')
        cita = CitaAsesoria.objects.get(pk=r.json()['cita_id'])
        self.client.force_login(self.coordinador)
        resp = self.client.post(reverse('portal:coordinador_asignar', args=[cita.pk]),
                                {'docente_id': '', 'estudiante_id': self.tutor.pk})
        self.assertEqual(resp.status_code, 200)  # re-render con error
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.SOLICITADA)

    def test_asesoria_puede_asignarse_sin_docente(self):
        r = self._reservar('orientacion')
        cita = CitaAsesoria.objects.get(pk=r.json()['cita_id'])
        self.client.force_login(self.coordinador)
        self.client.post(reverse('portal:coordinador_asignar', args=[cita.pk]),
                         {'docente_id': '', 'estudiante_id': self.tutor.pk})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.ASIGNADA)

    def test_ficha_consultoria_en_reserva(self):
        r = self._reservar('especializada', {
            'ctx_objetivos': 'Migrar la base a la nube',
            'ctx_entregables': 'Plan de migración'})
        cita = CitaAsesoria.objects.get(pk=r.json()['cita_id'])
        inter = cita.interacciones.get()
        self.assertEqual(inter.datos_extra['alcance'], 'Migrar la base a la nube')
        self.assertEqual(inter.datos_extra['origen'], 'solicitud_cliente')

    def test_ficha_rechazada_en_asesoria(self):
        r = self._reservar('orientacion', {'ctx_objetivos': 'no deberia'})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(CitaAsesoria.objects.count(), 0)

    def test_modelo_rechaza_consultoria_asignada_sin_docente(self):
        from django.core.exceptions import ValidationError
        r = self._reservar('especializada')
        cita = CitaAsesoria.objects.get(pk=r.json()['cita_id'])
        cita.estado = CitaAsesoria.Estado.ASIGNADA
        with self.assertRaises(ValidationError):
            cita.full_clean()


class TransicionesFormalTests(TestCase):
    """I-2: tabla formal de transiciones aplicada en el portal."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4t-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Trans SA'))
        cls.docente = make_user('f4t-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.franja = make_franja(Area.SISTEMAS)

    def _cita(self, estado, **kw):
        return CitaAsesoria.objects.create(
            franja=self.franja, cliente=self.cliente, subespecialidad='web',
            asunto='Transición', estado=estado,
            docente_asignado=self.docente if estado != 'solicitada' else None,
            **kw)

    def test_rechazo_retroceso_en_proceso_a_asignada(self):
        cita = self._cita(CitaAsesoria.Estado.EN_PROCESO)
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'gestionar', 'estado': 'asignada',
                          'resumen_cierre': '', 'estudiante_apoyo': ''})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.EN_PROCESO)
        self.assertEqual(cita.eventos.filter(tipo='estado_cambiado').count(), 0)

    def test_estado_rapido_tambien_respeta_la_tabla(self):
        cita = self._cita(CitaAsesoria.Estado.EN_PROCESO)
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'estado_rapido', 'nuevo_estado': 'asignada'})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.EN_PROCESO)

    def test_avance_asignada_a_finalizada_si_permitido(self):
        cita = self._cita(CitaAsesoria.Estado.ASIGNADA)
        self.client.force_login(self.docente)
        self.client.post(reverse('portal:docente_caso_detalle', args=[cita.pk]),
                         {'accion': 'gestionar', 'estado': 'finalizada',
                          'resumen_cierre': 'OK F4', 'estudiante_apoyo': ''})
        cita.refresh_from_db()
        self.assertEqual(cita.estado, CitaAsesoria.Estado.FINALIZADA)
        self.assertIsNotNone(cita.cerrada_en)

    def test_finalizada_a_cancelada_no_permitida(self):
        cita = self._cita(CitaAsesoria.Estado.FINALIZADA, resumen_cierre='x')
        from django.core.exceptions import ValidationError
        from scheduling.trazabilidad import cambio_estado
        with self.assertRaises(ValidationError):
            cambio_estado(cita, self.docente, 'cancelada')


class CancelacionI4AdjuntoI3Tests(TestCase):
    """I-4 cancelación desde portal con confirmación; I-3 descarga autorizada."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4c-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Cancel SA'))
        cls.otro_cli = CustomUser.objects.create_user(
            email='f4c-otro@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Otra SA'))
        cls.docente = make_user('f4c-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        f = make_franja(Area.SISTEMAS, horas_al_futuro=48)
        f2 = make_franja(Area.SISTEMAS, horas_al_futuro=120)
        cls.cita = CitaAsesoria.objects.create(
            franja=f, cliente=cls.cliente, subespecialidad='web', asunto='Cancelable')
        cls.cita_proceso = CitaAsesoria.objects.create(
            franja=f2, cliente=cls.cliente, subespecialidad='bd',
            asunto='En proceso', estado=CitaAsesoria.Estado.EN_PROCESO,
            docente_asignado=cls.docente)
        from django.core.files.base import ContentFile
        cls.cita.archivo_adjunto.save('tdr.txt', ContentFile('doc F4'), save=True)

    def test_cancelacion_requiere_confirmacion(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                             {'accion': 'cancelar'})
        self.assertEqual(r.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, CitaAsesoria.Estado.SOLICITADA)

    def test_cancelacion_valida_deja_evento(self):
        self.client.force_login(self.cliente)
        r = self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita.pk]),
                             {'accion': 'cancelar', 'confirmar': 'si'})
        self.assertEqual(r.status_code, 302)
        self.cita.refresh_from_db()
        self.assertEqual(self.cita.estado, CitaAsesoria.Estado.CANCELADA)
        self.assertTrue(self.cita.eventos.filter(
            tipo='cancelada', actor_label=self.cliente.email).exists())

    def test_no_cancela_caso_en_proceso(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('portal:cliente_seguimiento', args=[self.cita_proceso.pk]),
                         {'accion': 'cancelar', 'confirmar': 'si'})
        self.cita_proceso.refresh_from_db()
        self.assertEqual(self.cita_proceso.estado, CitaAsesoria.Estado.EN_PROCESO)

    def test_adjunto_solo_para_partes(self):
        url = reverse('portal:cita_adjunto', args=[self.cita.pk])
        self.client.force_login(self.otro_cli)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.cliente)
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        self.assertIn('attachment', r['Content-Disposition'])

    def test_adjunto_docente_no_asignado_sin_acceso(self):
        # cita_proceso no tiene adjunto: el acceso es denegado por autoría
        # (403) antes de evaluar el archivo
        self.client.force_login(make_user('f4c-x@qa.local', Role.DOCENTE, Area.SISTEMAS))
        self.assertEqual(self.client.get(
            reverse('portal:cita_adjunto', args=[self.cita.pk])).status_code, 403)


class ReportesInteraccionTests(TestCase):
    """8: métricas de aprobación, columna CSV y muestra honesta."""

    @classmethod
    def setUpTestData(cls):
        cls.director = make_user('f4r-dir@qa.local', Role.DIRECTOR)
        cls.cliente = CustomUser.objects.create_user(
            email='f4r-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Repo SA'))
        cls.docente = make_user('f4r-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        f = make_franja(Area.SISTEMAS, horas_al_futuro=48)
        cls.c1 = CitaAsesoria.objects.create(
            franja=f, cliente=cls.cliente, subespecialidad='web',
            estado=CitaAsesoria.Estado.EN_PROCESO, docente_asignado=cls.docente,
            asunto='R1')
        f2 = make_franja(Area.SISTEMAS, horas_al_futuro=120)
        cls.c2 = CitaAsesoria.objects.create(
            franja=f2, cliente=cls.cliente, subespecialidad='bd',
            estado=CitaAsesoria.Estado.EN_PROCESO, docente_asignado=cls.docente,
            asunto='R2')
        from scheduling.trazabilidad import (
            publicar_entrega, registrar_decision_cliente)
        with transaction.atomic():
            publicar_entrega(cls.c1, cls.docente, 'Ente 1', 'cont')
        with transaction.atomic():
            publicar_entrega(cls.c2, cls.docente, 'Ente 2', 'cont')
        with transaction.atomic():
            registrar_decision_cliente(cls.c2, cls.cliente, True, 'ok')

    def test_metricas_aprobacion(self):
        qs, _ = indicadores.parse_filtros({})
        m = indicadores.metricas_interaccion(qs)
        self.assertEqual(m['entregas_publicadas'], 2)
        self.assertEqual(m['pendientes_aprobacion'], 1)
        self.assertEqual(m['aprobaciones'], 1)
        self.assertIsNone(m['valoracion_media'])

    def test_csv_incluye_columna_aprobacion_coherente(self):
        self.client.force_login(self.director)
        r = self.client.get('/panel/trazabilidad/exportar.csv')
        contenido = r.content.decode('utf-8-sig')
        self.assertIn('Aprobación de entregables', contenido)
        lineas = [l for l in contenido.splitlines() if l.startswith('CITI-')]
        estados = {l.split(',')[0]: l for l in lineas}
        fila_pend = [l for l in lineas if str(self.c1.pk).zfill(5) in l][0]
        fila_apr = [l for l in lineas if str(self.c2.pk).zfill(5) in l][0]
        self.assertIn('pendiente', fila_pend)
        self.assertIn('aprobada', fila_apr)

    def test_trazabilidad_render_indicadores_interaccion(self):
        self.client.force_login(self.director)
        r = self.client.get('/panel/trazabilidad/')
        self.assertContains(r, 'Pendientes de aprobación')
        self.assertContains(r, 'Seguimiento con el cliente')


class NavegacionRegresionF4Tests(TestCase):
    """7 y 12-regresión: navegación real por rol y organigrama eliminado."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente = CustomUser.objects.create_user(
            email='f4n-cli@qa.local', password=PASSWORD, role=Role.CLIENTE,
            empresa=make_empresa('Nav SA'))
        cls.docente = make_user('f4n-doc@qa.local', Role.DOCENTE, Area.SISTEMAS)
        cls.coordinador = make_user('f4n-coord@qa.local', Role.COORDINADOR, Area.SISTEMAS)
        cls.director = make_user('f4n-dir@qa.local', Role.DIRECTOR)
        cls.est = CustomUser.objects.create_user(
            email='f4n-est@qa.local', password=PASSWORD, role=Role.ESTUDIANTE,
            area=Area.SISTEMAS, student_type=StudentType.CONSULTOR)

    def test_landing_sin_organigrama(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertNotContains(r, 'citi-organigrama.png')
        self.assertNotContains(r, 'orgModal')
        self.assertNotContains(r, 'org-scroll')
        self.assertContains(r, 'modalidades')  # diferenciación presente

    def test_mis_solicitudes_cliente_y_notificaciones(self):
        self.client.force_login(self.cliente)
        for url in (reverse('portal:cliente_dashboard'),
                    reverse('portal:cliente_mis_solicitudes'),
                    reverse('portal:cliente_notificaciones'),
                    reverse('portal:perfil')):
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_perfil_accesible_todos_los_roles(self):
        for user in (self.cliente, self.docente, self.coordinador,
                     self.director, self.est):
            self.client.force_login(user)
            self.assertEqual(
                self.client.get(reverse('portal:perfil')).status_code, 200, user.email)

    def test_staff_seguimiento_por_rol(self):
        url = reverse('portal:staff_seguimiento')
        self.client.force_login(self.coordinador)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.director)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.docente)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(url).status_code, 302)  # rol_required

    def test_cliente_no_ve_seguimiento_de_otro(self):
        cita = CitaAsesoria.objects.create(
            franja=make_franja(Area.SISTEMAS), cliente=self.cliente,
            subespecialidad='web', asunto='Propia')
        self.client.force_login(self.docente)
        r = self.client.get(reverse('portal:cliente_seguimiento', args=[cita.pk]))
        self.assertEqual(r.status_code, 302)


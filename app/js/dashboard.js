/**
 * CITI — Dashboard base helper
 */
function initDashboard(role, activePage, pageTitle, pageSubtitle) {
  const session = CITI_AUTH.requireRole(role, '../');
  if (!session) return null;

  const roleData = CITI_DATA.roles[session.role];

  document.getElementById('sidebarNav').innerHTML = CITI_AUTH.renderSidebar(activePage);
  let badgeLabel = roleData.label;
  if (session.studentType && CITI_DATA.studentTypes[session.studentType]) {
    badgeLabel = CITI_DATA.studentTypes[session.studentType].label;
  }
  document.getElementById('roleBadge').textContent = badgeLabel;
  document.getElementById('roleBadge').style.background = roleData.color + '22';
  document.getElementById('roleBadge').style.color = roleData.color;
  document.getElementById('pageTitle').textContent = pageTitle;
  document.getElementById('pageSubtitle').textContent = pageSubtitle;
  CITI_AUTH.renderUserHeader('userHeader');

  const permsEl = document.getElementById('permsPanel');
  if (permsEl) permsEl.innerHTML = CITI_AUTH.renderPermissionsPanel(session.role);

  document.querySelectorAll('.nav-item').forEach((item) => {
    item.addEventListener('click', (e) => {
      e.preventDefault();
      const page = item.dataset.page;
      document.querySelectorAll('.page-section').forEach((s) => s.classList.remove('active'));
      document.querySelectorAll('.nav-item').forEach((n) => n.classList.remove('active'));
      const section = document.getElementById('page-' + page);
      if (section) section.classList.add('active');
      item.classList.add('active');
      const titles = {
        dashboard: [pageTitle, pageSubtitle],
        solicitudes: ['Solicitudes', 'Gestión de solicitudes entrantes'],
        usuarios: ['Usuarios', 'Gestión de cuentas del sistema'],
        informes: ['Informes', 'Informes y reportes'],
        empresas: ['Banco de empresas', 'Registro de empresas atendidas'],
        config: ['Configuración', 'Parámetros del semestre'],
        asignaciones: ['Asignar equipo', 'Tutor y docente por caso'],
        estudiantes: ['Estudiantes', 'Tutores y consultores del área'],
        recepcion: ['Recepción', 'Atención al público'],
        casos: ['Mis casos', 'Casos asignados'],
        visitas: ['Visitas empresariales', 'Registro de visitas'],
        talleres: ['Talleres', 'Seminarios y capacitaciones'],
        practicas: ['Prácticas', 'Práctica empresarial'],
        consultas: ['Registro de consultas', 'Atención al público'],
        correspondencia: ['Correspondencia', 'Entrada y salida de documentos'],
        radial: ['Programa radial', 'Espacio en emisora universitaria'],
        empleo: ['Bolsa de empleo', 'Oferta y demanda laboral'],
        mensajes: ['Mensajes', 'Comunicación con docente y empresa'],
        solicitar: ['Nueva solicitud', 'Solicitar asesoría o capacitación'],
        'mis-casos': ['Mis casos', 'Estado de tus solicitudes'],
        historial: ['Historial', 'Servicios anteriores'],
      };
      if (titles[page]) {
        document.getElementById('pageTitle').textContent = titles[page][0];
        document.getElementById('pageSubtitle').textContent = titles[page][1];
      }
    });
  });

  document.getElementById('btnLogout').addEventListener('click', () => CITI_AUTH.logout());

  document.querySelectorAll('.page-section').forEach((s) => s.classList.remove('active'));
  const initial = document.getElementById('page-' + activePage);
  if (initial) initial.classList.add('active');

  return session;
}

function estadoBadge(estado) {
  const map = {
    pendiente: 'badge-pending',
    en_proceso: 'badge-active',
    completado: 'badge-done',
    rechazado: 'badge-reject',
  };
  const labels = { pendiente: 'Pendiente', en_proceso: 'En proceso', completado: 'Completado', rechazado: 'Rechazado' };
  return `<span class="badge ${map[estado] || ''}">${labels[estado] || estado}</span>`;
}

/**
 * CITI — Autenticación por rol (5 portales)
 */
const CITI_AUTH = {
  SESSION_KEY: 'citi_session_v3',

  /** Compatibilidad con sesiones anteriores */
  _migrateSession(session) {
    if (!session) return null;
    const map = { admin: 'director', consultor: 'estudiante', tutor: 'estudiante' };
    if (map[session.role]) {
      session.role = map[session.role];
      if (!session.studentType && session.role === 'estudiante') {
        session.studentType = 'tutor';
      }
    }
    return session;
  },

  login(email, password, expectedRole) {
    const user = CITI_DATA.users.find(
      (u) => u.email.toLowerCase() === email.toLowerCase() && u.password === password
    );

    if (!user) {
      return { ok: false, error: 'Correo o contraseña incorrectos.' };
    }

    if (user.role !== expectedRole) {
      const correctRole = CITI_DATA.roles[user.role];
      return {
        ok: false,
        error: `Esta cuenta es de "${correctRole.label}".`,
        redirectRole: user.role,
        redirectStudentType: user.studentType || null,
      };
    }

    const session = {
      userId: user.id,
      email: user.email,
      name: user.name,
      role: user.role,
      meta: user.meta,
      area: user.area || null,
      empresaId: user.empresaId || null,
      studentType: user.studentType || null,
      loginAt: new Date().toISOString(),
      token: btoa(`${user.id}:${user.role}:${Date.now()}`),
    };

    localStorage.setItem(this.SESSION_KEY, JSON.stringify(session));
    return { ok: true, session };
  },

  logout() {
    localStorage.removeItem(this.SESSION_KEY);
    localStorage.removeItem('citi_session_v2');
    if (typeof CITI_FLOW !== 'undefined') {
      const f = CITI_FLOW.get();
      if (f && f.id === 5) CITI_FLOW.advance();
    }
    if (typeof CITI_UI !== 'undefined') CITI_UI.toast('Sesión cerrada', 'info');
    setTimeout(() => { window.location.href = '../login.html'; }, 400);
  },

  getSession() {
    try {
      let raw = localStorage.getItem(this.SESSION_KEY);
      if (!raw) raw = localStorage.getItem('citi_session_v2');
      if (!raw) return null;
      const session = this._migrateSession(JSON.parse(raw));
      if (!session?.role || !session?.token) return null;
      return session;
    } catch {
      return null;
    }
  },

  requireRole(allowedRoles, basePath = '../') {
    const session = this.getSession();
    const roles = Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles];

    if (!session) {
      window.location.href = `${basePath}login.html`;
      return null;
    }

    if (!roles.includes(session.role)) {
      const portal = CITI_DATA.roles[session.role];
      if (typeof CITI_UI !== 'undefined') CITI_UI.toast('Acceso no autorizado', 'error');
      window.location.href = `${basePath}${portal.dashboard}`;
      return null;
    }

    return session;
  },

  isConsultor(session) {
    return session?.role === 'estudiante' && session.studentType === 'consultor';
  },

  isTutor(session) {
    return session?.role === 'estudiante' && session.studentType === 'tutor';
  },

  renderUserHeader(containerId) {
    const session = this.getSession();
    if (!session) return;
    const el = document.getElementById(containerId);
    if (!el) return;
    const role = CITI_DATA.roles[session.role];
    let subtitle = role.label;
    if (session.studentType && CITI_DATA.studentTypes[session.studentType]) {
      subtitle = CITI_DATA.studentTypes[session.studentType].label;
    }
    el.innerHTML = `
      <div class="user-chip">
        <div class="user-avatar" style="background:${role.color}22;color:${role.color}">${role.icon}</div>
        <div class="user-info">
          <strong>${session.name}</strong>
          <span>${subtitle}</span>
        </div>
      </div>
    `;
  },

  renderSidebar(activePage) {
    const session = this.getSession();
    if (!session) return '';

    const menus = {
      director: [
        { id: 'dashboard', label: 'Panel general', icon: '📊' },
        { id: 'solicitudes', label: 'Solicitudes', icon: '📥' },
        { id: 'usuarios', label: 'Usuarios', icon: '👥' },
        { id: 'informes', label: 'Informes UCC', icon: '📄' },
        { id: 'empresas', label: 'Banco empresas', icon: '🏢' },
        { id: 'config', label: 'Configuración', icon: '⚙️' },
      ],
      coordinador: [
        { id: 'dashboard', label: 'Mi área', icon: '📊' },
        { id: 'solicitudes', label: 'Aprobar', icon: '✅' },
        { id: 'asignaciones', label: 'Asignar equipo', icon: '👤' },
        { id: 'estudiantes', label: 'Estudiantes', icon: '🎓' },
        { id: 'visitas', label: 'Visitas', icon: '🚗' },
        { id: 'informes', label: 'Informe mensual', icon: '📄' },
      ],
      docente: [
        { id: 'dashboard', label: 'Mis tutorías', icon: '📊' },
        { id: 'casos', label: 'Casos', icon: '📁' },
        { id: 'informes', label: 'Revisar informes', icon: '✅' },
        { id: 'talleres', label: 'Talleres', icon: '📚' },
        { id: 'practicas', label: 'Prácticas', icon: '💼' },
      ],
      cliente: [
        { id: 'dashboard', label: 'Inicio', icon: '🏠' },
        { id: 'solicitar', label: 'Nueva solicitud', icon: '➕' },
        { id: 'mis-casos', label: 'Mis casos', icon: '📁' },
        { id: 'informes', label: 'Informes', icon: '📄' },
        { id: 'historial', label: 'Historial', icon: '🕐' },
      ],
    };

    if (session.role === 'estudiante') {
      const items = [];
      if (this.isConsultor(session)) {
        items.push(
          { id: 'recepcion', label: 'Recepción', icon: '🎧' },
          { id: 'consultas', label: 'Consultas', icon: '📝' },
          { id: 'correspondencia', label: 'Correspondencia', icon: '✉️' },
          { id: 'empleo', label: 'Bolsa empleo', icon: '💼' }
        );
      }
      if (this.isTutor(session)) {
        items.push(
          { id: 'casos', label: 'Mis casos', icon: '📁' },
          { id: 'informes', label: 'Informes', icon: '📝' },
          { id: 'mensajes', label: 'Mensajes', icon: '💬' }
        );
      }
      items.push({ id: 'radial', label: 'Programa radial', icon: '📻' });
      return items.map((item) => `
        <a href="#" class="nav-item ${item.id === activePage ? 'active' : ''}" data-page="${item.id}">
          <span class="nav-icon">${item.icon}</span>${item.label}
        </a>`).join('');
    }

    const items = menus[session.role] || [];
    return items.map((item) => `
      <a href="#" class="nav-item ${item.id === activePage ? 'active' : ''}" data-page="${item.id}">
        <span class="nav-icon">${item.icon}</span>${item.label}
      </a>`).join('');
  },

  renderPermissionsPanel(roleId) {
    const perms = CITI_DATA.permissions[roleId];
    if (!perms) return '';
    return `
      <div class="perms-grid">
        <div class="perms-can"><h4>✓ Puede</h4><ul>${perms.can.map((p) => `<li>${p}</li>`).join('')}</ul></div>
        <div class="perms-cannot"><h4>✗ No puede</h4><ul>${perms.cannot.map((p) => `<li>${p}</li>`).join('')}</ul></div>
      </div>
    `;
  },
};

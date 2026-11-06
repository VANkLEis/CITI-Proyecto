/**
 * CITI Hi-Fi UI — Toast, Modal, Flow helpers
 */
const CITI_UI = {
  toast(msg, type = 'info', duration = 3500) {
    let container = document.querySelector('.toast-container');
    if (!container) {
      container = document.createElement('div');
      container.className = 'toast-container';
      document.body.appendChild(container);
    }
    const icons = { success: '✓', error: '✕', info: 'ℹ', warning: '⚠' };
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.innerHTML = `<span>${icons[type] || 'ℹ'}</span><span>${msg}</span>`;
    container.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateX(20px)';
      el.style.transition = 'all 0.3s';
      setTimeout(() => el.remove(), 300);
    }, duration);
  },

  modal({ title, body, confirmText = 'Confirmar', cancelText = 'Cancelar', onConfirm, onCancel }) {
    const overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.innerHTML = `
      <div class="modal" role="dialog">
        <div class="modal-header"><h3>${title}</h3></div>
        <div class="modal-body">${body}</div>
        <div class="modal-footer">
          <button class="btn btn-secondary" data-action="cancel">${cancelText}</button>
          <button class="btn btn-primary" data-action="confirm">${confirmText}</button>
        </div>
      </div>`;
    document.body.appendChild(overlay);
    const close = () => overlay.remove();
    overlay.querySelector('[data-action="cancel"]').onclick = () => { onCancel?.(); close(); };
    overlay.querySelector('[data-action="confirm"]').onclick = () => { onConfirm?.(); close(); };
    overlay.onclick = (e) => { if (e.target === overlay) { onCancel?.(); close(); } };
  },

  showLayerTag() { /* deshabilitado en producción */ },
};

const CITI_FLOW = {
  KEY: 'citi_prototype_flow',

  start(flowId) {
    const flows = {
      1: { name: 'Login correcto por rol', step: 0, steps: ['Landing', 'Login', 'Dashboard'] },
      2: { name: 'Login incorrecto (aislamiento)', step: 0, steps: ['Login Admin', 'Error rol', 'Login Cliente', 'Dashboard Cliente'] },
      3: { name: 'Solicitud de asesoría CU-01', step: 0, steps: ['Cliente solicita', 'Coord. aprueba', 'Coord. asigna', 'Tutor informe', 'Docente revisa', 'Cliente firma'] },
      4: { name: 'Registro recepción', step: 0, steps: ['Consultor', 'Registro', 'Tabla actualizada'] },
      5: { name: 'Cerrar sesión', step: 0, steps: ['Dashboard', 'Logout', 'Login'] },
    };
    sessionStorage.setItem(this.KEY, JSON.stringify({ id: flowId, ...flows[flowId] }));
    this.renderBar();
  },

  get() {
    try { return JSON.parse(sessionStorage.getItem(this.KEY)); } catch { return null; }
  },

  advance() {
    const f = this.get();
    if (!f) return;
    f.step = Math.min(f.step + 1, f.steps.length - 1);
    sessionStorage.setItem(this.KEY, JSON.stringify(f));
    this.renderBar();
  },

  clear() {
    sessionStorage.removeItem(this.KEY);
    document.querySelector('.flow-bar')?.remove();
  },

  renderBar() {
    const params = new URLSearchParams(window.location.search);
    if (!params.get('flow')) return;
    const f = this.get();
    if (!f) return;
    let bar = document.querySelector('.flow-bar');
    if (!bar) {
      bar = document.createElement('div');
      bar.className = 'flow-bar';
      document.body.prepend(bar);
      document.body.style.paddingTop = '44px';
    }
    bar.innerHTML = `
      <div><strong>Flujo ${f.id}:</strong> ${f.name}</div>
      <div class="flow-steps">${f.steps.map((s, i) =>
        `<span class="flow-step-dot ${i < f.step ? 'done' : ''} ${i === f.step ? 'current' : ''}" title="${s}"></span>`
      ).join('')} <span style="margin-left:8px;opacity:.8">${f.steps[f.step]}</span></div>
      <button class="btn btn-sm btn-secondary" onclick="CITI_FLOW.clear()" style="color:white;border-color:rgba(255,255,255,.3)">✕ Salir flujo</button>`;
  },
};

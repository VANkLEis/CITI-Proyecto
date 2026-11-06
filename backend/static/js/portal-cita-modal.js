(function () {
  const overlay = document.getElementById('citaModalOverlay');
  const body = document.getElementById('citaModalBody');
  if (!overlay || !body) return;

  function closeModal() {
    overlay.hidden = true;
    overlay.setAttribute('aria-hidden', 'true');
    body.innerHTML = '';
    document.body.classList.remove('cita-modal-open');
  }

  function openModal() {
    overlay.hidden = false;
    overlay.setAttribute('aria-hidden', 'false');
    document.body.classList.add('cita-modal-open');
  }

  async function loadCitaDetalle(citaId) {
    body.innerHTML = '<p class="cita-muted" style="padding:1.5rem;">Cargando detalle…</p>';
    openModal();
    try {
      const res = await fetch('/panel/cita/' + citaId + '/detalle/', {
        credentials: 'same-origin',
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (!res.ok) {
        body.innerHTML = '<p class="field-error" style="padding:1.5rem;">No se pudo cargar el detalle.</p>';
        return;
      }
      body.innerHTML = await res.text();
      body.querySelectorAll('.cita-modal-close').forEach(function (btn) {
        btn.addEventListener('click', closeModal);
      });
    } catch (e) {
      body.innerHTML = '<p class="field-error" style="padding:1.5rem;">Error de conexión.</p>';
    }
  }

  document.querySelectorAll('[data-cita-detalle]').forEach(function (el) {
    el.addEventListener('click', function (e) {
      const id = el.getAttribute('data-cita-detalle');
      if (!id) return;
      if (el.tagName === 'A') e.preventDefault();
      loadCitaDetalle(id);
    });
  });

  document.querySelectorAll('tr[data-cita-row]').forEach(function (row) {
    row.addEventListener('click', function (e) {
      if (e.target.closest('a, button, input, select, textarea')) return;
      const id = row.getAttribute('data-cita-row');
      if (id) loadCitaDetalle(id);
    });
  });

  overlay.addEventListener('click', function (e) {
    if (e.target === overlay) closeModal();
  });

  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape' && !overlay.hidden) closeModal();
  });
})();

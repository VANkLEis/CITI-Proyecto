/* Zona pública CITI — comportamiento progresivo (Fase 05).
   - Menú móvil.
   - Videos decorativos: respeta prefers-reduced-motion y cae a la imagen de
     respaldo si el MP4 no existe todavía (los archivos finales de IA son un
     insumo externo reemplazable). */
(function () {
  'use strict';

  var toggle = document.getElementById('pubNavToggle');
  var nav = document.getElementById('pubNav');
  if (toggle && nav) {
    toggle.addEventListener('click', function () {
      var abierto = nav.classList.toggle('is-open');
      toggle.setAttribute('aria-expanded', abierto ? 'true' : 'false');
    });
    nav.addEventListener('click', function (evento) {
      if (evento.target.closest('a')) {
        nav.classList.remove('is-open');
        toggle.setAttribute('aria-expanded', 'false');
      }
    });
  }

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  var videos = Array.prototype.slice.call(
    document.querySelectorAll('[data-media-video] video'));

  function marcarFallback(video) {
    var wrapper = video.closest('[data-media-video]');
    if (!wrapper) { return; }
    wrapper.classList.add('is-fallback');
    wrapper.dataset.failed = '1';
  }

  function aplicar() {
    videos.forEach(function (video) {
      var wrapper = video.closest('[data-media-video]');
      if (!wrapper) { return; }
      if (reduce.matches) {
        video.pause();
        wrapper.classList.add('is-fallback');
        return;
      }
      if (wrapper.dataset.failed === '1') { return; }
      wrapper.classList.remove('is-fallback');
      var intento = video.play();
      if (intento && typeof intento.catch === 'function') {
        intento.catch(function () { /* autoplay bloqueado: queda el poster */ });
      }
    });
  }

  videos.forEach(function (video) {
    video.addEventListener('error', function () { marcarFallback(video); });
    var source = video.querySelector('source');
    if (source) {
      source.addEventListener('error', function () { marcarFallback(video); });
    }
  });

  aplicar();
  if (typeof reduce.addEventListener === 'function') {
    reduce.addEventListener('change', aplicar);
  }
})();

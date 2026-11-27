/** Boot — barra de flujo solo en modo demo (?flow=) */
document.addEventListener('DOMContentLoaded', () => {
  if (new URLSearchParams(location.search).get('flow') && typeof CITI_FLOW !== 'undefined') {
    CITI_FLOW.renderBar();
  }
});

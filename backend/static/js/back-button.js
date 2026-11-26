(function () {
  const sameOrigin = window.location.origin;

  document.querySelectorAll('[data-back-button]').forEach(function (link) {
    link.addEventListener('click', function (event) {
      if (event.defaultPrevented || event.button !== 0 ||
          event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
        return;
      }
      try {
        const referrer = document.referrer ? new URL(document.referrer) : null;
        const fromLogin = referrer && referrer.pathname.indexOf('/cuenta/login') === 0;
        if (referrer && referrer.origin === sameOrigin && !fromLogin &&
            window.history.length > 1) {
          event.preventDefault();
          window.history.back();
        }
      } catch (error) {
        /* Si el referrer no es una URL válida, se usa el href de respaldo. */
      }
    });
  });
})();

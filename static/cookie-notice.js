(function () {
  const notice = document.querySelector('[data-cookie-notice]');
  if (!notice) return;
  try {
    if (localStorage.getItem('push-cookie-notice') === 'dismissed') {
      notice.hidden = true;
      notice.style.display = 'none';
      return;
    }
  } catch (_) {}
  notice.hidden = false;
  document.addEventListener('click', function (event) {
    if (!event.target.closest('[data-cookie-dismiss]')) return;
    notice.hidden = true;
    notice.style.display = 'none';
    try { localStorage.setItem('push-cookie-notice', 'dismissed'); } catch (_) {}
  });
})();

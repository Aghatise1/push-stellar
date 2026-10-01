(function () {
  const notice = document.querySelector('[data-cookie-notice]');
  if (!notice) return;
  const preferenceKey = 'push-cookie-consent';
  const preferenceCookie = 'push_cookie_consent';

  function readPreference() {
    try {
      const stored = localStorage.getItem(preferenceKey);
      if (stored) return stored;
    } catch (_) {}
    const match = document.cookie.match(new RegExp('(?:^|; )' + preferenceCookie + '=([^;]*)'));
    return match ? decodeURIComponent(match[1]) : '';
  }

  const preference = readPreference();
  if (preference === 'accepted' || preference === 'declined') {
    notice.hidden = true;
    return;
  }

  notice.hidden = false;
  document.addEventListener('click', function (event) {
    const choiceButton = event.target.closest('[data-cookie-choice]');
    if (!choiceButton) return;
    const choice = choiceButton.dataset.cookieChoice;
    if (choice !== 'accepted' && choice !== 'declined') return;

    notice.hidden = true;
    try {
      localStorage.setItem(preferenceKey, choice);
      localStorage.removeItem('push-cookie-notice');
    } catch (_) {}
    document.cookie = preferenceCookie + '=' + encodeURIComponent(choice) +
      '; Max-Age=31536000; Path=/; SameSite=Lax' +
      (window.location.protocol === 'https:' ? '; Secure' : '');

    window.dispatchEvent(new CustomEvent('push:cookie-consent', {
      detail: { optionalCookies: choice === 'accepted' }
    }));
  });
})();

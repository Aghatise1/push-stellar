(function () {
  const notice = document.querySelector('[data-cookie-notice]');
  if (!notice) return;
  const preferenceKey = 'push-cookie-consent';

  try {
    const preference = localStorage.getItem(preferenceKey);
    if (preference === 'accepted' || preference === 'declined') {
      notice.hidden = true;
      return;
    }
  } catch (_) {}

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

    window.dispatchEvent(new CustomEvent('push:cookie-consent', {
      detail: { optionalCookies: choice === 'accepted' }
    }));
  });
})();

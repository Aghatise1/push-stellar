(function () {
  function copyText(value) {
    if (legacyCopy(value)) return Promise.resolve();
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(value);
    }
    return Promise.reject(new Error('Copy unavailable'));
  }
  function legacyCopy(value) {
    var field = document.createElement('textarea');
    field.value = value;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    var copied = document.execCommand('copy');
    field.remove();
    return copied;
  }
  function attach(button) {
    button.addEventListener('click', function () {
    var url = window.location.origin + window.location.pathname;
    copyText(url).then(function () {
      var original = button.textContent;
      button.textContent = button.getAttribute('data-copied-label') || 'Link copied';
      button.setAttribute('aria-live', 'polite');
      window.setTimeout(function () { button.textContent = original; }, 1800);
    }).catch(function () {
      window.prompt('Copy this job link:', url);
    });
    });
  }
  function init() {
    document.querySelectorAll('[data-copy-current]').forEach(attach);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}());

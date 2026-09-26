(function () {
  function copyText(value) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(value).catch(function () { return legacyCopy(value); });
    }
    return legacyCopy(value);
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
    return copied ? Promise.resolve() : Promise.reject(new Error('Copy unavailable'));
  }
  document.addEventListener('click', function (event) {
    var button = event.target.closest('[data-copy-current]');
    if (!button) return;
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
}());

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
    var targetSelector = button.getAttribute('data-copy-target');
    var target = targetSelector ? document.querySelector(targetSelector) : null;
    var url = target ? target.value : window.location.origin + window.location.pathname;
    var original = button.textContent;
    var settled = false;
    if (target) { target.focus(); target.select(); target.setSelectionRange(0, target.value.length); }
    button.textContent = 'Copying…';
    function finish(label) {
      if (settled) return;
      settled = true;
      button.textContent = label;
      button.setAttribute('aria-live', 'polite');
      window.setTimeout(function () { button.textContent = original; }, 1800);
    }
    copyText(url).then(function () {
      finish(button.getAttribute('data-copied-label') || 'Link copied');
    }).catch(function () {
      finish('Select link below');
    });
    window.setTimeout(function () { finish('Select link below'); }, 900);
    });
  }
  function init() {
    document.querySelectorAll('[data-copy-current],[data-copy-target]').forEach(attach);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}());

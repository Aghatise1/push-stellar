(function () {
  document.addEventListener('submit', function (event) {
    const form = event.target;
    if (!(form instanceof HTMLFormElement) || !form.checkValidity()) return;
    if (form.dataset.submitting === 'true') {
      event.preventDefault();
      return;
    }
    form.dataset.submitting = 'true';
    form.setAttribute('aria-busy', 'true');
    const submitter = event.submitter;
    if (submitter && !submitter.name) {
      submitter.disabled = true;
      submitter.dataset.originalLabel = submitter.textContent;
      submitter.textContent = 'Working…';
    }
  });
  window.addEventListener('pageshow', function () {
    document.querySelectorAll('form[data-submitting="true"]').forEach(function (form) {
      delete form.dataset.submitting;
      form.removeAttribute('aria-busy');
      form.querySelectorAll('[data-original-label]').forEach(function (button) {
        button.disabled = false;
        button.textContent = button.dataset.originalLabel;
        delete button.dataset.originalLabel;
      });
    });
  });
})();

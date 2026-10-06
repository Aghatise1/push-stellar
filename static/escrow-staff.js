(function () {
  'use strict';
  document.querySelectorAll('[data-staff-check]').forEach(function (button) {
    button.addEventListener('click', async function () {
      var status = document.querySelector('[data-escrow-status]');
      button.disabled = true;
      try {
        var response = await fetch(button.dataset.endpoint, {method:'POST', credentials:'same-origin', headers:{'Content-Type':'application/json','X-CSRFToken':document.querySelector('[name=csrfmiddlewaretoken]').value}, body:JSON.stringify({wallet:button.dataset.staffCheck})});
        var result = await response.json();
        status.textContent = result.message;
      } catch (_) { status.textContent = 'Could not check contract access. Please retry.'; }
      finally { button.disabled = false; }
    });
  });
})();

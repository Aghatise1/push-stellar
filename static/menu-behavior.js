(function () {
  var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  function panelFor(details) {
    return details.querySelector(':scope > nav, :scope > .account-popover');
  }

  function closeMenu(details) {
    if (!details || !details.open) return;
    var panel = panelFor(details);
    if (reduceMotion || !panel || !panel.animate) {
      details.open = false;
      return;
    }
    panel.animate([
      { opacity: 1, transform: 'scale(1)' },
      { opacity: 0, transform: 'scale(0.96)' }
    ], { duration: 140, easing: 'cubic-bezier(0.23, 1, 0.32, 1)' }).finished.then(function () {
      details.open = false;
    }).catch(function () {
      details.open = false;
    });
  }

  document.addEventListener('click', function (event) {
    document.querySelectorAll('.compact-menu[open], .account-menu[open]').forEach(function (details) {
      if (!details.contains(event.target)) closeMenu(details);
    });
  });

  document.addEventListener('keydown', function (event) {
    if (event.key !== 'Escape') return;
    document.querySelectorAll('.compact-menu[open], .account-menu[open]').forEach(closeMenu);
  });

  document.querySelectorAll('.compact-menu > summary, .account-menu > summary').forEach(function (summary) {
    summary.addEventListener('click', function (event) {
      var details = summary.parentElement;
      if (!details.open) return;
      event.preventDefault();
      closeMenu(details);
    });
  });
}());

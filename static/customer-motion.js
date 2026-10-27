(function () {
  'use strict';

  var observer = null;

  function show(element) {
    element.setAttribute('data-motion-visible', '');
    if (observer) observer.unobserve(element);
  }

  function observePending() {
    if (!observer || document.hidden) return;
    document.querySelectorAll('.customer-app-mode .scroll-reveal[data-motion-pending]:not([data-motion-visible])').forEach(function (element) {
      observer.observe(element);
    });
  }

  function init() {
    var body = document.body;
    if (!body || !body.classList.contains('customer-app-mode')) return;
    var preference = window.matchMedia('(prefers-reduced-motion: reduce)');
    if (preference.matches || document.hidden) return;

    var elements = Array.prototype.slice.call(document.querySelectorAll('.customer-app-mode main .app-reveal, .customer-app-mode main .scroll-reveal')).filter(function (element) {
      return !element.matches('nav, .consumer-priority, .consumer-wallet-states') && !element.querySelector('form, [data-wallet-connect]');
    });
    if (!elements.length) return;

    body.classList.add('customer-motion-ready');
    elements.forEach(function (element) {
      element.setAttribute('data-motion-pending', '');
    });

    window.requestAnimationFrame(function () {
      document.querySelectorAll('.customer-app-mode .app-reveal[data-motion-pending]').forEach(show);
    });

    if ('IntersectionObserver' in window) {
      observer = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) show(entry.target);
        });
      }, { rootMargin: '0px 0px -7% 0px', threshold: 0.08 });
      observePending();
    } else {
      document.querySelectorAll('.customer-app-mode .scroll-reveal[data-motion-pending]').forEach(show);
    }

    document.addEventListener('visibilitychange', function () {
      if (!observer) return;
      if (document.hidden) observer.disconnect();
      else observePending();
    });
    document.addEventListener('focusin', function (event) {
      var section = event.target.closest('[data-motion-pending]');
      if (section) show(section);
    });
    if (preference.addEventListener) preference.addEventListener('change', function (event) {
      if (!event.matches) return;
      body.classList.remove('customer-motion-ready');
      elements.forEach(show);
      if (observer) observer.disconnect();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, { once: true });
  else init();
}());

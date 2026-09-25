(function () {
  function init() {
    var section = document.querySelector('[data-handshake]');
    if (!section) return;
    var left = section.querySelector('.hand-left');
    var right = section.querySelector('.hand-right');
    var seal = section.querySelector('.agreement-seal');
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var queued = false;

    function render() {
      queued = false;
      if (reduceMotion) {
        left.style.transform = 'translate3d(0, -50%, 0)';
        right.style.transform = 'translate3d(0, -50%, 0)';
        seal.style.opacity = '1';
        seal.style.transform = 'translate3d(-50%, -50%, 0) scale(1)';
        return;
      }
      var rect = section.getBoundingClientRect();
      var distance = Math.max(1, rect.height - window.innerHeight);
      var progress = Math.max(0, Math.min(1, -rect.top / distance));
      var approachRaw = Math.min(1, progress / 0.72);
      var approach = approachRaw * approachRaw * (3 - 2 * approachRaw);
      var joined = Math.max(0, Math.min(1, (progress - 0.72) / 0.28));
      var tremor = Math.sin(joined * Math.PI * 3) * 1.8 * (1 - joined);
      var leftX = -36 + (36 * approach);
      var rightX = 36 - (36 * approach);
      left.style.transform = 'translate3d(' + leftX + '%, calc(-50% + ' + tremor + 'px), 0) rotate(' + (-1.5 + 1.5 * approach) + 'deg)';
      right.style.transform = 'translate3d(' + rightX + '%, calc(-50% - ' + tremor + 'px), 0) rotate(' + (1.5 - 1.5 * approach) + 'deg)';
      var sealProgress = Math.max(0, Math.min(1, (progress - 0.76) / 0.16));
      seal.style.opacity = String(sealProgress);
      seal.style.transform = 'translate3d(-50%, -50%, 0) scale(' + (0.94 + sealProgress * 0.06) + ')';
    }

    function requestRender() {
      if (queued) return;
      queued = true;
      window.requestAnimationFrame(render);
    }

    window.addEventListener('scroll', requestRender, { passive: true });
    window.addEventListener('resize', requestRender);
    render();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}());

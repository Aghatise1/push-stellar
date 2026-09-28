(function () {
  function init() {
    var reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var copyButton = document.querySelector('[data-copy]');
    if (copyButton) {
      copyButton.addEventListener('click', function () {
        navigator.clipboard.writeText(copyButton.getAttribute('data-copy')).then(function () {
          var original = copyButton.textContent;
          copyButton.textContent = 'Address copied';
          window.setTimeout(function () { copyButton.textContent = original; }, 1800);
        });
      });
    }

    var chatThread = document.querySelector('.chat-thread');
    if (chatThread) chatThread.scrollTop = chatThread.scrollHeight;

    if (reduceMotion || !window.gsap) return;
    var gsap = window.gsap;

    gsap.from('.app-reveal', {
      opacity: 0,
      y: 12,
      duration: 0.22,
      stagger: 0.04,
      ease: 'power3.out',
      clearProps: 'transform,opacity'
    });

    var roleDashboard = document.querySelector('[data-role-dashboard]');
    if (roleDashboard) {
      gsap.from('[data-role-reveal]', {
        opacity: 0,
        y: 10,
        duration: 0.24,
        ease: 'power3.out',
        clearProps: 'transform,opacity'
      });
      gsap.from('[data-role-card]', {
        opacity: 0,
        y: 12,
        duration: 0.26,
        stagger: 0.045,
        delay: 0.05,
        ease: 'power3.out',
        clearProps: 'transform,opacity'
      });
    }

    if (window.ScrollTrigger) {
      gsap.registerPlugin(window.ScrollTrigger);
      gsap.utils.toArray('.scroll-reveal').forEach(function (section) {
        gsap.from(section, {
          scrollTrigger: { trigger: section, start: 'top 88%', once: true },
          opacity: 0,
          y: 16,
          duration: 0.26,
          ease: 'power3.out',
          clearProps: 'transform,opacity'
        });
      });
    }

    var stage = document.querySelector('.motion-stage');
    var flowToken = document.querySelector('.flow-token');
    if (stage && flowToken) {
      var flow = gsap.timeline({ repeat: -1, repeatDelay: 0.5, repeatRefresh: true });
      flow.set(flowToken, { x: 0, y: 10, scale: 0.92, opacity: 0 })
        .to(flowToken, { opacity: 1, scale: 1, duration: 0.35, ease: 'power3.out' })
        .to(flowToken, { x: function () { return (stage.clientWidth - flowToken.offsetWidth) * 0.44; }, y: -34, duration: 1.15, ease: 'power2.inOut' })
        .to('.stage-review i', { scale: 1.45, duration: 0.16, yoyo: true, repeat: 1 }, '<0.92')
        .to(flowToken, { x: function () { return stage.clientWidth - flowToken.offsetWidth - 5; }, y: 10, duration: 1.15, ease: 'power2.inOut' })
        .to('.stage-paid i', { scale: 1.5, duration: 0.18, yoyo: true, repeat: 1 }, '<0.92')
        .to(flowToken, { opacity: 0, scale: 0.94, duration: 0.3, delay: 0.45 });
    }

    gsap.to('.flow-spark', { rotation: 360, scale: 1.35, duration: 2.8, repeat: -1, yoyo: true, ease: 'sine.inOut', stagger: 0.45 });
    gsap.to('.token-disc', { y: -8, rotation: 3, duration: 2.8, repeat: -1, yoyo: true, ease: 'sine.inOut' });
    gsap.to('.orbit-one', { rotation: 360, duration: 22, repeat: -1, ease: 'none' });
    gsap.to('.orbit-two', { rotation: -360, duration: 16, repeat: -1, ease: 'none' });
    gsap.to('.card-front', { y: -12, rotation: -4, duration: 3.2, repeat: -1, yoyo: true, ease: 'sine.inOut' });
    gsap.to('.card-back', { y: 10, rotation: 5, duration: 3.8, repeat: -1, yoyo: true, ease: 'sine.inOut' });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
}());

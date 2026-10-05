(() => {
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const reveals = [...document.querySelectorAll('[data-reveal]')];
  if (!reveals.length) return;

  document.body.classList.add('home-motion-ready');
  document.querySelectorAll('[data-stagger]').forEach((group) => {
    [...group.children].forEach((item, index) => item.style.setProperty('--reveal-index', index));
  });

  const storyVideo = document.querySelector('[data-story-video]');
  if (storyVideo && reduceMotion) storyVideo.pause();

  if (reduceMotion || !('IntersectionObserver' in window)) {
    reveals.forEach((section) => section.classList.add('is-visible'));
    return;
  }

  const revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add('is-visible');
      revealObserver.unobserve(entry.target);
    });
  }, { threshold: 0.01, rootMargin: '0px' });

  reveals.forEach((section) => revealObserver.observe(section));

  if (storyVideo) {
    const videoObserver = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) storyVideo.play().catch(() => {});
      else storyVideo.pause();
    }, { threshold: 0.18 });
    videoObserver.observe(storyVideo);
  }

  const header = document.querySelector('.site-header');
  const parallaxItems = [...document.querySelectorAll('[data-parallax]')];
  const progress = document.createElement('span');
  progress.className = 'home-scroll-progress';
  progress.setAttribute('aria-hidden', 'true');
  header?.append(progress);

  let scheduled = false;
  const updateProgress = () => {
    const maximum = document.documentElement.scrollHeight - window.innerHeight;
    const amount = maximum > 0 ? Math.min(1, Math.max(0, window.scrollY / maximum)) : 0;
    progress.style.transform = `scaleX(${amount})`;
    parallaxItems.forEach((item) => {
      const bounds = item.getBoundingClientRect();
      const centreOffset = (bounds.top + bounds.height / 2 - window.innerHeight / 2) / window.innerHeight;
      const shift = Math.max(-16, Math.min(16, centreOffset * -18));
      item.style.setProperty('--parallax-y', `${shift}px`);
    });
    scheduled = false;
  };
  const requestProgress = () => {
    if (scheduled) return;
    scheduled = true;
    window.requestAnimationFrame(updateProgress);
  };
  updateProgress();
  window.addEventListener('scroll', requestProgress, { passive: true });

  const sectionLinks = [...document.querySelectorAll('.primary-nav a[href*="#"]')];
  const sectionMap = new Map(sectionLinks.map((link) => [link.hash.slice(1), link]));
  const sectionObserver = new IntersectionObserver((entries) => {
    const current = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
    if (!current) return;
    sectionLinks.forEach((link) => link.removeAttribute('aria-current'));
    sectionMap.get(current.target.id)?.setAttribute('aria-current', 'location');
  }, { threshold: [0.2, 0.45, 0.7], rootMargin: '-25% 0px -55% 0px' });
  document.querySelectorAll('#product, #how-it-works, #opportunities, #investors').forEach((section) => sectionObserver.observe(section));
})();

(() => {
  const body = document.body;
  const endpoint = body.dataset.activityEndpoint;
  if (!endpoint) return;

  let latestId = Number(body.dataset.latestNotificationId || 0);
  const setCount = (key, value) => {
    document.querySelectorAll(`[data-live-count="${key}"]`).forEach((badge) => {
      badge.textContent = value > 99 ? '99+' : String(value);
      badge.hidden = value < 1;
      badge.classList.toggle('attention-count', key === 'work' && value > 0);
    });
  };
  const announce = (notice) => {
    if (!notice || notice.id <= latestId) return;
    latestId = notice.id;
    const live = document.querySelector('[data-activity-live]');
    if (!live) return;
    live.textContent = notice.title;
    live.href = notice.link && notice.link.startsWith('/') ? notice.link : '/notifications/';
    live.hidden = false;
    window.setTimeout(() => { live.hidden = true; }, 7000);
  };
  const refresh = async () => {
    if (document.hidden) return;
    try {
      const response = await fetch(endpoint, { credentials: 'same-origin', cache: 'no-store' });
      if (!response.ok) return;
      const data = await response.json();
      setCount('notifications', data.notifications);
      setCount('messages', data.messages);
      setCount('assigned', data.assigned);
      setCount('work', data.work_attention);
      announce(data.latest);
    } catch (_) {
      // The next scheduled check will recover without interrupting the user.
    }
  };

  window.setInterval(refresh, 20000);
  document.addEventListener('visibilitychange', refresh);
})();

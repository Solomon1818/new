// Auto-dismiss alerts
document.querySelectorAll('.alert').forEach(alert => {
  setTimeout(() => {
    alert.style.opacity = '0';
    alert.style.transition = 'opacity 0.4s';
    setTimeout(() => alert.remove(), 400);
  }, 4000);
});

// Hamburger / sidebar toggle
const hamburger = document.getElementById('hamburger');
const sidebar   = document.getElementById('sidebar');
const overlay   = document.getElementById('overlay');

function toggleSidebar() {
  sidebar?.classList.toggle('open');
  hamburger?.classList.toggle('open');
  overlay?.classList.toggle('active');
  document.body.style.overflow = sidebar?.classList.contains('open') ? 'hidden' : '';
}
hamburger?.addEventListener('click', toggleSidebar);
overlay?.addEventListener('click', toggleSidebar);

// Close on nav link click (mobile)
document.querySelectorAll('.nav-links a').forEach(a => {
  a.addEventListener('click', () => {
    if (window.innerWidth <= 768) toggleSidebar();
  });
});

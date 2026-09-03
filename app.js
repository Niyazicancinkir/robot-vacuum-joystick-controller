const navItems = [...document.querySelectorAll('.nav-item')];
const sections = [...document.querySelectorAll('.page-section')];
const toast = document.querySelector('.toast');

const observer = new IntersectionObserver((entries) => {
  const visible = entries.filter((entry) => entry.isIntersecting).sort((a, b) => b.intersectionRatio - a.intersectionRatio)[0];
  if (!visible) return;
  navItems.forEach((item) => item.classList.toggle('active', item.getAttribute('href') === `#${visible.target.id}`));
}, { rootMargin: '-25% 0px -60% 0px', threshold: [0, 0.25, 0.6] });

sections.forEach((section) => observer.observe(section));

document.querySelectorAll('[data-copy]').forEach((button) => {
  button.addEventListener('click', async () => {
    await navigator.clipboard.writeText(button.dataset.copy);
    toast.classList.add('show');
    window.setTimeout(() => toast.classList.remove('show'), 1700);
  });
});

/* Carga/oculta el overlay de inicio si la página lo tiene.
   Taller.html referenciaba este archivo, pero no existía (404 en consola). */
document.addEventListener('DOMContentLoaded', () => {
  const loader = document.getElementById('loader-wrapper');
  if (!loader) return;
  loader.style.transition = 'opacity 0.5s ease';
  loader.style.opacity = '0';
  setTimeout(() => { loader.style.display = 'none'; }, 500);
});

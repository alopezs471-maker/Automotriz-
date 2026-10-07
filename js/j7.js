document.addEventListener("DOMContentLoaded", () => {
  const modal = document.getElementById("vehicleModal");
  const closeModal = document.getElementById("closeModal");
  const modalCarImg = document.getElementById("modalCarImg");
  const modalCarTitle = document.getElementById("modalCarTitle");
  const modalCarSpecs = document.getElementById("modalCarSpecs");
  const swatches = document.querySelectorAll(".swatch");

  // Abrir modal al hacer clic en "VISUALIZAR"
  document.querySelectorAll(".btn-showroom").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const card = e.target.closest(".showroom-card");
      const title = card.querySelector("h3").innerText;
      const specs = card.querySelector(".car-specs").innerText;
      // Toma la imagen encendida por defecto para el visor
      const imgSrc = card.querySelector(".car-on").getAttribute("src");

      modalCarTitle.innerText = title;
      modalCarSpecs.innerText = specs;
      modalCarImg.setAttribute("src", imgSrc);

      modal.classList.add("active");
    });
  });

  // Cerrar modal
  closeModal.addEventListener("click", () => {
    modal.classList.remove("active");
  });

  // Cerrar haciendo clic fuera del contenedor
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.remove("active");
    }
  });

  // Interacción de cambio de color (Simulación visual con filtros de tono)
  swatches.forEach((swatch) => {
    swatch.addEventListener("click", (e) => {
      swatches.forEach((s) => s.classList.remove("active"));
      e.target.classList.add("active");

      const color = e.target.getAttribute("data-color");
      
      // Aplicamos un filtro sutil de matiz para diferenciar los 3 colores en tiempo real
      if (color === "onyx") {
        modalCarImg.style.filter = "grayscale(100%) brightness(0.8)";
      } else if (color === "platinum") {
        modalCarImg.style.filter = "grayscale(30%) brightness(1.2)";
      } else if (color === "crimson") {
        modalCarImg.style.filter = "sepia(100%) hue-rotate(300deg) saturate(300%) brightness(0.9)";
      }
    });
  });
});
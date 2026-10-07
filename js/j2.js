// Variable para llevar el control de la diapositiva actual
let currentSlide = 0;

// Textos correspondientes a cada diapositiva (coinciden con el orden de tus imágenes)
const sliderData = [
    {
        title: "Rendimiento y Confiabilidad",
        description: "Nuestros vehiculos equipados con rines y llantas actualizados de alto desempeño, diseñado para ofrecerte un agarre superior y una experiencia de conducción inigualable en cualquier ruta."
    },
    {
        title: "Toyota Corolla: Suspensión Avanzada",
        description: "Disfruta de una suspensión mejorada que absorbe cada imperfección del camino, brindando un viaje suave, silencioso y cómodo tanto para el conductor como para los pasajeros."
    },
    {
        title: "Mazda 3",
        description: "Desde la defensa delantera hasta la parte trasera, el exterior fue rediseñado por completo para ser más eficiente y maximizar la aerodinámica el mejor automovil de todos"
    }
];

function updateSliderContent() {
    const titleElement = document.getElementById('sliderTitle');
    const descElement = document.getElementById('sliderDesc');
    
    if (titleElement && descElement) {
        titleElement.textContent = sliderData[currentSlide].title;
        descElement.textContent = sliderData[currentSlide].description;
    }
}

function moveSlide(direction) {
    const track = document.getElementById('sliderTrack');
    if (!track) return;
    
    const slides = track.children;
    const totalSlides = slides.length;
    
    currentSlide = (currentSlide + direction + totalSlides) % totalSlides;
    track.style.transform = `translateX(-${currentSlide * 100}%)`;
    updateSliderContent();
}


setInterval(() => {
    moveSlide(1);
}, 5000);

document.addEventListener("DOMContentLoaded", function() {

    const sectionsToAnimate = document.querySelectorAll('.tesla-specs-section, .tesla-feature-section, .tesla-cta-section');


    const observerOptions = {
        root: null, 
        rootMargin: '0px 0px -50px 0px',
        threshold: 0.05 
    };

    const observerCallback = (entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {

                entry.target.classList.add('visible');

                observer.unobserve(entry.target);
            }
        });
    };

    const observer = new IntersectionObserver(observerCallback, observerOptions);

    // Ponemos a observar cada sección
    sectionsToAnimate.forEach(section => {
        observer.observe(section);
    });
});


/* --- LOGICA DEL CURSOR AUTOMOTRIZ --- */
document.addEventListener("DOMContentLoaded", () => {
    const car = document.querySelector(".car-cursor");
    if (!car) return; // Si la página actual no tiene el div del carro, no ejecuta nada y evita errores

    let mX = window.innerWidth / 2;
    let mY = window.innerHeight / 2;
    let cX = mX, cY = mY;   
    let vX = 0, vY = 0;     
    
    // Configuración física del llavero colgante
    const elasticidad = 0.12;  
    const friccion = 0.74;     
    const gravedad = 0.35;     

    window.addEventListener("mousemove", (e) => {
        mX = e.clientX;
        mY = e.clientY;
    });

    function updateLlaveroPhysics() {
        let fuerzaX = (mX - cX) * elasticidad;
        let fuerzaY = (mY - cY) * elasticidad;

        vX += fuerzaX;
        vY += fuerzaY + gravedad;

        vX *= friccion;
        vY *= friccion;

        cX += vX;
        cY += vY;

        car.style.left = `${cX}px`;
        car.style.top = `${cY}px`;

        const dx = mX - cX;
        const dy = mY - cY;
        
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) {
            const angle = Math.atan2(dy, dx) * (180 / Math.PI) + 90;
            car.style.transform = `translate(-50%, -50%) rotate(${angle}deg)`;
        }

        requestAnimationFrame(updateLlaveroPhysics);
    }
    requestAnimationFrame(updateLlaveroPhysics);

    
    const zonasClickeables = document.querySelectorAll("a, button, .brand-item, .why-card, .prev, .next");
    zonasClickeables.forEach(item => {
        item.addEventListener("mouseenter", () => document.body.classList.add("car-hover-active"));
        item.addEventListener("mouseleave", () => document.body.classList.remove("car-hover-active"));
    });
});


function updateIndexCartBadge() {
  // 1. Obtiene los productos guardados desde el almacenamiento global
  const cartData = localStorage.getItem('premium_cart');
  const cart = cartData ? JSON.parse(cartData) : [];
  
  // 2. Suma las cantidades totales de los productos
  const totalItems = cart.reduce((acc, item) => acc + (item.quantity || 1), 0);
  
  // 3. Busca la burbuja o badge del carrito en index.html y la actualiza
  const badge = document.querySelector('.floating-cart .cart-count');
  if (badge) {
    badge.textContent = totalItems;
  }
}

// Ejecutar al cargar la página index
document.addEventListener('DOMContentLoaded', updateIndexCartBadge);

// Actualizar automáticamente si cambia el carrito desde otra pestaña
window.addEventListener('storage', (e) => {
  if (e.key === 'premium_cart') {
    updateIndexCartBadge();
  }
});
  

  function updateIndexCartBadge() {
    const cartData = localStorage.getItem('premium_cart');
    const cart = cartData ? JSON.parse(cartData) : [];
    
    // Calcula el total de productos agregados
    const totalItems = cart.reduce((acc, item) => acc + (item.quantity || 1), 0);
    
    // Actualiza el número flotante del botón
    const badge = document.getElementById('index-cart-count');
    if (badge) {
        badge.textContent = totalItems;
    }
}

// Ejecutar al cargar index.html
document.addEventListener('DOMContentLoaded', updateIndexCartBadge);

// Detectar cambios en el carrito si el usuario agrega algo desde otra pestaña
window.addEventListener('storage', (e) => {
    if (e.key === 'premium_cart') {
        updateIndexCartBadge();
    }
});


window.addEventListener("load", () => {
    const loader = document.getElementById("loader-wrapper");
    if (loader) {
        loader.classList.add("loader-hidden");
    }
});
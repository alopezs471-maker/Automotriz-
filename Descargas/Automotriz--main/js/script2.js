window.addEventListener("load", () => {
    const loader = document.getElementById("loader-wrapper");
    const heroLeft = document.querySelector(".hero-left");

    if (loader) {
        loader.style.transition = "opacity 0.5s ease";
        loader.style.opacity = "0";

        setTimeout(() => {
            loader.style.display = "none";
            // Activa el recorte para revelar la imagen de la derecha
            if (heroLeft) heroLeft.classList.add("reveal-active");
        }, 500);
    } else {
        if (heroLeft) heroLeft.classList.add("reveal-active");
    }
});


// Animación de entrada por scroll para la sección About
document.addEventListener("DOMContentLoaded", () => {
    const aboutSection = document.querySelector(".about-section");
    if (!aboutSection) return;

    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add("visible");
            }
        });
    }, { threshold: 0.2 });

    observer.observe(aboutSection);
});

// Funcionalidad de Pestañas Interactivas (Tabs)
document.addEventListener("DOMContentLoaded", () => {
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");

            // Remover clase activa de todos los botones y contenidos
            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));

            // Activar botón y contenido correspondiente
            btn.classList.add("active");
            const activeContent = document.getElementById(targetTab);
            if (activeContent) {
                activeContent.classList.add("active");
            }
        });
    });
});


// Animación por scroll para la sección de Proceso
document.addEventListener("DOMContentLoaded", () => {
    const processCards = document.querySelectorAll(".process-card");
    if (!processCards.length) return;

    const cardObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = "1";
                entry.target.style.transform = "translateY(0)";
            }
        });
    }, { threshold: 0.15 });

    processCards.forEach(card => {
        card.style.opacity = "0";
        card.style.transform = "translateY(30px)";
        card.style.transition = "opacity 0.6s ease, transform 0.6s ease";
        cardObserver.observe(card);
    });
});


document.addEventListener("DOMContentLoaded", () => {
    
    // 1. ANIMACIÓN INTERACTIVA DE PESTAÑAS (TABS)
    const tabBtns = document.querySelectorAll(".tab-btn");
    const tabContents = document.querySelectorAll(".tab-content");

    tabBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const targetTab = btn.getAttribute("data-tab");

            tabBtns.forEach(b => b.classList.remove("active"));
            tabContents.forEach(c => c.classList.remove("active"));

            btn.classList.add("active");
            const activeContent = document.getElementById(targetTab);
            if (activeContent) {
                activeContent.classList.add("active");
            }
        });
    });

    // 2. OBSERVADOR DE SCROLL CON RETARDO EN CASCADA (STAGGERED ANIMATION)
    const observerOptions = {
        threshold: 0.15,
        rootMargin: "0px 0px -50px 0px"
    };

    const scrollObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                // Si la sección tiene elementos secundarios (tarjetas)
                const cards = entry.target.querySelectorAll(".process-card, .pricing-card");
                
                if (cards.length > 0) {
                    cards.forEach((card, index) => {
                        setTimeout(() => {
                            card.classList.add("animate-in");
                        }, index * 180); // Retardo de 180ms entre tarjeta y tarjeta
                    });
                } else {
                    entry.target.classList.add("animate-in");
                }

                // Dejar de observar una vez animado
                observer.unobserve(entry.target);
            }
        });
    }, observerOptions);

    // Observar la sección de Proceso y la sección de Planes
    const processGrid = document.querySelector(".process-grid");
    const pricingGrid = document.querySelector(".pricing-grid");

    if (processGrid) scrollObserver.observe(processGrid);
    if (pricingGrid) scrollObserver.observe(pricingGrid);
});



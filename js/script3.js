document.addEventListener("DOMContentLoaded", () => {
    
    // 1. EFECTO PARALLAX 3D EN HERO IMAGE
    const heroCard = document.getElementById("heroImageCard");
    const heroSection = document.querySelector(".fin-hero-section");

    if (heroCard && heroSection) {
        heroSection.addEventListener("mousemove", (e) => {
            const { clientX, clientY } = e;
            const { innerWidth, innerHeight } = window;
            
            const rotateX = ((clientY / innerHeight) - 0.5) * -12;
            const rotateY = ((clientX / innerWidth) - 0.5) * 12;

            heroCard.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg)`;
        });

        heroSection.addEventListener("mouseleave", () => {
            heroCard.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg)";
        });
    }

    // 2. DESPLAZAMIENTO SUAVE
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });

    // 3. LÓGICA DEL SLIDER DE PÓLIZAS
    const slides = document.querySelectorAll(".policy-slide");
    const dots = document.querySelectorAll(".slider-dots .dot");
    const prevBtn = document.getElementById("prevPolicy");
    const nextBtn = document.getElementById("nextPolicy");
    
    let currentSlide = 0;
    let autoSlideTimer = null;

    if (!slides.length) return;

    function updateSlider(index) {
        slides.forEach(slide => slide.classList.remove("active"));
        dots.forEach(dot => dot.classList.remove("active"));

        if (index >= slides.length) currentSlide = 0;
        else if (index < 0) currentSlide = slides.length - 1;
        else currentSlide = index;

        const activeSlide = slides[currentSlide];
        activeSlide.classList.add("active");

        // Cambio de color dinámico según data-bg
        const bgCol = activeSlide.querySelector(".policy-content-col");
        const customColor = activeSlide.getAttribute("data-bg");
        if (bgCol && customColor) {
            bgCol.style.backgroundColor = customColor;
        }

        if (dots[currentSlide]) {
            dots[currentSlide].classList.add("active");
        }
    }

    function resetTimer() {
        if (autoSlideTimer) clearInterval(autoSlideTimer);
        autoSlideTimer = setInterval(() => {
            updateSlider(currentSlide + 1);
        }, 6000);
    }

    if (nextBtn) {
        nextBtn.addEventListener("click", (e) => {
            e.preventDefault();
            updateSlider(currentSlide + 1);
            resetTimer();
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener("click", (e) => {
            e.preventDefault();
            updateSlider(currentSlide - 1);
            resetTimer();
        });
    }

    dots.forEach((dot, idx) => {
        dot.addEventListener("click", (e) => {
            e.preventDefault();
            updateSlider(idx);
            resetTimer();
        });
    });

    // Inicializar slider
    updateSlider(0);
    resetTimer();
});
document.addEventListener('DOMContentLoaded', () => {
    const slides = document.querySelectorAll('.slide');
    const nextBtn = document.querySelector('.next');
    const prevBtn = document.querySelector('.prev');
    
    let currentIndex = 0;
    const totalSlides = slides.length;
    let autoPlayInterval;

    function updateSlider() {
        slides.forEach((slide, index) => {
            slide.classList.toggle('active', index === currentIndex);
        });
    }

    function nextSlide() {
        currentIndex = (currentIndex + 1) % totalSlides;
        updateSlider();
    }

    function prevSlide() {
        currentIndex = (currentIndex - 1 + totalSlides) % totalSlides;
        updateSlider();
    }

    function startAutoPlay() {
        autoPlayInterval = setInterval(nextSlide, 5000); 
    }

    function resetAutoPlay() {
        clearInterval(autoPlayInterval);
        startAutoPlay();
    }

    if (nextBtn) {
        nextBtn.addEventListener('click', () => {
            nextSlide();
            resetAutoPlay();
        });
    }

    if (prevBtn) {
        prevBtn.addEventListener('click', () => {
            prevSlide();
            resetAutoPlay();
        });
    }

    startAutoPlay();
});

/*bajada1*/

document.addEventListener("DOMContentLoaded", function () {
  const sectionMer = document.querySelector(".mer");

  const opciones = {
    root: null,
    threshold: 0.2
  };

  const callback = (entradas, observador) => {
    entradas.forEach(entrada => {
      if (entrada.isIntersecting) {
        entrada.target.classList.add("visible");
        observador.unobserve(entrada.target);
      }
    });
  };

  const observador = new IntersectionObserver(callback, opciones);
  
  if (sectionMer) {
    observador.observe(sectionMer);
  }
});

document.addEventListener("DOMContentLoaded", function () {
  const miSection = document.querySelector("section");

  const opciones = {
    root: null,
    threshold: 0.15
  };

  const callback = (entradas, observador) => {
    entradas.forEach(entrada => {
      if (entrada.isIntersecting) {
        entrada.target.classList.add("visible");
        observador.unobserve(entrada.target);
      }
    });
  };

  const observador = new IntersectionObserver(callback, opciones);
  
  if (miSection) {
    observador.observe(miSection);
  }
});

// Proteger el mapa para que solo se ejecute si existe el div #map en la página
if (document.getElementById('map')) {
    var map = L.map('map').setView([60.613254141171886, 24.81319702471203], 13);

    var osmStandard = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
        subdomains: ['a', 'b', 'c'],
        app: 'ConcesionarioPremiumApp'
    });

    var sateliteStyle = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        maxZoom: 19,
        attribution: 'Tiles &copy; Esri &mdash; Source: Esri, i-cubed, USDA, USGS, AEX, GeoEye, Getmapping, Aerogrid, IGN, IGP, UPR-EGP, and the GIS User Community'
    });

    var topoStyle = L.tileLayer('https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png', {
        maxZoom: 17,
        attribution: 'Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, SRTM | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a>'
    });

    osmStandard.addTo(map);

    var greenIcon = L.icon({
        iconUrl: 'img/benz1.png',
        iconSize:     [50, 50], 
        iconAnchor:   [25, 50], 
        popupAnchor:  [-3, -38] 
    });

    var marker = L.marker([60.613254141171886, 24.81319702471203], {icon: greenIcon});
    marker.bindPopup('<b>DasAuto Finland</b><br><a href=https://www.google.com/maps/place/Auto+Nordic+Finland+Oy/@60.6132268,24.8121604,18.75z/data=!4m10!1m2!2m1!1sfinladia+cars!3m6!1s0x468e0f4035df01e1:0x75f1f9ac4ece9e0e!8m2!3d60.6132561!4d24.8132072!15sCg5maW5sYW5kaWEgY2Fyc5IBCmNhcl9kZWFsZXLgAQA!16s%2Fg%2F11z9q86d2x?entry=ttu&g_ep=EgoyMDI2MDkyMi4wIKXMDSoASAFQAw%3D%3D target="_blank">Ver mas a Detalle</a><br>DasAuto Nordic Finland Oy.');
    var mercedesLayer = L.layerGroup([marker]).addTo(map);
    marker.openPopup();

    var baseMaps = {
        "Estándar (OSM)": osmStandard,
        "Satelite": sateliteStyle,
        "Topográfico": topoStyle
    };

    var overlayMaps = {
        "DasAuto Finland": mercedesLayer
    };

    L.control.layers(baseMaps, overlayMaps).addTo(map);
}

document.addEventListener("DOMContentLoaded", function () {
  const loanSection = document.querySelector(".loan-brands-section");

  const opciones = {
    root: null,
    threshold: 0.15
  };

  const callback = (entradas, observador) => {
    entradas.forEach(entrada => {
      if (entrada.isIntersecting) {
        entrada.target.classList.add("visible");
        observador.unobserve(entrada.target);
      }
    });
  };

  const observador = new IntersectionObserver(callback, opciones);

  if (loanSection) {
    observador.observe(loanSection);
  }
});

/* --- EFECTO DE PROXIMIDAD EN LÍNEAS DE TARJETAS --- */
document.addEventListener("DOMContentLoaded", () => {
    const tarjetas = document.querySelectorAll(".why-card");

    tarjetas.forEach(tarjeta => {
        tarjeta.addEventListener("mousemove", (e) => {
            const rect = tarjeta.getBoundingClientRect();
            
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            tarjeta.style.setProperty("--mouse-x", `${x}px`);
            tarjeta.style.setProperty("--mouse-y", `${y}px`);
        });
    });
});


document.addEventListener("DOMContentLoaded", () => {
    const car = document.querySelector(".car-cursor");
    if (!car) return;

    let mX = window.innerWidth / 2;
    let mY = window.innerHeight / 2;
    let cX = mX, cY = mY;   
    let vX = 0, vY = 0;     
    
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


// =================================================================
// ANIMADOR DE DISTORSIÓN POR ONDAS SÚPER PREMIUM
// =================================================================
document.addEventListener('DOMContentLoaded', () => {
    const displacementMap = document.querySelector('#liquid-flag-wave feDisplacementMap');
    const turbulence = document.querySelector('#liquid-flag-wave feTurbulence');

    if (!displacementMap || !turbulence) return;

    let animationFrameId = null;
    let currentScale = 0;
    let targetScale = 0;
    let baseFreqX = 0.015;
    let baseFreqY = 0.08;
    let time = 0;

    function renderWave() {
        time += 0.06;

        currentScale += (targetScale - currentScale) * 0.12;
        displacementMap.setAttribute('scale', currentScale);

        if (currentScale > 0.5) {
            const dynamicX = baseFreqX + Math.sin(time) * 0.003;
            const dynamicY = baseFreqY + Math.cos(time * 0.8) * 0.01;
            turbulence.setAttribute('baseFrequency', `${dynamicX} ${dynamicY}`);
        }

        animationFrameId = requestAnimationFrame(renderWave);
    }

    renderWave();

    document.querySelectorAll('.product-card').forEach(card => {
        card.addEventListener('mouseenter', () => {
            targetScale = 22;
        });

        card.addEventListener('mouseleave', () => {
            targetScale = 0;
        });
    });
});
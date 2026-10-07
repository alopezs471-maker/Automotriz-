// =================================================================
// MOTOR UNIFICADO: FÍSICAS DE CURSOR, FILTRADO Y CARRITO PREMIUM
// =================================================================
document.addEventListener("DOMContentLoaded", () => {
    console.log("Sistema central de la tienda cargado con éxito.");

    // -------------------------------------------------------------
    // 1. FÍSICAS DEL CURSOR (CARRO LLAVERO)
    // -------------------------------------------------------------
    const car = document.querySelector(".car-cursor");
    if (car) {
        let mX = window.innerWidth / 2;
        let mY = window.innerHeight / 2;
        let cX = mX, cY = mY;
        let vX = 0, vY = 0;

        const elasticidad = 0.12;
        const friccion = 0.82;
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

        const zonasPqrs = document.querySelectorAll("a, button, input, select, textarea, .btn-pqrs-submit, .nav-links a");
        zonasPqrs.forEach(item => {
            item.addEventListener("mouseenter", () => document.body.classList.add("car-hover-active"));
            item.addEventListener("mouseleave", () => document.body.classList.remove("car-hover-active"));
        });
    }

    // -------------------------------------------------------------
    // 2. CONTROL DE DESPLEGABLES (DROPDOWNS DE FILTROS)
    // -------------------------------------------------------------
    const filterGroups = document.querySelectorAll('.filter-dropdown-group');

    filterGroups.forEach(group => {
        const btn = group.querySelector('.filter-top-header');
        const content = group.querySelector('.filter-top-content');

        if (btn && content) {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();

                document.querySelectorAll('.filter-top-content').forEach(other => {
                    if (other !== content) other.classList.remove('show');
                });

                content.classList.toggle('show');
            });

            content.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    });

    document.addEventListener('click', () => {
        document.querySelectorAll('.filter-top-content').forEach(content => {
            content.classList.remove('show');
        });
    });

    // -------------------------------------------------------------
    // 3. LÓGICA DE FILTRADO CORREGIDA
    // -------------------------------------------------------------
    const topCheckboxes = document.querySelectorAll('.filter-top-content input[type="checkbox"]');
    
    topCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', filterCars);
    });

    function filterCars() {
        // Obtener valores seleccionados de cada categoría
        const activeCategories = Array.from(document.querySelectorAll('input[name="categoria"]:checked')).map(cb => cb.value);
        const activePropulsion = Array.from(document.querySelectorAll('input[name="propulsion"]:checked')).map(cb => cb.value);
        const activePrices = Array.from(document.querySelectorAll('input[name="precio"]:checked')).map(cb => cb.value);
        const activeAutonomia = Array.from(document.querySelectorAll('input[name="autonomia"]:checked')).map(cb => cb.value);

        const carCards = document.querySelectorAll('.product-card');

        carCards.forEach(product => {
            // CORREGIDO: Se cambia 'data-categoria' por 'data-category'
            const categoria = product.getAttribute('data-category');
            const propulsion = product.getAttribute('data-propulsion');
            const autonomiaGroup = product.getAttribute('data-autonomia');
            const price = parseInt(product.getAttribute('data-price')) || 0;

            // Determinar rango de precio numérico
            let priceGroup = "gama-entrada";
            if (price > 250000000) {
                priceGroup = "gama-alta";
            } else if (price >= 150000000) {
                priceGroup = "gama-media";
            }

            // Validar si coincide con cada grupo activo
            const matchCat = activeCategories.length === 0 || activeCategories.includes(categoria);
            const matchProp = activePropulsion.length === 0 || activePropulsion.includes(propulsion);
            const matchAuto = activeAutonomia.length === 0 || activeAutonomia.includes(autonomiaGroup);
            const matchPrice = activePrices.length === 0 || activePrices.includes(priceGroup);

            // Mostrar u Ocultar la tarjeta de producto
            if (matchCat && matchProp && matchAuto && matchPrice) {
                product.style.setProperty('display', 'flex', 'important');
            } else {
                product.style.setProperty('display', 'none', 'important');
            }
        });

        // Reanimar elementos visibles al filtrar
        const visibleCards = document.querySelectorAll('.product-card:not([style*="display: none"])');
        visibleCards.forEach((card, index) => {
            card.style.animation = 'none';
            card.offsetHeight; // Forzar reflow
            card.style.animation = `waveAnimation 0.7s cubic-bezier(0.2, 0.8, 0.2, 1) ${index * 0.05}s both`;
        });
    }

    // -------------------------------------------------------------
    // 4. LÓGICA DEL CARRITO LATERAL Y COMPRAS
    // -------------------------------------------------------------
    const openCartBtn = document.getElementById('open-cart-btn');
    const closeCartBtn = document.getElementById('close-cart-btn');
    const cartSidebar = document.getElementById('cart-sidebar');
    const cartOverlay = document.getElementById('cart-overlay');
    const cartContainer = document.getElementById('cart-items-container');
    const cartSubtotalEl = document.getElementById('cart-subtotal');
    const clearCartBtn = document.getElementById('clear-cart-btn');

    function toggleCart(open) {
        if (!cartSidebar || !cartOverlay) return;
        if (open) {
            cartSidebar.classList.add('open');
            cartOverlay.classList.add('open');
            renderCartItems();
        } else {
            cartSidebar.classList.remove('open');
            cartOverlay.classList.remove('open');
        }
    }

    if (openCartBtn) openCartBtn.addEventListener('click', () => toggleCart(true));
    if (closeCartBtn) closeCartBtn.addEventListener('click', () => toggleCart(false));
    if (cartOverlay) cartOverlay.addEventListener('click', () => toggleCart(false));

    // Evento de Añadir al Carrito delegando sobre document
    document.addEventListener('click', (e) => {
        if (e.target && e.target.classList.contains('btn-add-cart')) {
            const card = e.target.closest('.product-card');
            if (!card) return;

            const product = {
                id: card.getAttribute('data-id'),
                name: card.getAttribute('data-name'),
                price: parseInt(card.getAttribute('data-price')),
                img: card.getAttribute('data-img'),
                quantity: 1
            };

            let cart = JSON.parse(localStorage.getItem('premium_cart')) || [];
            const existingIndex = cart.findIndex(item => item.id === product.id);

            if (existingIndex > -1) {
                cart[existingIndex].quantity += 1;
            } else {
                cart.push(product);
            }

            localStorage.setItem('premium_cart', JSON.stringify(cart));
            updateIndexCartBadge();
            toggleCart(true);
        }
    });

    function renderCartItems() {
        if (!cartContainer || !cartSubtotalEl) return;
        let cart = JSON.parse(localStorage.getItem('premium_cart')) || [];
        cartContainer.innerHTML = '';

        if (cart.length === 0) {
            cartContainer.innerHTML = '<p style="text-align: center; color: #707072; margin-top: 40px;">Tu carrito está vacío.</p>';
            cartSubtotalEl.textContent = '$ 0';
            return;
        }

        let total = 0;

        cart.forEach((item, index) => {
            total += item.price * item.quantity;
            const itemEl = document.createElement('div');
            itemEl.style.cssText = 'display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; border-bottom: 1px solid #f0f0f0; padding-bottom: 12px;';
            itemEl.innerHTML = `
                <img src="${item.img}" alt="${item.name}" style="width: 60px; height: 40px; object-fit: contain; border-radius: 4px; background: #f6f6f6; padding: 4px;">
                <div style="flex: 1; margin-left: 12px;">
                    <h4 style="font-size: 0.9rem; margin: 0; color: #171a20;">${item.name}</h4>
                    <span style="font-size: 0.8rem; color: #707072;">$ ${item.price.toLocaleString('es-CO')} x ${item.quantity}</span>
                </div>
                <button onclick="removeCartItem(${index})" style="background: transparent; border: none; color: #e74c3c; cursor: pointer; font-size: 1.1rem; font-weight: bold;">&times;</button>
            `;
            cartContainer.appendChild(itemEl);
        });

        cartSubtotalEl.textContent = `$ ${total.toLocaleString('es-CO')}`;
    }

    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', () => {
            localStorage.removeItem('premium_cart');
            updateIndexCartBadge();
            renderCartItems();
        });
    }

    window.removeCartItem = function(index) {
        let cart = JSON.parse(localStorage.getItem('premium_cart')) || [];
        cart.splice(index, 1);
        localStorage.setItem('premium_cart', JSON.stringify(cart));
        updateIndexCartBadge();
        renderCartItems();
    };

    // -------------------------------------------------------------
    // 5. RENDERIZADO DE ESTRELLAS DE VALORACIÓN
    // -------------------------------------------------------------
    function renderProductRatings() {
        const cards = document.querySelectorAll('.product-card');

        cards.forEach(card => {
            const ratingContainer = card.querySelector('.product-rating');
            if (!ratingContainer) return;

            const ratingVal = parseInt(card.getAttribute('data-rating')) || 0;
            const rating = Math.min(5, Math.max(0, ratingVal));

            let starsHTML = '';
            for (let i = 1; i <= 5; i++) {
                if (i <= rating) {
                    starsHTML += '<span class="star filled">★</span>';
                } else {
                    starsHTML += '<span class="star">★</span>';
                }
            }

            ratingContainer.innerHTML = starsHTML;
        });
    }

    renderProductRatings();
    updateIndexCartBadge();
});

// Actualiza la insignia flotante con el número de ítems
function updateIndexCartBadge() {
    const cartData = localStorage.getItem('premium_cart');
    const cart = cartData ? JSON.parse(cartData) : [];
    const totalItems = cart.reduce((acc, item) => acc + (item.quantity || 1), 0);
    
    const badge = document.getElementById('cart-count-badge');
    if (badge) {
        badge.textContent = totalItems;
    }
}

// Ocultar la pantalla de carga al terminar la carga de recursos
window.addEventListener("load", () => {
    const loader = document.getElementById("loader-wrapper");
    if (loader) {
        loader.classList.add("loader-hidden");
    }
});
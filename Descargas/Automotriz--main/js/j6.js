document.addEventListener("DOMContentLoaded", () => {
    // =================================================================
    // 1. ESTADO PERSISTENTE DEL CARRITO PREMIUM
    // =================================================================
    const placeholderImg = "data:image/svg+xml;utf8,<svg xmlns='http://w3.org' width='100' height='100' viewBox='0 0 24 24' fill='none' stroke='%23ccc' stroke-width='1.5'><rect x='2' y='3' width='20' height='14' rx='2'/><path d='M8 21h8'/><path d='M12 17v4'/></svg>";
    let cart = JSON.parse(localStorage.getItem('premium_cart')) || [];

    // localStorage es la única fuente del carrito: script1.js y conexion-datos.js
    // también lo modifican (al alinear precios con la base de datos o al confirmar
    // un pedido), así que se relee antes de cada operación.
    function leerCarrito() {
        try { return JSON.parse(localStorage.getItem('premium_cart')) || []; } catch (_) { return []; }
    }

    // Referencias de los elementos de la interfaz (DOM)
    const cartSidebar = document.getElementById('cart-sidebar');
    const cartOverlay = document.getElementById('cart-overlay');
    const openCartBtn = document.getElementById('open-cart-btn');
    const closeCartBtn = document.getElementById('close-cart-btn');
    const clearCartBtn = document.getElementById('clear-cart-btn');
    const cartItemsContainer = document.getElementById('cart-items-container');
    const cartCountBadge = document.getElementById('cart-count-badge');
    const cartSubtotal = document.getElementById('cart-subtotal');

    // =================================================================
    // 2. CONTROLADORES DE APERTURA Y CIERRE (ESTADOS FIJOS)
    // =================================================================
    function openCart() {
        if (cartSidebar) cartSidebar.classList.add('open');
        if (cartOverlay) cartOverlay.classList.add('open');
    }

    function closeCart() {
        if (cartSidebar) cartSidebar.classList.remove('open');
        if (cartOverlay) cartOverlay.classList.remove('open');
    }

    if (openCartBtn) {
        openCartBtn.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            openCart(); 
        });
    }

    if (closeCartBtn) closeCartBtn.addEventListener('click', (e) => { e.preventDefault(); closeCart(); });
    if (cartOverlay) cartOverlay.addEventListener('click', closeCart);

    // =================================================================
    // 3. CAPTURA DE COMPRA EN LA VITRINA DE VEHÍCULOS
    // =================================================================
    const productsGrid = document.querySelector('.products-grid');
    if (productsGrid) {
        productsGrid.addEventListener('click', (e) => {
            // Solo se ejecuta si el usuario hace clic exactamente en el botón de Ordenar
            if (e.target && (e.target.classList.contains('btn-add-cart') || e.target.textContent.includes('Ordenar'))) {
                e.preventDefault();
                e.stopPropagation(); // Frena el burbujeo para erradicar parpadeos

                const card = e.target.closest('[data-id]');
                if (!card) return;

                const id = card.getAttribute('data-id');
                const name = card.getAttribute('data-name');
                const price = parseFloat(card.getAttribute('data-price'));
                let img = card.getAttribute('data-img') || placeholderImg;

                cart = leerCarrito();
                const existingItem = cart.find(item => item.id === id);
                if (existingItem) {
                    existingItem.quantity += 1;
                } else {
                    cart.push({ id, name, price, img, quantity: 1 });
                }

                localStorage.setItem('premium_cart', JSON.stringify(cart));
                renderCart();
                openCart(); // Abre la barra fija
            }
        });
    }

    // =================================================================
    // 4. RENDERIZADO REACTIVO DE LAS COMPRAS
    // =================================================================
    function renderCart() {
        if (!cartItemsContainer) return;
        cart = leerCarrito();
        cartItemsContainer.innerHTML = '';
        let total = 0;
        let totalItems = 0;

        if (cart.length === 0) {
            cartItemsContainer.innerHTML = `
                <div style="text-align: center; margin-top: 60px; color: #5c5e62;"> 
                    <p style="font-size: 1rem; font-weight: 500;">No tienes pedidos agregados.</p> 
                    <p style="font-size: 0.8rem; margin-top: 8px;">Presiona 'Ordenar' en un auto para comenzar.</p> 
                </div>`;
            if (cartCountBadge) cartCountBadge.textContent = '0';
            if (cartSubtotal) cartSubtotal.textContent = '\$ 0';
            return;
        }

        cart.forEach(item => {
            total += item.price * item.quantity;
            totalItems += item.quantity;

            const itemRow = document.createElement('div');
            itemRow.style.cssText = 'display: flex; align-items: center; justify-content: space-between; margin-bottom: 24px; border-bottom: 1px solid #efefef; padding-bottom: 16px;';
            
            itemRow.innerHTML = `
                <div style="display: flex; align-items: center; gap: 14px; flex: 1;"> 
                    <div style="width: 65px; height: 65px; background: #f4f4f4; border: 1px solid #e2e2e2; border-radius: 6px; display:flex; align-items:center; justify-content:center; overflow:hidden; padding: 4px;"> 
                        <img src="${item.img}" alt="${item.name}" onerror="this.src='${placeholderImg}'" style="max-width:100%; max-height:100%; object-fit:contain;"> 
                    </div> 
                    <div> 
                        <h4 style="font-size: 0.9rem; margin: 0; font-weight: 600; color: #171a20;">${item.name}</h4> 
                        <p style="font-size: 0.85rem; color: #3e6ae1; margin: 4px 0 0 0; font-weight: 500;">$ ${(item.price * item.quantity).toLocaleString('es-CO')}</p> 
                    </div> 
                </div> 
                <div style="display: flex; align-items: center; gap: 12px;"> 
                    <div style="display: flex; align-items: center; background: #f4f4f4; border-radius: 4px; border: 1px solid #e2e2e2;"> 
                        <button class="btn-qty decrease" data-id="${item.id}" style="background:transparent; border:none; color:#171a20; padding: 4px 8px; cursor:pointer; font-weight:bold;">-</button> 
                        <span style="font-size: 0.85rem; min-width: 15px; text-align:center; font-weight:600; color:#171a20;">${item.quantity}</span> 
                        <button class="btn-qty increase" data-id="${item.id}" style="background:transparent; border:none; color:#171a20; padding: 4px 8px; cursor:pointer; font-weight:bold;">+</button> 
                    </div> 
                    <button class="btn-remove" data-id="${item.id}" style="background: transparent; border: none; color: #ff4a4a; cursor: pointer; font-size: 0.9rem; padding: 4px; display:flex; align-items:center;">✖</button> 
                </div>`;
            cartItemsContainer.appendChild(itemRow);
        });

        // Modifica la burbuja numérica azul en tiempo real
        if (cartCountBadge) cartCountBadge.textContent = totalItems;
        if (cartSubtotal) cartSubtotal.textContent = `$ ${total.toLocaleString('es-CO')}`;
    }

    // Controles internos de la barra lateral (+, -, ✖)
    if (cartItemsContainer) {
        cartItemsContainer.addEventListener('click', (e) => {
            e.stopPropagation();
            const id = e.target.getAttribute('data-id');
            if (!id) return;
            cart = leerCarrito();
            const index = cart.findIndex(item => item.id === id);
            if (index === -1) return;

            if (e.target.classList.contains('increase')) {
                cart[index].quantity += 1;
            } else if (e.target.classList.contains('decrease')) {
                if (cart[index].quantity > 1) cart[index].quantity -= 1;
                else cart.splice(index, 1);
            } else if (e.target.classList.contains('btn-remove')) {
                cart.splice(index, 1);
            }
            localStorage.setItem('premium_cart', JSON.stringify(cart));
            renderCart();
        });
    }

    // Vaciar orden completa
    if (clearCartBtn) {
        clearCartBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            cart = leerCarrito();
            if (cart.length > 0 && confirm('¿Deseas vaciar tu lista de compras?')) {
                cart = [];
                localStorage.setItem('premium_cart', JSON.stringify(cart));
                renderCart();
            }
        });
    }

    // Dibujo inicial al levantar la ventana
    renderCart();

    // Se redibuja si el carrito cambia desde otra pestaña o desde otro script.
    window.addEventListener('storage', (e) => {
        if (e.key === 'premium_cart' || e.key === null) renderCart();
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
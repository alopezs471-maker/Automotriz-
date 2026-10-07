// Variables Globales
let currentSelectedVehicle = 'Sedán Ejecutivo';
let selectedStoreName = 'Das Auto Finlandia (Helsinki)';
let map;
let markers = {};

// Cambio dinámico al presionar cualquiera de los 4 bloques
function selectDriveModel(name, imgSrc, specs, cardElement) {
  // Remover la selección previa de todas las tarjetas
  document.querySelectorAll('.model-card').forEach(card => card.classList.remove('selected'));
  
  // Asignar clase 'selected' al bloque pulsado
  if (cardElement) {
    cardElement.classList.add('selected');
  }

  const previewImg = document.getElementById('preview-img');
  const previewTitle = document.getElementById('preview-title');
  const previewSpecs = document.getElementById('preview-specs');

  // Animación de transición en la imagen de vista previa
  if (previewImg) {
    previewImg.style.opacity = '0.3';
    setTimeout(() => {
      previewImg.src = imgSrc;
      previewImg.style.opacity = '1';
    }, 150);
  }

  if (previewTitle) previewTitle.textContent = name;
  if (previewSpecs) previewSpecs.textContent = specs;
  
  currentSelectedVehicle = name;
}

// Enfocar sede en el mapa
function focusStore(storeKey, lat, lng, cardElement) {
  document.querySelectorAll('.store-card').forEach(card => card.classList.remove('selected'));
  if (cardElement) cardElement.classList.add('selected');

  if (storeKey === 'finland') {
    selectedStoreName = 'Das Auto Finlandia (Helsinki)';
  } else if (storeKey === 'norway') {
    selectedStoreName = 'Das Auto Noruega (Oslo)';
  }

  if (map && markers[storeKey]) {
    map.flyTo([lat, lng], 13, { animate: true, duration: 1.2 });
    markers[storeKey].openPopup();
  }
}

// Envío del Formulario
function handleDriveForm(event) {
  event.preventDefault();
  const name = document.getElementById('fname').value;
  const date = document.getElementById('drive-date').value;
  const time = document.getElementById('drive-time').value;

  alert(`¡Solicitud Confirmada!\n\nGracias ${name}.\nPrueba agendada para: "${currentSelectedVehicle}"\nSede: ${selectedStoreName}\nFecha: ${date} a las ${time}.`);
  event.target.reset();
}

// Inicialización de Leaflet
document.addEventListener('DOMContentLoaded', () => {
  const mapContainer = document.getElementById('leaflet-drive-map');
  
  if (mapContainer && typeof L !== 'undefined') {
    delete L.Icon.Default.prototype._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });

    map = L.map('leaflet-drive-map').setView([60.1699, 24.9384], 6);

    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 19,
      attribution: '&copy; OpenStreetMap'
    }).addTo(map);

    markers.finland = L.marker([60.1699, 24.9384]).addTo(map)
      .bindPopup('<b>Das Auto Finlandia</b><br>Aleksanterinkatu 15, Helsinki');

    markers.norway = L.marker([59.9139, 10.7522]).addTo(map)
      .bindPopup('<b>Das Auto Noruega</b><br>Karl Johans gate 22, Oslo');

    markers.finland.openPopup();

    setTimeout(() => {
      map.invalidateSize();
    }, 300);
  }
});
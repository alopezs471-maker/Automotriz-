-- 0008: ficha técnica de los 32 vehículos del catálogo.
-- Son datos de demostración, editables desde el panel de administración
-- (o con SQL). Se insertan solo si el vehículo aún no tiene ficha, así que
-- se puede volver a ejecutar sin duplicar nada.
BEGIN;

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Toyota','Corolla',2026,'El híbrido más vendido del mundo: silencioso en ciudad, eficiente en carretera y con la confiabilidad Toyota.', 'img/corl.png',
 '{"motor":"1.8 L híbrido (HEV)","potencia":"140 hp combinados","torque":"142 Nm","transmision":"eCVT","consumo":"4,5 L/100 km","airbags":"7","baul":"470 L","garantia":"5 años / 100.000 km"}',1 FROM inventario WHERE sku='corolla';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Mazda','Mazda 3',2026,'Diseño Kodo, acabados premium y una conducción que se siente más costosa de lo que cuesta.','img/mazda3.jpg',
 '{"motor":"2.0 L Skyactiv-G","potencia":"158 hp","torque":"202 Nm","transmision":"Automática 6 velocidades","consumo":"6,2 L/100 km","airbags":"7","baul":"358 L","garantia":"3 años / 100.000 km"}',1 FROM inventario WHERE sku='mazda-3';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Kia','K3',2026,'Sedán compacto con espacio de sobra, pantalla grande y la garantía más larga del segmento.','img/kiak3.webp',
 '{"motor":"1.6 L","potencia":"121 hp","torque":"152 Nm","transmision":"Automática IVT","consumo":"6,0 L/100 km","airbags":"6","baul":"502 L","garantia":"5 años / 100.000 km"}',0 FROM inventario WHERE sku='kia-k3';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Mazda','Mazda 2',2026,'Ágil, económico y con terminados que no se ven en su precio. Ideal para la ciudad.','img/maz2.webp',
 '{"motor":"1.5 L Skyactiv-G","potencia":"110 hp","torque":"144 Nm","transmision":"Automática 6 velocidades","consumo":"5,7 L/100 km","airbags":"6","baul":"280 L","garantia":"3 años / 100.000 km"}',0 FROM inventario WHERE sku='mazda-2';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Kia','Picanto',2026,'El urbano por excelencia: fácil de parquear, bajo consumo y mantenimiento económico.','img/kai.jpg',
 '{"motor":"1.0 L","potencia":"66 hp","torque":"96 Nm","transmision":"Manual 5 velocidades","consumo":"5,0 L/100 km","airbags":"2","baul":"255 L","garantia":"5 años / 100.000 km"}',0 FROM inventario WHERE sku='kia-picanto';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Tesla','Model 3',2026,'Cero gasolina, cero mantenimiento de motor y actualizaciones por aire. La referencia de los eléctricos.','img/TS3.png',
 '{"motor":"Eléctrico trasero","potencia":"208 kW (283 hp)","torque":"420 Nm","aceleracion":"0–100 km/h en 6,1 s","bateria":"60 kWh LFP","autonomia":"513 km (WLTP)","carga_rapida":"Hasta 170 kW","baul":"594 L"}',1 FROM inventario WHERE sku='tesla-model-3';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'BYD','Seagull',2026,'El eléctrico más asequible del mercado: pequeño por fuera, sorprendentemente amplio por dentro.','img/BDY.webp',
 '{"motor":"Eléctrico","potencia":"55 kW (75 hp)","torque":"135 Nm","bateria":"30 kWh","autonomia":"300 km (CLTC)","carga_rapida":"30 min al 80 %","airbags":"4","baul":"232 L"}',1 FROM inventario WHERE sku='byd-seagull';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'MG','MG4 Electric',2026,'Hatchback eléctrico con tracción trasera y un chasis que invita a manejar.','img/mguk.webp',
 '{"motor":"Eléctrico","potencia":"150 kW (204 hp)","torque":"250 Nm","aceleracion":"0–100 km/h en 7,9 s","bateria":"64 kWh","autonomia":"450 km (WLTP)","carga_rapida":"Hasta 135 kW"}',0 FROM inventario WHERE sku='mg4-electric';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Kia','EV2',2026,'El eléctrico urbano de Kia: formato compacto, interior amplio y carga rápida.','img/kiah.webp',
 '{"motor":"Eléctrico","potencia":"150 kW","torque":"250 Nm","bateria":"42 kWh","autonomia":"300 km (WLTP)","carga_rapida":"10–80 % en 30 min","airbags":"6"}',0 FROM inventario WHERE sku='kia-ev2';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Renault','Duster',2026,'La camioneta que aguanta todo: altura al piso, baúl enorme y repuestos económicos.','img/dust.webp',
 '{"motor":"1.6 L","potencia":"115 hp","torque":"156 Nm","transmision":"Manual 5 velocidades","consumo":"7,0 L/100 km","airbags":"4","baul":"472 L","garantia":"3 años / 100.000 km"}',0 FROM inventario WHERE sku='renault-duster';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Toyota','Corolla Cross',2026,'La practicidad de una SUV con el consumo de un híbrido. Tracción integral disponible.','img/cross.jpg',
 '{"motor":"2.0 L híbrido (HEV)","potencia":"196 hp combinados","transmision":"eCVT · tracción AWD","consumo":"5,0 L/100 km","airbags":"7","baul":"440 L","garantia":"5 años / 100.000 km"}',0 FROM inventario WHERE sku='corolla-cross';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Mazda','CX-30',2026,'Crossover con acabados de marca premium, posición de manejo elevada y respuesta precisa.','img/CX.5-s',
 '{"motor":"2.0 L Skyactiv-G","potencia":"158 hp","torque":"202 Nm","transmision":"Automática 6 velocidades","consumo":"6,4 L/100 km","airbags":"7","baul":"430 L","garantia":"3 años / 100.000 km"}',0 FROM inventario WHERE sku='mazda-cx30';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Volkswagen','Taos',2026,'SUV compacta con motor turbo, caja DSG y un interior muy bien terminado.','img/TAO.jpg',
 '{"motor":"1.4 L turbo TSI","potencia":"150 hp","torque":"250 Nm","transmision":"DSG 6 velocidades","consumo":"6,5 L/100 km","airbags":"6","baul":"498 L","garantia":"3 años / 100.000 km"}',0 FROM inventario WHERE sku='vw-taos';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Tesla','Model Y',2026,'El eléctrico familiar más vendido: baúl gigante, techo panorámico y asistencia de conducción.','img/TSY.png',
 '{"motor":"Eléctrico trasero","potencia":"220 kW (299 hp)","torque":"440 Nm","aceleracion":"0–100 km/h en 6,9 s","bateria":"75 kWh","autonomia":"533 km (WLTP)","baul":"854 L (2.041 L abatido)"}',1 FROM inventario WHERE sku='tesla-model-y';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'BYD','Yuan UP',2026,'SUV eléctrica con buen despeje, cámara 360° y batería Blade de alta seguridad.','img/SUV.jpg',
 '{"motor":"Eléctrico","potencia":"130 kW (176 hp)","torque":"290 Nm","bateria":"60,5 kWh","autonomia":"430 km (CLTC)","carga_rapida":"30–80 % en 30 min","airbags":"6"}',0 FROM inventario WHERE sku='byd-yuan-up';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Chery','iCar 03',2026,'SUV eléctrica de estilo aventurero, tracción trasera y carrocería robusta.','img/CHER.webp',
 '{"motor":"Eléctrico","potencia":"135 kW (184 hp)","bateria":"65 kWh","autonomia":"430 km (CLTC)","traccion":"Trasera","airbags":"6","baul":"385 L"}',0 FROM inventario WHERE sku='chery-icar-03';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'MG','S5 EV',2026,'SUV eléctrica con pantalla de 15,6", techo panorámico y carga rápida de serie.','img/MG.png',
 '{"motor":"Eléctrico","potencia":"125 kW (170 hp)","torque":"250 Nm","bateria":"62 kWh","autonomia":"460 km (WLTP)","carga_rapida":"Hasta 120 kW","airbags":"6"}',0 FROM inventario WHERE sku='mg-s5-ev';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'GAC','Aion V / UT',2026,'Eléctrica con mucho espacio interior, asientos reclinables y batería de larga duración.','img/GAC.webp',
 '{"motor":"Eléctrico","potencia":"150 kW (204 hp)","torque":"300 Nm","bateria":"70 kWh","autonomia":"500 km (CLTC)","carga_rapida":"30–80 % en 25 min","airbags":"6"}',0 FROM inventario WHERE sku='gac-aion-v';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Chevrolet','Equinox EV',2026,'SUV eléctrica de tamaño medio con gran autonomía y pantalla de 17,7 pulgadas.','img/EV.avif',
 '{"motor":"Eléctrico","potencia":"213 hp","bateria":"85 kWh","autonomia":"480 km (EPA)","carga_rapida":"Hasta 150 kW","airbags":"6","baul":"714 L"}',0 FROM inventario WHERE sku='chevrolet-equinox';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'BYD','Yuan Plus',2026,'Compacta eléctrica con interior tecnológico, techo panorámico y buena relación precio-equipamiento.','img/bdysuv.webp',
 '{"motor":"Eléctrico","potencia":"150 kW (204 hp)","torque":"310 Nm","bateria":"60 kWh","autonomia":"420 km (WLTP)","carga_rapida":"30–80 % en 30 min","airbags":"6"}',0 FROM inventario WHERE sku='byd-yuan-plus';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Yamaha','MT-09',2026,'Naked de tres cilindros: ligera, torquera y con una electrónica de primera.','img/mt09.jpg',
 '{"motor":"890 cc CP3 · 3 cilindros","potencia":"119 hp","torque":"93 Nm","transmision":"6 velocidades","peso":"193 kg","tanque":"14 L","frenos":"Disco doble con ABS"}',0 FROM inventario WHERE sku='yamaha-mt09';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Kawasaki','Z900',2026,'Deportiva naked con motor de cuatro cilindros y un rugido inconfundible.','img/z900.png',
 '{"motor":"948 cc · 4 cilindros","potencia":"125 hp","torque":"98,6 Nm","transmision":"6 velocidades","peso":"212 kg","tanque":"17 L","frenos":"Disco doble con ABS"}',0 FROM inventario WHERE sku='kawasaki-z900';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'BMW','R 1250 GS',2026,'La trail de referencia: motor bóxer, suspensión electrónica y comodidad para viajar sin fin.','img/r1200.webp',
 '{"motor":"1.254 cc bóxer","potencia":"136 hp","torque":"143 Nm","transmision":"6 velocidades","peso":"249 kg","tanque":"30 L","frenos":"ABS en curva"}',1 FROM inventario WHERE sku='bmw-r1250-gs';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Ducati','Panigale V4',2026,'Superbike de MotoGP para la calle: 216 hp, alerones y una puesta a punto de circuito.','img/duc.png',
 '{"motor":"1.103 cc Desmosedici Stradale V4","potencia":"216 hp","torque":"123 Nm","transmision":"6 velocidades","peso":"195 kg","tanque":"17 L","frenos":"Disco doble 330 mm con ABS"}',0 FROM inventario WHERE sku='ducati-panigale-v4';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'KTM','790 Duke',2026,'La "scalpel": chasis ligero, motor bicilíndrico vivo y diversión garantizada en curvas.','img/duk.png',
 '{"motor":"799 cc bicilíndrico","potencia":"105 hp","torque":"87 Nm","transmision":"6 velocidades","peso":"187 kg","tanque":"14 L","frenos":"Disco doble con ABS en curva"}',0 FROM inventario WHERE sku='ktm-790-duke';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Super Soco','TC Max',2026,'Moto eléctrica urbana: carnet A2, mantenimiento mínimo y costo por kilómetro casi nulo.','img/soco.png',
 '{"motor":"Eléctrico 5 kW","torque":"60 Nm a la rueda","bateria":"3,2 kWh extraíble","autonomia":"100 km","velocidad_maxima":"85 km/h","peso":"98 kg","frenos":"Disco con ABS"}',0 FROM inventario WHERE sku='starker-tc-max';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Zero','SR/F Electric',2026,'Moto eléctrica de altas prestaciones: 110 hp, sin marchas y sin vibraciones.','img/zero.png',
 '{"motor":"Eléctrico","potencia":"82 kW (110 hp)","torque":"190 Nm","bateria":"15,6 kWh","autonomia":"259 km combinada","aceleracion":"0–100 km/h en 3,3 s","peso":"220 kg"}',0 FROM inventario WHERE sku='zero-s-rf';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Honda','CB650R',2026,'Neo Sports Café: cuatro cilindros, sonido adictivo y una postura cómoda para todos los días.','img/CB.htm',
 '{"motor":"649 cc · 4 cilindros","potencia":"95 hp","torque":"63 Nm","transmision":"6 velocidades","peso":"202 kg","tanque":"15,4 L","frenos":"Disco doble con ABS"}',0 FROM inventario WHERE sku='honda-cb650r';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Suzuki','V-Strom 1050',2026,'Trail viajera con motor V-twin, protección aerodinámica y comodidad para largas rutas.','img/suki.png',
 '{"motor":"1.037 cc V-twin","potencia":"106 hp","torque":"100 Nm","transmision":"6 velocidades","peso":"236 kg","tanque":"20 L","frenos":"Disco doble con ABS"}',0 FROM inventario WHERE sku='suzuki-vstrom-1050';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Vespa','Elettrica',2026,'Ícono italiano en versión eléctrica: estilo atemporal, cero ruido y cero gasolina.','img/vespa.webp',
 '{"motor":"Eléctrico","potencia":"4 kW","bateria":"4,2 kWh","autonomia":"100 km","velocidad_maxima":"70 km/h","peso":"130 kg","frenos":"Disco con ABS"}',0 FROM inventario WHERE sku='vespa-elettrica';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'Harley-Davidson','LiveWire',2026,'La Harley eléctrica: 105 hp, aceleración inmediata y el diseño más atrevido de la marca.','img/harley.webp',
 '{"motor":"Eléctrico Revelation","potencia":"78 kW (105 hp)","torque":"116 Nm","bateria":"15,5 kWh","autonomia":"235 km ciudad","aceleracion":"0–100 km/h en 3 s","peso":"249 kg"}',0 FROM inventario WHERE sku='harley-davidson-livewire';

INSERT OR IGNORE INTO inventario_ficha(inventario_id,marca,modelo,anio,descripcion,imagen_url,especificaciones,destacado)
SELECT id,'BMW','S 1000 RR',2026,'La superbike alemana: 210 hp, alerones, electrónica de pista y frenos M de serie.','img/BWMS.webp',
 '{"motor":"999 cc · 4 cilindros","potencia":"210 hp","torque":"113 Nm","transmision":"6 velocidades","peso":"197 kg","tanque":"16,5 L","frenos":"Disco doble 320 mm con ABS en curva"}',0 FROM inventario WHERE sku='bmw-s1000rr';

COMMIT;

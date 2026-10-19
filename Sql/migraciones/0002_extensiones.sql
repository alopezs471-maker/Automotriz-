-- 
-- DasAuto · Migración 0002 · EXTENSIONES (100% ADITIVA)
-- 
-- Regla de esta migración: NO modifica, NO elimina y NO altera ninguna
-- tabla existente (usuarios, pqrs, inventario, promociones, migraciones).
-- Solo crea tablas NUEVAS que se apoyan en las actuales por clave foránea.
-- Si algo sale mal, se pueden borrar estas tablas sin perder un solo dato
-- de lo que ya tienes.
--
-- Compatible con SQLite 3.35+ (el que usa base_datos.py).
-- Se aplica sobre la misma base de datos que usa base_datos.py.
-- 

PRAGMA foreign_keys = ON;

-- 
-- 1. Sedes / sucursales (hoy las tiendas están quemadas en el HTML:
--    "Das Auto Finlandia", "Das Auto Noruega"...)
-- 
CREATE TABLE IF NOT EXISTS sedes (
  id          INTEGER PRIMARY KEY,
  codigo      TEXT NOT NULL UNIQUE,
  nombre      TEXT NOT NULL,
  direccion   TEXT,
  ciudad      TEXT,
  telefono    TEXT,
  latitud     REAL,
  longitud    REAL,
  activa      INTEGER NOT NULL DEFAULT 1 CHECK(activa IN (0,1)),
  creado_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 
-- 2. Citas de taller (Taller.html hoy no guarda nada)
-- 
CREATE TABLE IF NOT EXISTS citas_taller (
  id                 INTEGER PRIMARY KEY,
  radicado           TEXT NOT NULL UNIQUE,
  envio_id           TEXT NOT NULL UNIQUE,
  usuario_id         INTEGER REFERENCES usuarios(id),
  sede_id            INTEGER REFERENCES sedes(id),
  inventario_id      INTEGER REFERENCES inventario(id),
  nombre             TEXT NOT NULL,
  documento          TEXT NOT NULL,
  email              TEXT NOT NULL,
  telefono           TEXT NOT NULL,
  placa              TEXT,
  kilometraje        INTEGER CHECK(kilometraje IS NULL OR kilometraje >= 0),
  servicio           TEXT NOT NULL CHECK(servicio IN
                       ('mantenimiento','diagnostico','frenos','llantas',
                        'bateria','aire_acondicionado','pintura','garantia','otro')),
  descripcion        TEXT,
  fecha_programada   TEXT NOT NULL CHECK(
                     fecha_programada GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'
                     AND CAST(substr(fecha_programada,6,2) AS INTEGER) BETWEEN 1 AND 12
                     AND CAST(substr(fecha_programada,9,2) AS INTEGER) BETWEEN 1 AND 31),
  hora_programada    TEXT NOT NULL CHECK(hora_programada  GLOB '[0-2][0-9]:[0-5][0-9]'),
  estado             TEXT NOT NULL DEFAULT 'solicitada'
                       CHECK(estado IN ('solicitada','confirmada','en_taller',
                                        'finalizada','cancelada','no_show')),
  costo_estimado     INTEGER CHECK(costo_estimado IS NULL OR costo_estimado >= 0),
  acepta_tratamiento INTEGER NOT NULL CHECK(acepta_tratamiento = 1),
  creado_en          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en     TEXT
);
CREATE INDEX IF NOT EXISTS idx_citas_fecha    ON citas_taller(fecha_programada, hora_programada);
CREATE INDEX IF NOT EXISTS idx_citas_estado   ON citas_taller(estado);
CREATE INDEX IF NOT EXISTS idx_citas_sede     ON citas_taller(sede_id);

-- 
-- 3. Pruebas de manejo (Agendar prueba.html hoy no guarda nada)
-- 
CREATE TABLE IF NOT EXISTS pruebas_manejo (
  id                 INTEGER PRIMARY KEY,
  radicado           TEXT NOT NULL UNIQUE,
  envio_id           TEXT NOT NULL UNIQUE,
  usuario_id         INTEGER REFERENCES usuarios(id),
  sede_id            INTEGER REFERENCES sedes(id),
  inventario_id      INTEGER REFERENCES inventario(id),
  nombre             TEXT NOT NULL,
  apellido           TEXT NOT NULL,
  documento          TEXT,
  email              TEXT NOT NULL,
  telefono           TEXT NOT NULL,
  modelo_interes     TEXT NOT NULL,
  fecha_programada   TEXT NOT NULL CHECK(
                     fecha_programada GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'
                     AND CAST(substr(fecha_programada,6,2) AS INTEGER) BETWEEN 1 AND 12
                     AND CAST(substr(fecha_programada,9,2) AS INTEGER) BETWEEN 1 AND 31),
  hora_programada    TEXT NOT NULL CHECK(hora_programada  GLOB '[0-2][0-9]:[0-5][0-9]'),
  estado             TEXT NOT NULL DEFAULT 'solicitada'
                       CHECK(estado IN ('solicitada','confirmada','realizada',
                                        'cancelada','no_show')),
  acepta_tratamiento INTEGER NOT NULL CHECK(acepta_tratamiento = 1),
  creado_en          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  actualizado_en     TEXT
);
CREATE INDEX IF NOT EXISTS idx_pruebas_fecha  ON pruebas_manejo(fecha_programada);
CREATE INDEX IF NOT EXISTS idx_pruebas_estado ON pruebas_manejo(estado);

-- 
-- 4. Mensajes de contacto (Contacto.html hoy no guarda nada)
-- 
CREATE TABLE IF NOT EXISTS contactos (
  id                 INTEGER PRIMARY KEY,
  envio_id           TEXT NOT NULL UNIQUE,
  usuario_id         INTEGER REFERENCES usuarios(id),
  nombre             TEXT NOT NULL,
  email              TEXT NOT NULL,
  telefono           TEXT,
  asunto             TEXT NOT NULL CHECK(asunto IN ('ventas','prueba','taller','financiacion','seguros','otro')),
  mensaje            TEXT NOT NULL,
  estado             TEXT NOT NULL DEFAULT 'nuevo'
                       CHECK(estado IN ('nuevo','en_proceso','cerrado')),
  acepta_tratamiento INTEGER NOT NULL CHECK(acepta_tratamiento = 1),
  creado_en          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_contactos_estado ON contactos(estado);

-- 
-- 5. Simulaciones de financiación (Financiacion.html)
--    Guarda la simulación para saber qué busca cada cliente.
-- 
CREATE TABLE IF NOT EXISTS cotizaciones_financiacion (
  id               INTEGER PRIMARY KEY,
  envio_id         TEXT NOT NULL UNIQUE,
  usuario_id       INTEGER REFERENCES usuarios(id),
  inventario_id    INTEGER REFERENCES inventario(id),
  nombre           TEXT NOT NULL,
  email            TEXT NOT NULL,
  telefono         TEXT,
  precio_vehiculo  INTEGER NOT NULL CHECK(precio_vehiculo >= 0),
  cuota_inicial    INTEGER NOT NULL CHECK(cuota_inicial >= 0),
  plazo_meses      INTEGER NOT NULL CHECK(plazo_meses BETWEEN 6 AND 84),
  tasa_anual       REAL    NOT NULL CHECK(tasa_anual >= 0 AND tasa_anual <= 100),
  cuota_mensual    INTEGER NOT NULL CHECK(cuota_mensual >= 0),
  moneda           TEXT NOT NULL DEFAULT 'COP',
  estado           TEXT NOT NULL DEFAULT 'simulada'
                     CHECK(estado IN ('simulada','enviada','aprobada','rechazada')),
  creado_en        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(cuota_inicial <= precio_vehiculo)
);
CREATE INDEX IF NOT EXISTS idx_fin_estado ON cotizaciones_financiacion(estado);

-- 
-- 6. Cotizaciones de seguro (Seguros.html)
-- 
CREATE TABLE IF NOT EXISTS cotizaciones_seguro (
  id               INTEGER PRIMARY KEY,
  envio_id         TEXT NOT NULL UNIQUE,
  usuario_id       INTEGER REFERENCES usuarios(id),
  inventario_id    INTEGER REFERENCES inventario(id),
  nombre           TEXT NOT NULL,
  email            TEXT NOT NULL,
  telefono         TEXT,
  tipo_cobertura   TEXT NOT NULL CHECK(tipo_cobertura IN ('responsabilidad','basica','estandar','todo_riesgo')),
  anio_vehiculo    INTEGER CHECK(anio_vehiculo IS NULL OR anio_vehiculo BETWEEN 1950 AND 2100),
  valor_asegurado  INTEGER NOT NULL CHECK(valor_asegurado >= 0),
  prima_mensual    INTEGER CHECK(prima_mensual IS NULL OR prima_mensual >= 0),
  moneda           TEXT NOT NULL DEFAULT 'COP',
  estado           TEXT NOT NULL DEFAULT 'simulada'
                     CHECK(estado IN ('simulada','enviada','emitida','rechazada')),
  creado_en        TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 
-- 7. Pedidos (ordenar.html + carrito que hoy vive solo en localStorage)
-- 
CREATE TABLE IF NOT EXISTS pedidos (
  id           INTEGER PRIMARY KEY,
  radicado     TEXT NOT NULL UNIQUE,
  envio_id     TEXT NOT NULL UNIQUE,
  usuario_id   INTEGER REFERENCES usuarios(id),
  nombre       TEXT NOT NULL,
  documento    TEXT NOT NULL,
  email        TEXT NOT NULL,
  telefono     TEXT NOT NULL,
  subtotal     INTEGER NOT NULL CHECK(subtotal >= 0),
  descuento    INTEGER NOT NULL DEFAULT 0 CHECK(descuento >= 0),
  total        INTEGER NOT NULL CHECK(total >= 0),
  moneda       TEXT NOT NULL DEFAULT 'COP',
  estado       TEXT NOT NULL DEFAULT 'pendiente'
                 CHECK(estado IN ('pendiente','confirmado','facturado','cancelado')),
  notas        TEXT,
  creado_en    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pedidos_estado ON pedidos(estado);

CREATE TABLE IF NOT EXISTS pedidos_items (
  id              INTEGER PRIMARY KEY,
  pedido_id       INTEGER NOT NULL REFERENCES pedidos(id) ON DELETE CASCADE,
  inventario_id   INTEGER NOT NULL REFERENCES inventario(id),
  sku             TEXT NOT NULL,
  nombre          TEXT NOT NULL,
  cantidad        INTEGER NOT NULL CHECK(cantidad > 0),
  precio_unitario INTEGER NOT NULL CHECK(precio_unitario >= 0),
  UNIQUE(pedido_id, inventario_id)
);

-- 
-- 8. Ficha extendida del vehículo (marca, año, imagen, specs...)
--    Tabla APARTE a propósito: así no se toca `inventario`.
-- 
CREATE TABLE IF NOT EXISTS inventario_ficha (
  inventario_id   INTEGER NOT NULL UNIQUE REFERENCES inventario(id) ON DELETE CASCADE,
  marca           TEXT,
  modelo          TEXT,
  anio            INTEGER CHECK(anio IS NULL OR anio BETWEEN 1950 AND 2100),
  descripcion     TEXT,
  imagen_url      TEXT,
  especificaciones TEXT,          -- JSON en texto (SQLite no tiene tipo JSON nativo obligatorio)
  kilometraje     INTEGER CHECK(kilometraje IS NULL OR kilometraje >= 0),
  destacado       INTEGER NOT NULL DEFAULT 0 CHECK(destacado IN (0,1)),
  activo          INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
  actualizado_en  TEXT
);

-- 
-- 9. Kardex / movimientos de inventario
--    (hoy `existencias` se pisa con gestionar.py y no queda rastro)
-- 
CREATE TABLE IF NOT EXISTS inventario_movimientos (
  id             INTEGER PRIMARY KEY,
  inventario_id  INTEGER NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
  tipo           TEXT NOT NULL CHECK(tipo IN ('entrada','salida','ajuste')),
  cantidad       INTEGER NOT NULL,          -- negativo = sale, positivo = entra
  saldo_final    INTEGER CHECK(saldo_final IS NULL OR saldo_final >= 0),
  motivo         TEXT,
  referencia     TEXT,                      -- p.ej. radicado del pedido
  creado_en      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_movimientos_inv ON inventario_movimientos(inventario_id, creado_en);

-- 
-- 10. Histórico de promociones
--     `promociones.inventario_id` es UNIQUE: solo 1 promo viva por vehículo.
--     Esta tabla guarda las anteriores sin tocar la original.
-- 
CREATE TABLE IF NOT EXISTS promociones_historico (
  id                  INTEGER PRIMARY KEY,
  inventario_id       INTEGER NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
  titulo              TEXT NOT NULL,
  beneficio           TEXT,
  precio_promocional  INTEGER NOT NULL CHECK(precio_promocional >= 0),
  fecha_inicio        TEXT,
  fecha_fin           TEXT,
  cerrada_en          TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- 
-- 11. Trazabilidad de PQRS (quién cambió el estado y cuándo)
-- 
CREATE TABLE IF NOT EXISTS pqrs_eventos (
  id          INTEGER PRIMARY KEY,
  pqrs_id     INTEGER NOT NULL REFERENCES pqrs(id) ON DELETE CASCADE,
  estado      TEXT NOT NULL CHECK(estado IN ('radicada','en_proceso','respondida','cerrada')),
  nota        TEXT,
  responsable TEXT,
  creado_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_pqrs_eventos ON pqrs_eventos(pqrs_id, creado_en);

-- 
-- 12. Auditoría general (opcional pero barata)
-- 
CREATE TABLE IF NOT EXISTS auditoria (
  id          INTEGER PRIMARY KEY,
  tabla       TEXT NOT NULL,
  registro_id INTEGER,
  accion      TEXT NOT NULL CHECK(accion IN ('insert','update','delete','lectura_sensible')),
  detalle     TEXT,
  origen      TEXT,                          -- 'web', 'gestionar.py', 'sql'
  creado_en   TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabla ON auditoria(tabla, creado_en);

-- 
-- 13. Semilla mínima de sedes (idempotente)
-- 
INSERT OR IGNORE INTO sedes(codigo, nombre, direccion, ciudad) VALUES
  ('principal', 'Sede Principal',        'Por definir', 'Bogotá D.C.'),
  ('norte',     'Das Auto Sede Norte',   'Por definir', 'Bogotá D.C.'),
  ('taller',    'Taller de Servicio',    'Por definir', 'Bogotá D.C.');

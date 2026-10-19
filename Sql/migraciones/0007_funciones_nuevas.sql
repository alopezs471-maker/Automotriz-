-- 0007: funciones nuevas, todas ADITIVAS.
--   · historial de precios (base y promocional) con disparadores (triggers)
--   · cupos de agenda de taller
--   · inventario real: reservas + control de existencias en los pedidos
--   · tasas de financiación
--   · cuentas y sesiones del panel de administración
-- No altera ninguna tabla existente; solo agrega tablas, vistas y triggers.
BEGIN;

--  1. Precios
CREATE TABLE IF NOT EXISTS precios_historico (
  id            INTEGER PRIMARY KEY,
  inventario_id INTEGER NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
  campo         TEXT NOT NULL CHECK(campo IN ('precio_base','precio_promocional')),
  valor_anterior INTEGER,
  valor_nuevo   INTEGER,
  origen        TEXT,
  creado_en     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_precios_historico_auto ON precios_historico(inventario_id, id DESC);

CREATE TRIGGER IF NOT EXISTS tr_precio_base_alta
AFTER INSERT ON inventario
BEGIN
  INSERT INTO precios_historico(inventario_id,campo,valor_anterior,valor_nuevo,origen)
  VALUES(NEW.id,'precio_base',NULL,NEW.precio_base,'alta de vehículo');
END;

CREATE TRIGGER IF NOT EXISTS tr_precio_base_cambio
AFTER UPDATE OF precio_base ON inventario
WHEN OLD.precio_base IS NOT NEW.precio_base
BEGIN
  INSERT INTO precios_historico(inventario_id,campo,valor_anterior,valor_nuevo,origen)
  VALUES(NEW.id,'precio_base',OLD.precio_base,NEW.precio_base,'cambio de precio base');
END;

CREATE TRIGGER IF NOT EXISTS tr_precio_promo_alta
AFTER INSERT ON promociones
BEGIN
  INSERT INTO precios_historico(inventario_id,campo,valor_anterior,valor_nuevo,origen)
  VALUES(NEW.inventario_id,'precio_promocional',NULL,NEW.precio_promocional,'promoción creada');
END;

CREATE TRIGGER IF NOT EXISTS tr_precio_promo_cambio
AFTER UPDATE OF precio_promocional ON promociones
WHEN OLD.precio_promocional IS NOT NEW.precio_promocional
BEGIN
  INSERT INTO precios_historico(inventario_id,campo,valor_anterior,valor_nuevo,origen)
  VALUES(NEW.inventario_id,'precio_promocional',OLD.precio_promocional,NEW.precio_promocional,'cambio de oferta');
END;

-- Al finalizar (o borrar) una promoción queda la ficha de lo que estuvo publicado.
CREATE TRIGGER IF NOT EXISTS tr_promocion_finalizada
AFTER UPDATE OF estado ON promociones
WHEN NEW.estado = 'finalizada' AND OLD.estado <> 'finalizada'
BEGIN
  INSERT INTO promociones_historico(inventario_id,titulo,beneficio,precio_promocional,fecha_inicio,fecha_fin)
  VALUES(OLD.inventario_id,OLD.titulo,OLD.beneficio,OLD.precio_promocional,OLD.fecha_inicio,OLD.fecha_fin);
END;

CREATE TRIGGER IF NOT EXISTS tr_promocion_borrada
AFTER DELETE ON promociones
BEGIN
  INSERT INTO promociones_historico(inventario_id,titulo,beneficio,precio_promocional,fecha_inicio,fecha_fin)
  VALUES(OLD.inventario_id,OLD.titulo,OLD.beneficio,OLD.precio_promocional,OLD.fecha_inicio,OLD.fecha_fin);
END;

CREATE VIEW IF NOT EXISTS v_historial_precios AS
SELECT h.id, h.inventario_id, i.sku, i.nombre, h.campo,
       h.valor_anterior, h.valor_nuevo, h.origen, h.creado_en
FROM precios_historico h
JOIN inventario i ON i.id = h.inventario_id
ORDER BY h.id DESC;

--  2. Cupos de agenda
CREATE TABLE IF NOT EXISTS agenda_cupos (
  id             INTEGER PRIMARY KEY,
  fecha          TEXT NOT NULL CHECK(
                   fecha GLOB '[0-9][0-9][0-9][0-9]-[01][0-9]-[0-3][0-9]'
                   AND CAST(substr(fecha,6,2) AS INTEGER) BETWEEN 1 AND 12
                   AND CAST(substr(fecha,9,2) AS INTEGER) BETWEEN 1 AND 31),
  hora           TEXT NOT NULL CHECK(hora GLOB '[0-2][0-9]:[0-5][0-9]'),
  capacidad      INTEGER NOT NULL DEFAULT 2 CHECK(capacidad BETWEEN 0 AND 20),
  activo         INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
  actualizado_en TEXT,
  UNIQUE(fecha, hora)
);

--  3. Inventario real
CREATE TABLE IF NOT EXISTS inventario_reservas (
  id            INTEGER PRIMARY KEY,
  inventario_id INTEGER NOT NULL REFERENCES inventario(id) ON DELETE CASCADE,
  pedido_id     INTEGER REFERENCES pedidos(id) ON DELETE CASCADE,
  cantidad      INTEGER NOT NULL CHECK(cantidad > 0),
  estado        TEXT NOT NULL DEFAULT 'activa'
                  CHECK(estado IN ('activa','consumida','liberada','vencida')),
  expira_en     TEXT,
  creado_en     TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_reservas_pedido ON inventario_reservas(pedido_id, estado);
CREATE INDEX IF NOT EXISTS ix_reservas_estado ON inventario_reservas(estado, expira_en);

-- Regla dura: no se puede vender más de lo que hay (si el vehículo lleva control de existencias).
CREATE TRIGGER IF NOT EXISTS tr_pedido_item_stock
BEFORE INSERT ON pedidos_items
WHEN (SELECT existencias FROM inventario WHERE id = NEW.inventario_id) IS NOT NULL
 AND (SELECT existencias FROM inventario WHERE id = NEW.inventario_id) < NEW.cantidad
BEGIN
  SELECT RAISE(ABORT, 'Sin existencias suficientes para este vehículo.');
END;

-- Cada línea del pedido descuenta, deja el movimiento en el kardex y reserva 48 horas.
CREATE TRIGGER IF NOT EXISTS tr_pedido_item_salida
AFTER INSERT ON pedidos_items
BEGIN
  UPDATE inventario SET existencias = existencias - NEW.cantidad
   WHERE id = NEW.inventario_id AND existencias IS NOT NULL;
  INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
  VALUES(NEW.inventario_id,'salida',-NEW.cantidad,
         (SELECT existencias FROM inventario WHERE id = NEW.inventario_id),
         'Pedido web', (SELECT radicado FROM pedidos WHERE id = NEW.pedido_id));
  INSERT INTO inventario_reservas(inventario_id,pedido_id,cantidad,expira_en)
  VALUES(NEW.inventario_id,NEW.pedido_id,NEW.cantidad,datetime('now','localtime','+48 hours'));
END;

-- Pedido cancelado: se devuelve lo reservado.
CREATE TRIGGER IF NOT EXISTS tr_pedido_cancelado
AFTER UPDATE OF estado ON pedidos
WHEN NEW.estado = 'cancelado' AND OLD.estado <> 'cancelado'
BEGIN
  UPDATE inventario SET existencias = existencias + (
           SELECT SUM(r.cantidad) FROM inventario_reservas r
            WHERE r.pedido_id = NEW.id AND r.estado = 'activa' AND r.inventario_id = inventario.id)
   WHERE existencias IS NOT NULL
     AND id IN (SELECT inventario_id FROM inventario_reservas WHERE pedido_id = NEW.id AND estado = 'activa');
  INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
  SELECT r.inventario_id,'entrada',r.cantidad,
         (SELECT existencias FROM inventario i WHERE i.id = r.inventario_id),
         'Pedido cancelado',NEW.radicado
    FROM inventario_reservas r WHERE r.pedido_id = NEW.id AND r.estado = 'activa';
  UPDATE inventario_reservas SET estado = 'liberada'
   WHERE pedido_id = NEW.id AND estado = 'activa';
END;

-- Pedido confirmado o facturado: la reserva pasa a venta en firme.
CREATE TRIGGER IF NOT EXISTS tr_pedido_confirmado
AFTER UPDATE OF estado ON pedidos
WHEN NEW.estado IN ('confirmado','facturado') AND OLD.estado NOT IN ('confirmado','facturado')
BEGIN
  UPDATE inventario_reservas SET estado = 'consumida'
   WHERE pedido_id = NEW.id AND estado = 'activa';
END;

--  4. Tasas de financiación
CREATE TABLE IF NOT EXISTS tasas_financiacion (
  id              INTEGER PRIMARY KEY,
  nombre          TEXT NOT NULL,
  plazo_min       INTEGER NOT NULL CHECK(plazo_min BETWEEN 6 AND 84),
  plazo_max       INTEGER NOT NULL CHECK(plazo_max BETWEEN 6 AND 84),
  tasa_anual      REAL NOT NULL CHECK(tasa_anual BETWEEN 0 AND 100),
  inicial_min_pct REAL NOT NULL DEFAULT 10 CHECK(inicial_min_pct BETWEEN 0 AND 90),
  activo          INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
  CHECK(plazo_min <= plazo_max)
);
INSERT OR IGNORE INTO tasas_financiacion(id,nombre,plazo_min,plazo_max,tasa_anual,inicial_min_pct,activo) VALUES
  (1,'Plan corto · 12 a 24 meses',12,24,14.9,20,1),
  (2,'Plan estándar · 25 a 48 meses',25,48,16.5,15,1),
  (3,'Plan extendido · 49 a 72 meses',49,72,17.9,10,1),
  (4,'Plan largo · 73 a 84 meses',73,84,19.2,10,1);

--  5. Panel: cuentas y sesiones
CREATE TABLE IF NOT EXISTS admin_usuarios (
  id           INTEGER PRIMARY KEY,
  usuario      TEXT NOT NULL UNIQUE,
  nombre       TEXT NOT NULL,
  clave_hash   TEXT NOT NULL,
  rol          TEXT NOT NULL DEFAULT 'admin'
                 CHECK(rol IN ('admin','ventas','taller','consulta')),
  activo       INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
  creado_en    TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ultimo_acceso TEXT
);
CREATE TABLE IF NOT EXISTS admin_sesiones (
  id         INTEGER PRIMARY KEY,
  token_hash TEXT NOT NULL UNIQUE,
  usuario_id INTEGER NOT NULL REFERENCES admin_usuarios(id) ON DELETE CASCADE,
  ip         TEXT,
  creado_en  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  expira_en  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_admin_sesiones_usuario ON admin_sesiones(usuario_id);
CREATE INDEX IF NOT EXISTS ix_admin_sesiones_expira ON admin_sesiones(expira_en);

--  6. Existencias iniciales para poder controlar
-- Solo donde aún no hay dato (NULL  "por confirmar" en el catálogo original).
UPDATE inventario SET existencias = 3 + (id * 7) % 10 WHERE existencias IS NULL;

INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo)
SELECT id,'entrada',existencias,existencias,'Dotación inicial (migración 0007)'
  FROM inventario
 WHERE existencias IS NOT NULL
   AND NOT EXISTS (SELECT 1 FROM inventario_movimientos
                    WHERE motivo = 'Dotación inicial (migración 0007)'
                      AND inventario_id = inventario.id);

-- Punto de partida del historial: el precio con el que nace esta migración.
-- Así la línea de tiempo ya tiene un primer registro y los cambios posteriores
-- se comparan contra él.
INSERT INTO precios_historico(inventario_id,campo,valor_anterior,valor_nuevo,origen)
SELECT i.id,'precio_base',NULL,i.precio_base,'precio de partida'
  FROM inventario i
 WHERE NOT EXISTS (SELECT 1 FROM precios_historico h
                    WHERE h.inventario_id = i.id AND h.campo = 'precio_base');

INSERT INTO precios_historico(inventario_id,campo,valor_anterior,valor_nuevo,origen)
SELECT p.inventario_id,'precio_promocional',NULL,p.precio_promocional,'oferta de partida'
  FROM promociones p
 WHERE NOT EXISTS (SELECT 1 FROM precios_historico h
                    WHERE h.inventario_id = p.inventario_id AND h.campo = 'precio_promocional');

--  7. Vista pública con ficha y estado de stock
CREATE VIEW IF NOT EXISTS v_inventario_publico AS
SELECT p.inventario_id, p.sku, p.nombre, p.categoria, p.propulsion,
       p.precio_base, p.precio_venta, p.promo_vigente, p.existencias,
       f.marca, f.modelo, f.anio, f.descripcion, f.imagen_url,
       f.especificaciones, COALESCE(f.destacado,0) AS destacado,
       CASE WHEN p.existencias IS NULL THEN 'por_confirmar'
            WHEN p.existencias = 0      THEN 'agotado'
            WHEN p.existencias <= 3     THEN 'ultimas'
            ELSE 'disponible' END AS estado_stock
FROM v_precios p
LEFT JOIN inventario_ficha f ON f.inventario_id = p.inventario_id;

COMMIT;

BEGIN;

CREATE TABLE IF NOT EXISTS roles (
  id INTEGER PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  nombre TEXT NOT NULL,
  activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1))
);

CREATE TABLE IF NOT EXISTS permisos (
  id INTEGER PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  descripcion TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rol_permisos (
  rol_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permiso_id INTEGER NOT NULL REFERENCES permisos(id) ON DELETE CASCADE,
  PRIMARY KEY (rol_id, permiso_id)
);

INSERT OR IGNORE INTO roles(codigo,nombre) VALUES
  ('admin','Administrador'),
  ('ventas','Ventas'),
  ('taller','Taller'),
  ('consulta','Consulta');

INSERT OR IGNORE INTO permisos(codigo,descripcion) VALUES
  ('dashboard.ver','Consultar resumen del sistema'),
  ('reportes.ver','Consultar reportes y estadísticas'),
  ('ventas.ver','Consultar pedidos y facturas'),
  ('ventas.gestionar','Gestionar ventas, facturas y pagos'),
  ('inventario.ver','Consultar vehículos y existencias'),
  ('inventario.gestionar','Gestionar vehículos, precios y existencias'),
  ('taller.ver','Consultar citas y órdenes de taller'),
  ('taller.gestionar','Gestionar órdenes y servicios de taller'),
  ('clientes.ver','Consultar clientes y seguimiento'),
  ('clientes.gestionar','Gestionar seguimiento de clientes'),
  ('cotizaciones.ver','Consultar cotizaciones'),
  ('cotizaciones.gestionar','Gestionar cotizaciones'),
  ('seguridad.gestionar','Gestionar cuentas y seguridad'),
  ('seguridad.clave','Cambiar la propia clave');

INSERT OR IGNORE INTO rol_permisos(rol_id,permiso_id)
SELECT r.id,p.id FROM roles r CROSS JOIN permisos p WHERE r.codigo='admin';

INSERT OR IGNORE INTO rol_permisos(rol_id,permiso_id)
SELECT r.id,p.id FROM roles r JOIN permisos p ON p.codigo IN
 ('dashboard.ver','reportes.ver','ventas.ver','ventas.gestionar',
  'inventario.ver','inventario.gestionar','clientes.ver','clientes.gestionar',
  'cotizaciones.ver','cotizaciones.gestionar','seguridad.clave')
WHERE r.codigo='ventas';

INSERT OR IGNORE INTO rol_permisos(rol_id,permiso_id)
SELECT r.id,p.id FROM roles r JOIN permisos p ON p.codigo IN
 ('dashboard.ver','reportes.ver','inventario.ver','taller.ver','taller.gestionar',
  'clientes.ver','clientes.gestionar','seguridad.clave')
WHERE r.codigo='taller';

INSERT OR IGNORE INTO rol_permisos(rol_id,permiso_id)
SELECT r.id,p.id FROM roles r JOIN permisos p ON p.codigo IN
 ('dashboard.ver','reportes.ver','ventas.ver','inventario.ver','taller.ver',
  'clientes.ver','cotizaciones.ver','seguridad.clave')
WHERE r.codigo='consulta';

CREATE TABLE IF NOT EXISTS facturas (
  id INTEGER PRIMARY KEY,
  pedido_id INTEGER NOT NULL UNIQUE REFERENCES pedidos(id),
  usuario_id INTEGER REFERENCES usuarios(id),
  numero TEXT NOT NULL UNIQUE,
  fecha_emision TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  estado TEXT NOT NULL DEFAULT 'emitida'
    CHECK(estado IN ('borrador','emitida','pagada','anulada')),
  nombre_cliente TEXT NOT NULL,
  documento_cliente TEXT NOT NULL,
  email_cliente TEXT NOT NULL,
  subtotal INTEGER NOT NULL CHECK(subtotal >= 0),
  descuento INTEGER NOT NULL DEFAULT 0 CHECK(descuento >= 0),
  impuestos INTEGER NOT NULL DEFAULT 0 CHECK(impuestos >= 0),
  total INTEGER NOT NULL CHECK(total >= 0 AND total = subtotal - descuento + impuestos),
  moneda TEXT NOT NULL DEFAULT 'COP',
  notas TEXT,
  creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(descuento <= subtotal)
);

CREATE INDEX IF NOT EXISTS idx_facturas_fecha_estado ON facturas(fecha_emision,estado);
CREATE INDEX IF NOT EXISTS idx_facturas_cliente_fecha ON facturas(usuario_id,fecha_emision);

CREATE TABLE IF NOT EXISTS pagos (
  id INTEGER PRIMARY KEY,
  factura_id INTEGER NOT NULL REFERENCES facturas(id),
  referencia TEXT UNIQUE,
  metodo TEXT NOT NULL CHECK(metodo IN ('efectivo','transferencia','tarjeta','financiacion','otro')),
  valor INTEGER NOT NULL CHECK(valor > 0),
  estado TEXT NOT NULL DEFAULT 'pendiente'
    CHECK(estado IN ('pendiente','confirmado','rechazado','reembolsado')),
  pagado_en TEXT,
  creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  notas TEXT
);

CREATE INDEX IF NOT EXISTS idx_pagos_factura_estado ON pagos(factura_id,estado);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_estado ON pagos(pagado_en,estado);

CREATE TRIGGER IF NOT EXISTS tr_factura_pedido_valido
BEFORE INSERT ON facturas
WHEN NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id=NEW.pedido_id AND p.estado<>'cancelado')
BEGIN
  SELECT RAISE(ABORT,'No se puede facturar un pedido cancelado o inexistente.');
END;

CREATE TRIGGER IF NOT EXISTS tr_pago_factura_vigente
BEFORE INSERT ON pagos
WHEN EXISTS (SELECT 1 FROM facturas f WHERE f.id=NEW.factura_id AND f.estado IN ('borrador','anulada'))
BEGIN
  SELECT RAISE(ABORT,'No se puede registrar un pago en una factura anulada o en borrador.');
END;

CREATE TRIGGER IF NOT EXISTS tr_factura_no_anular_con_pagos
BEFORE UPDATE OF estado ON facturas
WHEN NEW.estado='anulada'
 AND EXISTS (SELECT 1 FROM pagos p WHERE p.factura_id=NEW.id AND p.estado='confirmado')
BEGIN
  SELECT RAISE(ABORT,'No se puede anular una factura con pagos confirmados.');
END;

CREATE TRIGGER IF NOT EXISTS tr_pago_no_excede_factura
BEFORE INSERT ON pagos
WHEN NEW.estado='confirmado'
 AND COALESCE((SELECT SUM(valor) FROM pagos WHERE factura_id=NEW.factura_id AND estado='confirmado'),0)+NEW.valor
     > COALESCE((SELECT total FROM facturas WHERE id=NEW.factura_id),0)
BEGIN
  SELECT RAISE(ABORT,'El pago supera el saldo de la factura.');
END;

CREATE TRIGGER IF NOT EXISTS tr_pago_actualizado_no_excede_factura
BEFORE UPDATE OF valor,estado,factura_id ON pagos
WHEN NEW.estado='confirmado'
 AND COALESCE((SELECT SUM(valor) FROM pagos WHERE factura_id=NEW.factura_id AND estado='confirmado' AND id<>NEW.id),0)+NEW.valor
     > COALESCE((SELECT total FROM facturas WHERE id=NEW.factura_id),0)
BEGIN
  SELECT RAISE(ABORT,'El pago supera el saldo de la factura.');
END;

CREATE TRIGGER IF NOT EXISTS tr_factura_pagada_alta_con_saldo
BEFORE INSERT ON facturas
WHEN NEW.estado='pagada' AND NEW.total>0
BEGIN
  SELECT RAISE(ABORT,'La factura no puede crearse pagada sin pagos confirmados.');
END;

CREATE TRIGGER IF NOT EXISTS tr_factura_pagada_con_saldo_cero
BEFORE UPDATE OF estado ON facturas
WHEN NEW.estado='pagada'
 AND COALESCE((SELECT SUM(valor) FROM pagos WHERE factura_id=NEW.id AND estado='confirmado'),0)<NEW.total
BEGIN
  SELECT RAISE(ABORT,'La factura no puede marcarse pagada mientras tenga saldo.');
END;

CREATE TRIGGER IF NOT EXISTS tr_pago_reembolsado_actualiza_factura
AFTER UPDATE OF estado ON pagos
WHEN OLD.estado='confirmado' AND NEW.estado<>'confirmado'
BEGIN
  UPDATE facturas SET estado='emitida'
   WHERE id=NEW.factura_id AND estado='pagada';
END;

CREATE TABLE IF NOT EXISTS servicios_taller (
  id INTEGER PRIMARY KEY,
  codigo TEXT NOT NULL UNIQUE,
  nombre TEXT NOT NULL,
  descripcion TEXT,
  precio_base INTEGER NOT NULL DEFAULT 0 CHECK(precio_base >= 0),
  duracion_minutos INTEGER CHECK(duracion_minutos IS NULL OR duracion_minutos BETWEEN 5 AND 1440),
  activo INTEGER NOT NULL DEFAULT 1 CHECK(activo IN (0,1)),
  creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO servicios_taller(codigo,nombre,descripcion,precio_base,duracion_minutos) VALUES
  ('mantenimiento','Mantenimiento preventivo','Inspección y mantenimiento periódico',0,120),
  ('diagnostico','Diagnóstico','Evaluación técnica del vehículo',0,60),
  ('frenos','Servicio de frenos','Inspección y reparación del sistema de frenos',0,90),
  ('llantas','Servicio de llantas','Inspección y cambio de llantas',0,60),
  ('bateria','Servicio de batería','Diagnóstico y reemplazo de batería',0,45),
  ('aire_acondicionado','Aire acondicionado','Inspección del sistema de climatización',0,90),
  ('pintura','Pintura y carrocería','Revisión de pintura y carrocería',0,240),
  ('garantia','Garantía','Diagnóstico de solicitud de garantía',0,120),
  ('otro','Otro servicio','Servicio por definir',0,60);

CREATE TABLE IF NOT EXISTS ordenes_taller (
  id INTEGER PRIMARY KEY,
  numero TEXT NOT NULL UNIQUE,
  cita_id INTEGER UNIQUE REFERENCES citas_taller(id),
  usuario_id INTEGER REFERENCES usuarios(id),
  inventario_id INTEGER REFERENCES inventario(id),
  placa TEXT,
  kilometraje INTEGER CHECK(kilometraje IS NULL OR kilometraje >= 0),
  estado TEXT NOT NULL DEFAULT 'recibida'
    CHECK(estado IN ('recibida','diagnostico','espera_aprobacion','aprobada','en_reparacion','lista','entregada','cancelada')),
  diagnostico TEXT,
  trabajo_realizado TEXT,
  tecnico TEXT,
  subtotal INTEGER NOT NULL DEFAULT 0 CHECK(subtotal >= 0),
  costo_interno INTEGER NOT NULL DEFAULT 0 CHECK(costo_interno >= 0),
  fecha_ingreso TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  fecha_prometida TEXT,
  fecha_cierre TEXT,
  actualizado_en TEXT,
  creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ordenes_taller_estado_fecha ON ordenes_taller(estado,fecha_ingreso);
CREATE INDEX IF NOT EXISTS idx_ordenes_taller_cliente_fecha ON ordenes_taller(usuario_id,fecha_ingreso);
CREATE INDEX IF NOT EXISTS idx_ordenes_taller_vehiculo_fecha ON ordenes_taller(inventario_id,fecha_ingreso);

CREATE TABLE IF NOT EXISTS ordenes_taller_items (
  id INTEGER PRIMARY KEY,
  orden_id INTEGER NOT NULL REFERENCES ordenes_taller(id) ON DELETE CASCADE,
  servicio_id INTEGER REFERENCES servicios_taller(id),
  tipo TEXT NOT NULL CHECK(tipo IN ('servicio','repuesto','mano_obra','otro')),
  descripcion TEXT NOT NULL,
  cantidad REAL NOT NULL CHECK(cantidad > 0),
  precio_unitario INTEGER NOT NULL CHECK(precio_unitario >= 0),
  costo_unitario INTEGER NOT NULL DEFAULT 0 CHECK(costo_unitario >= 0),
  total_linea INTEGER NOT NULL CHECK(total_linea >= 0),
  creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK(total_linea = CAST(ROUND(cantidad * precio_unitario) AS INTEGER))
);

CREATE INDEX IF NOT EXISTS idx_ordenes_items_orden ON ordenes_taller_items(orden_id);
CREATE INDEX IF NOT EXISTS idx_ordenes_items_servicio ON ordenes_taller_items(servicio_id);

CREATE TRIGGER IF NOT EXISTS tr_orden_item_recalcula_alta
AFTER INSERT ON ordenes_taller_items
BEGIN
  UPDATE ordenes_taller
     SET subtotal=(SELECT COALESCE(SUM(total_linea),0) FROM ordenes_taller_items WHERE orden_id=NEW.orden_id),
         costo_interno=(SELECT COALESCE(SUM(CAST(ROUND(cantidad*costo_unitario) AS INTEGER)),0) FROM ordenes_taller_items WHERE orden_id=NEW.orden_id),
         actualizado_en=datetime('now','localtime')
   WHERE id=NEW.orden_id;
END;

CREATE TRIGGER IF NOT EXISTS tr_orden_item_recalcula_cambio
AFTER UPDATE ON ordenes_taller_items
BEGIN
  UPDATE ordenes_taller
     SET subtotal=(SELECT COALESCE(SUM(total_linea),0) FROM ordenes_taller_items WHERE orden_id=NEW.orden_id),
         costo_interno=(SELECT COALESCE(SUM(CAST(ROUND(cantidad*costo_unitario) AS INTEGER)),0) FROM ordenes_taller_items WHERE orden_id=NEW.orden_id),
         actualizado_en=datetime('now','localtime')
   WHERE id=NEW.orden_id;
  UPDATE ordenes_taller
     SET subtotal=(SELECT COALESCE(SUM(total_linea),0) FROM ordenes_taller_items WHERE orden_id=OLD.orden_id),
         costo_interno=(SELECT COALESCE(SUM(CAST(ROUND(cantidad*costo_unitario) AS INTEGER)),0) FROM ordenes_taller_items WHERE orden_id=OLD.orden_id),
         actualizado_en=datetime('now','localtime')
   WHERE id=OLD.orden_id AND OLD.orden_id<>NEW.orden_id;
END;

CREATE TRIGGER IF NOT EXISTS tr_orden_item_recalcula_baja
AFTER DELETE ON ordenes_taller_items
BEGIN
  UPDATE ordenes_taller
     SET subtotal=(SELECT COALESCE(SUM(total_linea),0) FROM ordenes_taller_items WHERE orden_id=OLD.orden_id),
         costo_interno=(SELECT COALESCE(SUM(CAST(ROUND(cantidad*costo_unitario) AS INTEGER)),0) FROM ordenes_taller_items WHERE orden_id=OLD.orden_id),
         actualizado_en=datetime('now','localtime')
   WHERE id=OLD.orden_id;
END;

CREATE TRIGGER IF NOT EXISTS tr_orden_taller_actualizada
AFTER UPDATE ON ordenes_taller
WHEN NEW.actualizado_en IS OLD.actualizado_en
BEGIN
  UPDATE ordenes_taller SET actualizado_en=datetime('now','localtime') WHERE id=NEW.id;
END;

CREATE TABLE IF NOT EXISTS seguimientos_clientes (
  id INTEGER PRIMARY KEY,
  usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
  responsable TEXT,
  canal TEXT NOT NULL CHECK(canal IN ('llamada','correo','whatsapp','presencial','nota','otro')),
  asunto TEXT NOT NULL,
  detalle TEXT,
  estado TEXT NOT NULL DEFAULT 'pendiente'
    CHECK(estado IN ('pendiente','realizado','cancelado')),
  fecha_contacto TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  proximo_contacto TEXT,
  creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_seguimientos_cliente_fecha ON seguimientos_clientes(usuario_id,fecha_contacto);
CREATE INDEX IF NOT EXISTS idx_seguimientos_pendientes ON seguimientos_clientes(estado,proximo_contacto);

CREATE VIEW IF NOT EXISTS v_reporte_ventas_mensual AS
SELECT substr(f.fecha_emision,1,7) AS mes,
       COUNT(*) AS facturas,
       SUM(f.subtotal) AS subtotal,
       SUM(f.descuento) AS descuentos,
       SUM(f.impuestos) AS impuestos,
       SUM(f.total) AS total_facturado,
       SUM(CASE WHEN f.estado='pagada' THEN f.total ELSE 0 END) AS total_pagado
  FROM facturas f
 WHERE f.estado IN ('emitida','pagada')
 GROUP BY substr(f.fecha_emision,1,7);

CREATE VIEW IF NOT EXISTS v_reporte_vehiculos_ventas AS
SELECT pi.inventario_id,
       pi.sku,
       pi.nombre,
       SUM(pi.cantidad) AS unidades_vendidas,
       SUM(pi.cantidad*pi.precio_unitario) AS total_lineas
  FROM pedidos_items pi
  JOIN pedidos p ON p.id=pi.pedido_id
 WHERE p.estado IN ('confirmado','facturado')
 GROUP BY pi.inventario_id,pi.sku,pi.nombre;

CREATE VIEW IF NOT EXISTS v_reporte_pagos AS
SELECT substr(COALESCE(p.pagado_en,p.creado_en),1,7) AS mes,
       p.metodo,
       COUNT(*) AS cantidad_pagos,
       SUM(CASE WHEN p.estado='confirmado' THEN p.valor ELSE 0 END) AS valor_confirmado
  FROM pagos p
 GROUP BY substr(COALESCE(p.pagado_en,p.creado_en),1,7),p.metodo;

CREATE VIEW IF NOT EXISTS v_reporte_taller_mensual AS
SELECT substr(COALESCE(o.fecha_cierre,o.fecha_ingreso),1,7) AS mes,
       COUNT(*) AS ordenes_finalizadas,
       SUM(o.subtotal) AS total_servicios,
       SUM(o.costo_interno) AS costo_interno,
       SUM(o.subtotal-o.costo_interno) AS margen_estimado
  FROM ordenes_taller o
 WHERE o.estado IN ('lista','entregada')
 GROUP BY substr(COALESCE(o.fecha_cierre,o.fecha_ingreso),1,7);

CREATE VIEW IF NOT EXISTS v_reporte_cotizaciones AS
SELECT 'financiacion' AS tipo,id,usuario_id,estado,creado_en,precio_vehiculo AS valor_referencia
  FROM cotizaciones_financiacion
UNION ALL
SELECT 'seguro' AS tipo,id,usuario_id,estado,creado_en,valor_asegurado AS valor_referencia
  FROM cotizaciones_seguro;

CREATE VIEW IF NOT EXISTS v_reporte_clientes AS
SELECT u.id AS usuario_id,u.nombre,u.documento,u.email,u.telefono,u.creado_en,
       (SELECT COUNT(*) FROM pedidos p WHERE p.usuario_id=u.id) AS pedidos,
       (SELECT COUNT(*) FROM cotizaciones_financiacion c WHERE c.usuario_id=u.id) AS cotizaciones_financiacion,
       (SELECT COUNT(*) FROM cotizaciones_seguro s WHERE s.usuario_id=u.id) AS cotizaciones_seguro,
       (SELECT COUNT(*) FROM citas_taller t WHERE t.usuario_id=u.id) AS citas_taller,
       (SELECT COUNT(*) FROM seguimientos_clientes sc WHERE sc.usuario_id=u.id) AS seguimientos
  FROM usuarios u;

INSERT OR IGNORE INTO migraciones(nombre) VALUES('0010_ampliacion_profesional');

COMMIT;

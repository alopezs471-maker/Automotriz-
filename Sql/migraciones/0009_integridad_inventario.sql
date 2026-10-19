-- 0009: ajustes de la base de datos (solo objetos de datos; ni código ni páginas).
--
--  1. Al cancelar un pedido CONFIRMADO o FACTURADO, las unidades ya no se
--     perdían: la reserva estaba "consumida" y el trigger anterior solo
--     devolvía stock de reservas "activas". Ahora se devuelven ambas.
--  2. Índice para el kardex (evita ordenar en memoria cada consulta).
--  3. Índice parcial para reservas activas (la consulta más frecuente).
--  4. `actualizado_en` automático en citas, pruebas de manejo y fichas.
--  5. Blindaje: las existencias nunca pueden quedar negativas, ni por un
--     ajuste manual (el CHECK ya lo impide en pedidos).
BEGIN;

--  1. cancelar
DROP TRIGGER IF EXISTS tr_pedido_cancelado;

CREATE TRIGGER tr_pedido_cancelado
AFTER UPDATE OF estado ON pedidos
WHEN NEW.estado = 'cancelado' AND OLD.estado <> 'cancelado'
BEGIN
  -- Devolver unidades de reservas activas (pedido pendiente) y de reservas
  -- ya consumidas (pedido confirmado o facturado que luego se cancela).
  UPDATE inventario SET existencias = existencias + (
           SELECT SUM(r.cantidad) FROM inventario_reservas r
            WHERE r.pedido_id = NEW.id
              AND r.estado IN ('activa','consumida')
              AND r.inventario_id = inventario.id)
   WHERE existencias IS NOT NULL
     AND id IN (SELECT inventario_id FROM inventario_reservas
                 WHERE pedido_id = NEW.id AND estado IN ('activa','consumida'));

  INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
  SELECT r.inventario_id,'entrada',r.cantidad,
         (SELECT existencias FROM inventario i WHERE i.id = r.inventario_id),
         CASE WHEN r.estado = 'consumida' THEN 'Pedido confirmado cancelado'
              ELSE 'Pedido cancelado' END,
         NEW.radicado
    FROM inventario_reservas r
   WHERE r.pedido_id = NEW.id AND r.estado IN ('activa','consumida');

  UPDATE inventario_reservas SET estado = 'liberada'
   WHERE pedido_id = NEW.id AND estado IN ('activa','consumida');
END;

-- Al reactivar un pedido cancelado (p. ej. se canceló por error y se vuelve a
-- 'pendiente') se reserva de nuevo lo que se había liberado o vencido, sin
-- volver a descontar dos veces: se reutilizan las reservas de ese mismo pedido.
DROP TRIGGER IF EXISTS tr_pedido_reactivado;

CREATE TRIGGER tr_pedido_reactivado
AFTER UPDATE OF estado ON pedidos
WHEN NEW.estado IN ('pendiente','confirmado','facturado') AND OLD.estado = 'cancelado'
BEGIN
  UPDATE inventario SET existencias = existencias - (
           SELECT SUM(r.cantidad) FROM inventario_reservas r
            WHERE r.pedido_id = NEW.id
              AND r.estado IN ('liberada','vencida')
              AND r.inventario_id = inventario.id)
   WHERE existencias IS NOT NULL
     AND id IN (SELECT inventario_id FROM inventario_reservas
                 WHERE pedido_id = NEW.id AND estado IN ('liberada','vencida'));

  INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
  SELECT r.inventario_id,'salida',-r.cantidad,
         (SELECT existencias FROM inventario i WHERE i.id = r.inventario_id),
         'Pedido reactivado', NEW.radicado
    FROM inventario_reservas r
   WHERE r.pedido_id = NEW.id AND r.estado IN ('liberada','vencida');

  UPDATE inventario_reservas
     SET estado = CASE WHEN NEW.estado = 'pendiente' THEN 'activa' ELSE 'consumida' END,
         expira_en = CASE WHEN NEW.estado = 'pendiente'
                          THEN datetime('now','localtime','+48 hours') ELSE expira_en END
   WHERE pedido_id = NEW.id AND estado IN ('liberada','vencida');
END;

-- El pedido confirmado consume la reserva; el pendiente la mantiene activa.
-- Si la reserva ya había vencido (o se había liberado), al confirmar se vuelve
-- a descontar el stock: no se puede confirmar una venta sin unidades.
DROP TRIGGER IF EXISTS tr_pedido_confirmado;

CREATE TRIGGER tr_pedido_confirmado
AFTER UPDATE OF estado ON pedidos
WHEN NEW.estado IN ('confirmado','facturado') AND OLD.estado NOT IN ('confirmado','facturado')
BEGIN
  UPDATE inventario SET existencias = existencias - (
           SELECT SUM(r.cantidad) FROM inventario_reservas r
            WHERE r.pedido_id = NEW.id
              AND r.estado IN ('vencida','liberada')
              AND r.inventario_id = inventario.id)
   WHERE existencias IS NOT NULL
     AND id IN (SELECT inventario_id FROM inventario_reservas
                 WHERE pedido_id = NEW.id AND estado IN ('vencida','liberada'));

  INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
  SELECT r.inventario_id,'salida',-r.cantidad,
         (SELECT existencias FROM inventario i WHERE i.id = r.inventario_id),
         'Pedido confirmado (reserva vencida)', NEW.radicado
    FROM inventario_reservas r
   WHERE r.pedido_id = NEW.id AND r.estado IN ('vencida','liberada');

  UPDATE inventario_reservas SET estado = 'consumida'
   WHERE pedido_id = NEW.id AND estado IN ('activa','vencida','liberada');
END;

--  2 y 3. índices
-- Kardex: «los últimos movimientos de este vehículo» sin ordenar en memoria.
CREATE INDEX IF NOT EXISTS ix_movimientos_inv_id
  ON inventario_movimientos(inventario_id, id DESC);

-- Reservas que ocupan stock ahora mismo (índice parcial: pesa poco).
CREATE INDEX IF NOT EXISTS ix_reservas_activas
  ON inventario_reservas(inventario_id) WHERE estado = 'activa';

-- Franjas con citas: la agenda filtra por fecha + hora y excluye canceladas.
CREATE INDEX IF NOT EXISTS ix_citas_franja
  ON citas_taller(fecha_programada, hora_programada, estado);

-- Ofertas que se pueden cobrar hoy: v_precios filtra por estado y fechas.
CREATE INDEX IF NOT EXISTS ix_promos_vigencia_estado
  ON promociones(estado, fecha_inicio, fecha_fin);

--  4. actualizado_en automático
CREATE TRIGGER IF NOT EXISTS tr_cita_actualizada
AFTER UPDATE ON citas_taller
WHEN NEW.actualizado_en IS OLD.actualizado_en
BEGIN
  UPDATE citas_taller SET actualizado_en = datetime('now','localtime') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS tr_prueba_actualizada
AFTER UPDATE ON pruebas_manejo
WHEN NEW.actualizado_en IS OLD.actualizado_en
BEGIN
  UPDATE pruebas_manejo SET actualizado_en = datetime('now','localtime') WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS tr_ficha_actualizada
AFTER UPDATE ON inventario_ficha
WHEN NEW.actualizado_en IS OLD.actualizado_en
BEGIN
  UPDATE inventario_ficha SET actualizado_en = datetime('now','localtime')
   WHERE inventario_id = NEW.inventario_id;
END;

--  5. blindaje
-- Ningún camino (SQL directo incluido) puede dejar existencias negativas.
CREATE TRIGGER IF NOT EXISTS tr_existencias_no_negativas
BEFORE UPDATE OF existencias ON inventario
WHEN NEW.existencias IS NOT NULL AND NEW.existencias < 0
BEGIN
  SELECT RAISE(ABORT, 'Las existencias no pueden ser negativas.');
END;

-- Consistencia de la reserva: nunca más unidades que las vendidas en el pedido.
CREATE TRIGGER IF NOT EXISTS tr_reserva_valida
BEFORE INSERT ON inventario_reservas
WHEN NEW.cantidad <= 0
BEGIN
  SELECT RAISE(ABORT, 'La reserva debe tener una cantidad positiva.');
END;

COMMIT;

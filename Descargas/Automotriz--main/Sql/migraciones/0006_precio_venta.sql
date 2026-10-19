-- =====================================================================
-- DasAuto · Migración 0006 · UNA SOLA REGLA DE PRECIO
-- ---------------------------------------------------------------------
-- Antes el precio se calculaba en tres sitios y no coincidían:
--   * catalogo()          respetaba el estado y las fechas de la promoción;
--   * v_catalogo_publico  también, pero mostraba título y beneficio de borradores;
--   * guardar_pedido()    cobraba la oferta SIEMPRE, aunque fuera un borrador
--                         o estuviera finalizada.
--
-- Ahora la regla vive solo aquí, en la vista v_precios:
--   la oferta aplica únicamente si la promoción está 'publicada' y la fecha
--   de hoy (hora local del servidor, igual que hoy() en servidor.py) está
--   dentro de fecha_inicio / fecha_fin (vacías = sin límite).
--   precio_venta es lo que se muestra en la tienda y lo que se cobra.
--
-- Solo recrea VISTAS (no guardan datos): ninguna tabla se modifica.
-- =====================================================================

BEGIN;

DROP VIEW IF EXISTS v_catalogo_publico;
DROP VIEW IF EXISTS v_precios;

CREATE VIEW v_precios AS
SELECT b.*,
       CASE WHEN b.promo_vigente = 1 THEN b.precio_promocional
            ELSE b.precio_base END AS precio_venta
FROM (
  SELECT i.id AS inventario_id, i.sku, i.nombre, i.categoria, i.propulsion,
         i.precio_base, i.existencias, i.moneda,
         p.titulo, p.beneficio, p.precio_promocional,
         COALESCE(p.estado, 'sin_promocion') AS estado,
         p.fecha_inicio, p.fecha_fin,
         CASE WHEN p.estado = 'publicada'
               AND (p.fecha_inicio IS NULL OR p.fecha_inicio <= date('now', 'localtime'))
               AND (p.fecha_fin    IS NULL OR p.fecha_fin    >= date('now', 'localtime'))
              THEN 1 ELSE 0 END AS promo_vigente
  FROM inventario i
  LEFT JOIN promociones p ON p.inventario_id = i.id
) AS b;

-- Vitrina pública: los datos de una promoción solo aparecen si está vigente.
CREATE VIEW v_catalogo_publico AS
SELECT inventario_id, sku, nombre, categoria, propulsion,
       precio_base, existencias, moneda,
       CASE WHEN promo_vigente = 1 THEN precio_promocional END AS precio_promocional,
       precio_venta,
       CASE WHEN promo_vigente = 1 THEN titulo END AS titulo,
       CASE WHEN promo_vigente = 1 THEN beneficio END AS beneficio,
       promo_vigente
FROM v_precios;

-- Registro de la migración dentro de la misma transacción.
INSERT OR IGNORE INTO migraciones(nombre) VALUES('0006_precio_venta');

COMMIT;

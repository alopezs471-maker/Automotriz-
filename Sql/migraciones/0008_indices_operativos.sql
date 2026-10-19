-- DasAuto · Migración 0008 · índices operativos adicionales.
-- Solo crea índices; no cambia ni elimina datos ni restricciones.
BEGIN;

CREATE INDEX IF NOT EXISTS idx_citas_usuario_estado
  ON citas_taller(usuario_id, estado);
CREATE INDEX IF NOT EXISTS idx_pruebas_usuario_estado
  ON pruebas_manejo(usuario_id, estado);
CREATE INDEX IF NOT EXISTS idx_contactos_usuario_creado
  ON contactos(usuario_id, creado_en);
CREATE INDEX IF NOT EXISTS idx_fin_usuario_creado
  ON cotizaciones_financiacion(usuario_id, creado_en);
CREATE INDEX IF NOT EXISTS idx_seguro_usuario_creado
  ON cotizaciones_seguro(usuario_id, creado_en);
CREATE INDEX IF NOT EXISTS idx_pedidos_usuario_creado
  ON pedidos(usuario_id, creado_en);
CREATE INDEX IF NOT EXISTS idx_pedidos_items_inventario
  ON pedidos_items(inventario_id);
CREATE INDEX IF NOT EXISTS idx_reservas_inventario_estado
  ON inventario_reservas(inventario_id, estado);
CREATE INDEX IF NOT EXISTS idx_promos_historico_auto_fecha
  ON promociones_historico(inventario_id, cerrada_en);
CREATE INDEX IF NOT EXISTS idx_auditoria_tabla_registro_fecha
  ON auditoria(tabla, registro_id, creado_en);

INSERT OR IGNORE INTO migraciones(nombre) VALUES('0008_indices_operativos');

COMMIT;

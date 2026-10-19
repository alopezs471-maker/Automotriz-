-- 
-- DasAuto · Migración 0003 · ÍNDICES OPCIONALES sobre tablas existentes
-- 
-- Un índice NO cambia datos, NO cambia el significado de las columnas y
-- NO rompe ninguna consulta existente: solo acelera las búsquedas.
-- De todas formas va en archivo aparte para que decidas aplicarlo o no.
--
-- Cuándo se nota la diferencia: cuando pqrs pase de cientos a decenas de
-- miles de filas y cuando el catálogo se filtre por categoría/propulsión.
-- Costo: la base ocupa un poco más y los INSERT son un pelín más lentos.
-- 

CREATE INDEX IF NOT EXISTS idx_pqrs_estado      ON pqrs(estado);
CREATE INDEX IF NOT EXISTS idx_pqrs_creado      ON pqrs(creado_en);
CREATE INDEX IF NOT EXISTS idx_pqrs_tipo        ON pqrs(tipo_pqrs);
CREATE INDEX IF NOT EXISTS idx_pqrs_usuario     ON pqrs(usuario_id);
CREATE INDEX IF NOT EXISTS idx_pqrs_email       ON pqrs(email);

CREATE INDEX IF NOT EXISTS idx_usuarios_doc     ON usuarios(documento);
CREATE INDEX IF NOT EXISTS idx_usuarios_nombre  ON usuarios(nombre);

CREATE INDEX IF NOT EXISTS idx_inventario_cat   ON inventario(categoria);
CREATE INDEX IF NOT EXISTS idx_inventario_prop  ON inventario(propulsion);

CREATE INDEX IF NOT EXISTS idx_promos_estado    ON promociones(estado);
CREATE INDEX IF NOT EXISTS idx_promos_vigencia  ON promociones(fecha_inicio, fecha_fin);

-- Registro de la migración (solo INSERTA una fila, no toca las demás).
INSERT OR IGNORE INTO migraciones(nombre) VALUES('0003_indices_opcionales');

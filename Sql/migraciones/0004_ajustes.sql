-- 
-- DasAuto · Migración 0004 · Ajustes sobre las tablas nuevas de 0002
-- 
-- Solo toca tablas creadas por 0002 (que no existían antes), nunca las
-- originales: usuarios, pqrs, inventario, promociones, migraciones.
-- 

-- El cotizador de Seguros.html pregunta el tipo de vehículo; 0002 no lo tenía.
ALTER TABLE cotizaciones_seguro ADD COLUMN tipo_vehiculo TEXT;

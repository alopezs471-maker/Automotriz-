-- 
-- DasAuto · Migración 0005 · Ajustes sobre tablas nuevas de 0002
-- 
-- El formulario de "Agendar prueba" permite elegir sede; se guarda el
-- texto seleccionado (la sede_id se resuelve cuando el nombre coincide).
-- 

ALTER TABLE pruebas_manejo ADD COLUMN sede_texto TEXT;

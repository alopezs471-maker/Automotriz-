# Ampliación profesional de la base de datos de DasAuto

## Alcance

La migración `0010_ampliacion_profesional.sql` agrega tablas y vistas a SQLite. No elimina ni altera las tablas anteriores. El inicializador registra la migración junto con las demás revisiones pendientes.

## Ventas y facturación

`facturas` registra el comprobante comercial y conserva los datos del cliente en el momento de emisión. Cada factura corresponde a un pedido. `pagos` admite abonos y varios medios de pago. Los disparadores impiden facturar pedidos cancelados, sobrepasar el valor de una factura y marcarla pagada si mantiene saldo.

Esta estructura es para el control interno del concesionario. Antes de usarla como facturación electrónica oficial en Colombia, debe integrarse y validarse con un proveedor autorizado y los requisitos tributarios aplicables.

## Taller y mantenimiento

`servicios_taller` mantiene el catálogo de servicios. `ordenes_taller` registra la recepción, el diagnóstico, el técnico, el estado y las fechas. `ordenes_taller_items` almacena servicios, repuestos y mano de obra. Los disparadores recalculan el subtotal y el costo interno cuando se modifican los conceptos.

## Clientes y cotizaciones

`seguimientos_clientes` registra el canal, responsable, resultado y próxima fecha de contacto. `v_reporte_clientes` consolida la actividad relacionada con cada cliente sin duplicar su ficha principal.

## Seguridad y permisos

`roles`, `permisos` y `rol_permisos` definen los permisos por rol. Se conservan los roles existentes `admin`, `ventas`, `taller` y `consulta`. La API del panel verifica los permisos para consultar secciones y ejecutar acciones.

## Reportes

Las vistas `v_reporte_ventas_mensual`, `v_reporte_vehiculos_ventas`, `v_reporte_pagos`, `v_reporte_taller_mensual`, `v_reporte_cotizaciones` y `v_reporte_clientes` permiten consultar métricas directamente desde SQLite. Las ventas reportadas proceden de facturas emitidas o pagadas, mientras que el pago confirmado se calcula aparte.

## Aplicación y verificación

Al arrancar el servidor, `base_datos.py` aplica las migraciones pendientes automáticamente. Para ejecutar las pruebas desde la raíz del repositorio:

```bash
python -m unittest discover -s Sql/tests -v
```

Antes de usar datos reales, ejecuta un respaldo con `python Sql/mantenimiento.py respaldo` y revisa la integridad con `python Sql/mantenimiento.py informe`.

## Nota sobre los datos

La migración no asigna existencias inventadas ni modifica el stock actual. Los valores monetarios se almacenan como enteros en pesos colombianos. Las tablas de facturas y pagos son registros internos y no sustituyen una integración de facturación electrónica.

## Integración del panel

El endpoint protegido `GET /api/admin/datos?seccion=reportes` devuelve las vistas de estadísticas. También se agregan las secciones `facturas`, `pagos`, `taller` y `clientes`. La exportación usa el mismo permiso que la consulta.

El endpoint protegido `POST /api/admin/accion` admite las acciones `factura_crear`, `pago_registrar`, `factura_anular`, `orden_taller_crear`, `orden_taller_estado`, `orden_item_agregar` y `seguimiento_crear`. Las acciones comprueban el rol antes de ejecutar la operación y registran la actividad en auditoría.

Los permisos de lectura y escritura se comprueban en el servidor. La interfaz debe mostrar las opciones apropiadas para el rol, pero ocultar un botón no sustituye la comprobación de permisos de la API.

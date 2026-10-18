# Automotriz · DasAuto

Sitio web del concesionario + base de datos SQLite y servidor local en Python
(sin dependencias externas, Python 3.10+).

## Cómo arrancar

```bash
cd Sql
python servidor.py            # o doble clic en iniciar_windows.bat
```

Luego abre **<http://localhost:8000/index.html>**.

> Importante: hay que entrar por `http://localhost:8000`. Si abres los `.html`
> directamente o con Live Server, los formularios no guardan en la base de datos.

## Qué guarda en la base de datos

| Página | Tabla |
|---|---|
| `PQRS.html` | `pqrs` (+ `pqrs_eventos` con la trazabilidad) |
| `Taller.html` | `citas_taller` |
| `Agendar prueba.html` | `pruebas_manejo` |
| `Contacto.html` | `contactos` |
| `Seguros.html` | `cotizaciones_seguro` |
| `Promociones.html` → "Proceder al Pago" | `pedidos` + `pedidos_items` |

La base vive en `Sql/datos/dasauto.sqlite3` y **no se sube a Git** (ver `.gitignore`).
Las tablas y migraciones están en `Sql/migraciones/` y se aplican solas al arrancar.

## Gestión por terminal

```bash
python gestionar.py resumen                  # indicadores generales
python gestionar.py listar pqrs              # usuarios, pqrs, inventario, citas_taller, pedidos…
python gestionar.py responder PQRS-2026-XXX "Texto de la respuesta"
python gestionar.py estado-pqrs PQRS-2026-XXX en_proceso
python gestionar.py estado-cita T-2026-XXX confirmada
python gestionar.py asignar-cita T-2026-XXX 2026-10-22 09:00
python gestionar.py stock corolla 4          # existencias
python gestionar.py precio corolla 120000000 # precio de la promoción
python gestionar.py estado-promocion corolla publicada   # la oferta se cobra solo si está publicada y vigente
python gestionar.py estado-promocion todas publicada     # todas de una vez (o: todas borrador)
python gestionar.py listar v_precios         # precio_venta: lo que se muestra y se cobra hoy
python gestionar.py respaldo                 # copia de seguridad con fecha y hora
```

## Precios y promociones

La regla de precio vive en un solo lugar: la vista `v_precios`
(`Sql/migraciones/0006_precio_venta.sql`). Su columna `precio_venta` es lo que
muestran las tarjetas y el carrito **y lo que cobra el pedido**:

- Promoción `publicada` y hoy dentro de `fecha_inicio`–`fecha_fin` (vacías = sin límite) → precio de oferta.
- `borrador`, `finalizada`, fuera de fechas o sin promoción → precio base.

Todas las promociones nacen en `borrador` y solo se ven en la tabla de revisión
de `Promociones.html` hasta que las publiques con `gestionar.py estado-promocion`.

## Estructura

```
├── *.html                 Páginas del sitio
├── css/  js/  img/        Estilos, scripts e imágenes
└── Sql/
    ├── base_datos.py      Esquema, conexión y consultas
    ├── servidor.py        API + servidor de archivos
    ├── gestionar.py       Administración por terminal
    ├── catalogo_inicial.json   Catálogo semilla (32 vehículos)
    ├── datos/             Base de datos (no se versiona)
    ├── migraciones/       .sql aditivos + aplicador
    └── PROPUESTA_BASE_DATOS.md  Diagnóstico y propuesta completa
```

## Seguridad y datos personales

- Las PQRS y los formularios exigen aceptar el tratamiento de datos (Ley 1581 de 2012).
- No se sirven por HTTP la base de datos, el código Python ni el `.git`.
- Los datos personales se consultan con `gestionar.py`, nunca desde la web.

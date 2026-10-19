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
| `financiar.html` (nueva) | `cotizaciones_financiacion` + `tasas_financiacion` |
| `agenda-taller.html` (nueva) | `citas_taller` con cupos por hora |
| `panel.html` (nueva, con clave) | promociones, precios, inventario, agenda, pedidos y usuarios |

La base vive en `Sql/datos/dasauto.sqlite3` y **no se sube a Git** (ver `.gitignore`).
Las tablas y migraciones están en `Sql/migraciones/` y se aplican solas al arrancar.

## Funciones nuevas

Son páginas **aparte**: no modifican las páginas ni las tablas que ya existían.
El centro de todo es **`nuevas-funciones.html`**.

| Página | Qué resuelve |
|---|---|
| `financiar.html` | Simulador con las tasas de `tasas_financiacion`; guarda la solicitud con radicado `COT-…` |
| `vehiculo.html?sku=corolla` | Ficha técnica, precio vigente, stock, similares e historial de precios |
| `disponibilidad.html` | Existencias reales de los 32 vehículos, con filtros |
| `agenda-taller.html` | Cita de taller en franjas de una hora con cupo limitado |
| `panel.html` | Administración con usuario y clave |

### Panel de administración

Abre <http://localhost:8000/panel.html>. La primera vez el servidor crea el usuario
`admin` y deja la clave en **`Sql/datos/clave_admin_inicial.txt`** (puedes fijarla tú
con la variable `DASAUTO_ADMIN_CLAVE`). Desde el panel se publican promociones, se
cambian precios y fechas, se ajustan existencias, se liberan reservas, se fijan cupos,
se gestionan citas, pedidos y solicitudes, y se crean usuarios.

Las cuentas también se manejan por terminal (la clave se pide de forma oculta):

```bash
cd Sql
python admin.py usuarios
python admin.py crear asesor "Asesor Uno" ventas
python admin.py clave admin
python admin.py activar asesor no
```

Roles: `admin` (todo), `ventas`, `taller` y `consulta` (solo lectura).

### Qué agregan las migraciones 0007 y 0008

| Objeto | Para qué |
|---|---|
| `admin_usuarios`, `admin_sesiones` | Claves cifradas con PBKDF2-SHA256 (240.000 iteraciones) y sesiones de 8 h |
| `precios_historico` + disparadores + `v_historial_precios` | Cada cambio de precio base u oferta, con fecha y origen |
| `inventario_reservas` + disparadores en pedidos | Descenso de existencias, kardex y reserva de 48 h por pedido |
| `agenda_cupos` | Capacidad por fecha y hora (2 por defecto) |
| `tasas_financiacion` | Planes del simulador, editables |
| `inventario_ficha` | Ficha técnica de los 32 vehículos |
| `v_inventario_publico` | Catálogo + ficha + estado de stock |
| Índices y triggers de la migración 0009 | Inventario cuadrado al cancelar, reactivar o confirmar tarde |

Al aplicar la migración se fijan existencias iniciales (entre 3 y 12) solo donde el
dato estaba en `NULL`, y esa dotación se registra en el kardex. Los pedidos nuevos ya
no permiten vender más unidades de las que hay; al cancelar un pedido se devuelven.

> `Taller.html` y su formulario siguen funcionando igual. La agenda nueva
> (`agenda-taller.html`) es la que controla cupos por hora.

### Inventario y mantenimiento de la base (migración 0009)

- **Cancelar un pedido ya confirmado o facturado devuelve las unidades.** Antes solo
  se devolvían las de pedidos pendientes: esas unidades se perdían.
- **Confirmar un pedido cuya reserva venció vuelve a descontar stock**; si ya no hay
  unidades, la confirmación se rechaza.
- **Reactivar un pedido cancelado** vuelve a reservar lo que se había liberado, sin
  descontar dos veces.
- Las existencias no pueden quedar negativas por ningún camino, y `actualizado_en` de
  citas, pruebas y fichas se llena solo.
- Índices nuevos para el kardex, las franjas de agenda y las reservas activas.

Herramientas (no tocan páginas ni código):

```bash
cd Sql
python mantenimiento.py informe        # integridad, claves, descuadres y tamaños
python mantenimiento.py optimizar      # ANALYZE + PRAGMA optimize + vuelca el WAL
python mantenimiento.py limpiar        # borra sesiones vencidas y libera reservas vencidas
python mantenimiento.py respaldo --conservar 10
python mantenimiento.py vacio          # compacta (mejor con el servidor detenido)
```

> Corre **una sola instancia** del servidor sobre la base. Dos servidores escribiendo
> en el mismo archivo provocan bloqueos y el sitio puede quedarse cargando.

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
    ├── api_extra.py       Servicios nuevos: financiación, ficha, inventario, agenda y panel
    ├── admin.py           Cuentas del panel por terminal
    ├── gestionar.py       Administración por terminal
    ├── catalogo_inicial.json   Catálogo semilla (32 vehículos)
    ├── datos/             Base de datos (no se versiona)
    ├── migraciones/       .sql aditivos + aplicador
    └── PROPUESTA_BASE_DATOS.md  Diagnóstico y propuesta completa
```

## Seguridad y datos personales

- Las PQRS y los formularios exigen aceptar el tratamiento de datos (Ley 1581 de 2012).
- No se sirven por HTTP la base de datos, el código Python ni el `.git`.
- El panel exige usuario y clave (cookie HttpOnly, SameSite=Strict, 8 horas) y cada
  cambio queda registrado en `auditoria`. La clave inicial está en `Sql/datos/`,
  que no se sube a Git.
- Las páginas nuevas piden aceptar el tratamiento de datos (Ley 1581 de 2012).

## Peso de las páginas y recursos faltantes

Revisión de las 21 páginas: cada una carga completa, sin errores de JavaScript y sin
referencias a archivos inexistentes.

- **Imágenes**: se redimensionaron a 1800 px de lado máximo (640 px las que se muestran
  como miniatura) y se recomprimieron con calidad 82. `img/` pasó de **141 MB a 47 MB**
  y `Taller.html` de **32,8 MB a 3,5 MB**.
- **Videos de fondo**: los clips de 16 MB se piden con `preload="none"`, así solo se
  descargan cuando el visitante llega a esa sección. `Automoviles.html` bajó de
  **22,4 MB a 2,4 MB** al abrir.
- **Archivos que faltaban**: `img/wahs.jpg` (creado reutilizando `wash.jpg`), y los
  videos `video3/5/6/7/8/9/10.mp4` que solo existían en el HTML. En las secciones
  finales de Automóviles, Camioneta, Eléctricos y Motos se usa la imagen destacada; el
  video de fondo de Camioneta, Eléctricos y Motos es `img/video.mp4`.
- **Enlaces rotos**: el botón ☰ de 8 páginas apuntaba a `formuario.html` (no existe);
  ahora va a `Contacto.html`. El botón «Ordenar» de `Electricos.html` va a
  `Promociones.html`, igual que en las demás.
- **`js/j7.js`** se ejecutaba en `Galeria.html`, que no tiene el modal de showroom, y
  lanzaba un `TypeError`. Ahora se detiene si el modal no existe.

Pendiente opcional: `formuario(obsoleto).html` enlaza a `Nosotros.html` y
`Repuestos.html`, que tampoco existen. Es una copia antigua que ninguna página activa
enlaza; se puede borrar.

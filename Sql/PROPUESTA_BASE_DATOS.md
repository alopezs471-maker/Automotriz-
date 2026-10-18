# DasAuto · Propuesta y diagnóstico de base de datos

> **Regla que seguí: no cambié nada de lo que ya tienes.**
> Ningún archivo existente fue modificado. Todo lo de aquí son archivos nuevos
> (`migraciones/0002_extensiones.sql`, `migraciones/0003_indices_opcionales.sql`,
> `migraciones/aplicar.py`) o recomendaciones escritas para que tú decidas.

**Revisado:** `Sql/base_datos.py`, `Sql/servidor.py`, `Sql/gestionar.py`,
`Sql/catalogo_inicial.json`, `Sql/dasauto.sqlite3` (32 vehículos cargados),
`js/conexion-datos.js`, `PQRS.html`, `Promociones.html`, `Contacto.html`,
`Taller.html`, `Agendar prueba.html`, `Financiacion.html`, `Seguros.html`,
`ordenar.html`.

---

## 1. ¿Qué base de datos le puedo poner?

### 1.1 Opciones reales para este proyecto

| Motor | Tipo | Cuándo conviene | Costo | Esfuerzo desde tu código |
|---|---|---|---|---|
| **SQLite** (el que ya tienes) | Archivo local, embebido | Proyecto académico, demo, portafolio, 1 usuario a la vez | $0 | Ninguno, ya está |
| **PostgreSQL** | Servidor SQL | Vas a publicarlo con usuarios reales, varios vendedores, reportes | Gratis (Neon, Supabase, Railway, Render) | Bajo: cambia el driver y los `?` por `%s` |
| **MySQL / MariaDB** | Servidor SQL | Hosting compartido (cPanel, Hostinger, GoDaddy) que solo da MySQL | Incluido en el hosting | Bajo, igual que Postgres |
| **SQL Server** | Servidor SQL | Entorno .NET / Azure / universidad que lo exija | Licencia (Express gratis) | Medio |
| **Supabase / Firebase** | Backend como servicio (BaaS) | Quieres login, API y BD sin mantener servidor | Gratis hasta cierto tráfico | Medio: rehaces `servidor.py` contra su SDK |
| **Turso / libSQL** | SQLite en la nube | Te gusta SQLite pero necesitas acceso desde varias máquinas | Gratis → pago | Muy bajo: misma sintaxis |
| **MongoDB / Firestore** | NoSQL documentos | Catálogo con campos muy variables por vehículo | Gratis → pago | Alto: pierdes los `JOIN` y las FK |

### 1.2 Mi recomendación

**Quédate en SQLite.** Para este proyecto (catálogo de 32 vehículos, PQRS, citas
y formularios de un concesionario) SQLite sobra: soporta ~100.000 escrituras por
segundo en WAL y tu cuello de botella será el servidor Python, no la base.

Cámbiate **solo** si se cumple una de estas:

- 🔴 **Vas a publicarlo en internet con usuarios reales** → **PostgreSQL** (es el
  estándar, tiene tipos de fecha/hora correctos, `TIMESTAMPTZ`, mejor concurrencia
  y hosting gratis serio en Neon/Supabase).
- 🟡 **Tu hosting compartido solo ofrece MySQL** → **MySQL/MariaDB**, no pelees con el hosting.
- 🟡 **No quieres mantener servidor** → **Supabase** (Postgres + API REST automática).
- 🟢 **Solo es para la universidad / presentación local** → SQLite (lo que ya tienes).

> Dato práctico: el 90 % del SQL que ya escribiste funciona igual en PostgreSQL.
> Ver §1.3.

### 1.3 Si algún día pasas a PostgreSQL, los cambios son estos

| En SQLite (hoy) | En PostgreSQL |
|---|---|
| `INTEGER PRIMARY KEY` | `GENERATED ALWAYS AS IDENTITY` (o `SERIAL`) |
| `TEXT` | `TEXT` o `VARCHAR(n)` |
| `INTEGER` para pesos | `BIGINT` (o `NUMERIC(14,2)` si usas centavos) |
| `REAL` | `NUMERIC(6,3)` |
| `TEXT ... DEFAULT CURRENT_TIMESTAMP` | `TIMESTAMPTZ NOT NULL DEFAULT now()` |
| `CHECK (...)` | Idéntico, se soporta ✔ |
| `datetime('now')` | `now()` |
| `?` como parámetro | `%s` (psycopg) |
| `cur.lastrowid` | `INSERT ... RETURNING id` |
| `sqlite3.Row` | `psycopg` + `RealDictCursor` |
| `PRAGMA foreign_keys=ON` | No aplica: las FK siempre se validan |

Es decir: **tu diseño aguanta el salto**. No necesitas rediseñar nada.

---

## 2. Diagnóstico de tu base actual

### 2.1 Lo que está BIEN y no deberías tocar

✔ Uso de `CHECK` constraints en `tipo_pqrs`, `estado`, `acepta_tratamiento`,
`precio_base >= 0`, rangos de fechas: la base se defiende sola.
✔ `radicado` y `envio_id` únicos → el formulario es **idempotente**: si el usuario
reintenta o recarga, no se duplica la PQRS. Esto es de nivel profesional.
✔ `BEGIN IMMEDIATE` antes de insertar → evita condiciones de carrera.
✔ Validación en el **servidor**, no solo en el HTML (largo de campos, email, tipo).
✔ `acepta_tratamiento` obligatorio (Ley 1581 de 2012, protección de datos).
✔ Tabla `migraciones` y carga del catálogo desde JSON: buen hábito.
✔ `timeout=15` y `ThreadingHTTPServer`: pensado para concurrencia.
✔ Sin CORS abierto y con token entregado por el servidor.
✔ `gestionar.py` no expone datos personales en la web: los consultas por terminal.

En serio: el esquema es mejor que el de muchos proyectos de grado. Lo de abajo son
ajustes finos, no un rediseño.

### 2.2 Hallazgos ordenados por urgencia

#### 🔴 P0 · Hacen que hoy no funcione como esperas

> Los tres los verifiqué ejecutando el proyecto: `GET /index.html` devuelve **404**,
> el servidor crea una segunda base `Sql/datos/dasauto.sqlite3` y el `INNER JOIN`
> filtra del catálogo cualquier vehículo sin promoción.

| # | Hallazgo | Evidencia | Impacto | Solución |
|---|---|---|---|---|
| P0-1 | `servidor.py` sirve una carpeta que no existe | `PUBLIC = ROOT/'public'` y `ROOT = Sql/`, pero el sitio está en la carpeta padre | Al abrir `localhost:8000` todo da 404/403: **el servidor no encuentra los HTML** | `PUBLIC = ROOT.parent` (o mover el proyecto dentro de `Sql/public`) |
| P0-2 | Hay **dos** bases de datos y el sistema usa la que no está en Git | `base_datos.py` apunta a `Sql/datos/dasauto.sqlite3`; el archivo versionado con los 32 vehículos es `Sql/dasauto.sqlite3`. Comprobado: al arrancar el servidor crea `Sql/datos/dasauto.sqlite3` desde cero y siembra el catálogo desde el JSON | Las PQRS que hayas guardado en `Sql/dasauto.sqlite3` **nunca se leen**; trabajas sobre una base distinta a la que respaldas en el repo | Unificar la ruta: mueve el archivo a `Sql/datos/` o cambia `DB = ROOT/'dasauto.sqlite3'` |
| P0-3 | `catalogo()` usa `INNER JOIN` con `promociones` | `JOIN promociones p ON p.inventario_id=i.id` | Un vehículo **sin promoción desaparece** de la tabla y deja de sincronizar precio en su tarjeta | `LEFT JOIN` + `COALESCE(p.precio_promocional, i.precio_base)` |

#### 🟠 P1 · Se nota apenas el proyecto crezca

| # | Hallazgo | Impacto | Solución |
|---|---|---|---|
| P1-1 | `existencias` es `NULL` en los 32 registros | La tabla muestra "Por confirmar" en todo el catálogo | Definir `DEFAULT 0` y poblar; o dejar `NULL` pero documentarlo como "sin dato" |
| P1-2 | Las promociones nacen en `estado='borrador'` y aun así se muestran | La tienda publica precios de oferta no aprobados | Filtrar en la API: `WHERE p.estado='publicada' AND (fecha_fin IS NULL OR fecha_fin >= date('now'))` |
| P1-3 | `promociones.inventario_id UNIQUE` | Solo 1 promo por vehículo y **sin histórico**: al cambiar el precio se pierde el anterior | Tabla nueva `promociones_historico` (incluida en 0002) |
| P1-4 | `CURRENT_TIMESTAMP` guarda **UTC** | En Bogotá (UTC-5) todos los reportes salen 5 horas desfasados | Guardar UTC (correcto) y formatear a `America/Bogota` al mostrar; o agregar columna con hora local |
| P1-5 | `usuarios.documento` sin `UNIQUE` | La misma persona con dos correos queda como dos clientes distintos | Índice + validación en la app; un `UNIQUE` directo puede fallar si ya hay duplicados |
| P1-6 | Cero índices explícitos (solo los `UNIQUE`) | Invisible con 100 filas; lento con 100.000 PQRS | `migraciones/0003_indices_opcionales.sql` |
| P1-7 | `dasauto.sqlite3` está **versionado en Git** | Binario en el repo → conflictos, repo pesado y riesgo de subir datos personales reales | `.gitignore` con `*.sqlite3`, `datos/`, y respaldo aparte |
| P1-8 | El token CSRF es **global** para todo el sitio | Bien para localhost; en producción cualquier visitante obtiene el token válido | Token por sesión (cookie `HttpOnly` + `SameSite`) + rate limiting por IP |

#### 🟡 P2 · Oportunidades (formularios que hoy no guardan nada)

| # | Hallazgo | Impacto | Solución (incluida en 0002) |
|---|---|---|---|
| P2-1 | `Agendar prueba.html`, `Taller.html`, `Contacto.html`, `Financiacion.html`, `Seguros.html` **no persisten nada** | Solo PQRS guarda. Los leads se pierden al recargar | `pruebas_manejo`, `citas_taller`, `contactos`, `cotizaciones_financiacion`, `cotizaciones_seguro` |
| P2-2 | El carrito vive solo en `localStorage` | Si el cliente cierra el navegador, el pedido se pierde; no hay venta que reportar | `pedidos` + `pedidos_items` |
| P2-3 | `gestionar.py stock` pisa `existencias` sin dejar rastro | No sabes quién movió qué ni cuándo | `inventario_movimientos` (kardex) |
| P2-4 | No hay marca, año, imagen ni ficha técnica en la BD (todo hardcodeado en el HTML) | Duplicar un vehículo = editar HTML a mano | `inventario_ficha` (tabla aparte, sin tocar `inventario`) |
| P2-5 | No hay `activo`/borrado lógico | Quitar un vehículo del catálogo implica borrarlo y romper FK | `inventario_ficha.activo` |
| P2-6 | `migraciones` no guarda cuándo se aplicó | No hay trazabilidad del esquema | Lo registra `aplicar.py` (puedes agregar columna si migras de verdad) |
| P2-7 | Sin respaldo automático | Un `DELETE` sin `WHERE` y se fue el proyecto | `aplicar.py` ya hace `.bak`; añade un backup diario |

---

## 3. Mejoras propuestas, por nivel de riesgo

### 🟢 Nivel 1 · Cero riesgo (no toca el esquema)

1. **Corregir P0-1, P0-2 y P0-3** — son las únicas tres cosas que hoy hacen que el
   proyecto no se vea como esperas. Son 3 líneas en total.
2. **`.gitignore`** en la raíz:
   ```gitignore
   # Base de datos: nunca al repositorio
   *.sqlite3
   *.sqlite3-journal
   *.sqlite3-wal
   Sql/datos/
   *.bak
   ```
3. **Activar WAL** en `conectar()` — permite leer mientras se escribe:
   ```python
   db.execute('PRAGMA journal_mode=WAL')
   db.execute('PRAGMA synchronous=NORMAL')
   db.execute('PRAGMA busy_timeout=15000')
   ```
4. **Vista de catálogo pública** (`CREATE VIEW` es aditivo, no rompe nada):
   ```sql
   CREATE VIEW IF NOT EXISTS v_catalogo_publico AS
   SELECT i.id, i.sku, i.nombre, i.categoria, i.propulsion,
          i.precio_base, i.existencias, i.moneda,
          COALESCE(p.precio_promocional, i.precio_base) AS precio_venta,
          p.titulo, p.beneficio
   FROM inventario i
   LEFT JOIN promociones p
          ON p.inventario_id = i.id
         AND p.estado = 'publicada'
         AND (p.fecha_inicio IS NULL OR p.fecha_inicio <= date('now'))
         AND (p.fecha_fin   IS NULL OR p.fecha_fin   >= date('now'));
   ```
   Así `catalogo()` deja de esconder vehículos sin promo y deja de publicar borradores.
5. **Hora de Bogotá** al mostrar: `datetime(creado_en,'-5 hours')` en la consulta,
   o formatear en JS con `Intl.DateTimeFormat('es-CO',{timeZone:'America/Bogota'})`.

### 🟡 Nivel 2 · Aditivo (archivos ya listos en `Sql/migraciones/`)

`0002_extensiones.sql` crea **13 tablas nuevas**. No hace ni un solo `ALTER`,
`DROP` ni `UPDATE` sobre `usuarios`, `pqrs`, `inventario`, `promociones` o `migraciones`.

| Tabla nueva | Para qué sirve | Cubre |
|---|---|---|
| `sedes` | Sucursales/talleres (hoy quemadas en el HTML: "Finlandia", "Noruega") | P2 |
| `citas_taller` | Agenda del taller con vehículo, placa, servicio, fecha/hora y estado | P2-1 |
| `pruebas_manejo` | Test drive: modelo de interés, sede, fecha, estado | P2-1 |
| `contactos` | Mensajes del formulario de Contacto | P2-1 |
| `cotizaciones_financiacion` | Simulaciones de crédito (monto, cuota inicial, plazo, tasa, cuota) | P2-1 |
| `cotizaciones_seguro` | Cotizaciones de póliza por tipo de cobertura | P2-1 |
| `pedidos` + `pedidos_items` | La venta nacida del carrito (`ordenar.html`) | P2-2 |
| `inventario_ficha` | Marca, año, imagen, especificaciones, destacado, activo — **sin tocar `inventario`** | P2-4, P2-5 |
| `inventario_movimientos` | Kardex de entradas/salidas/ajustes | P2-3 |
| `promociones_historico` | Histórico de ofertas anteriores | P1-3 |
| `pqrs_eventos` | Quién cambió el estado de una PQRS y cuándo (SLA) | Trazabilidad |
| `auditoria` | Bitácora general de insert/update/delete | P2 |

`0003_indices_opcionales.sql` crea índices sobre tablas existentes. Un índice no
cambia datos ni significados: solo acelera búsquedas. Va en archivo aparte para
que decidas aplicarlo o no.

**Cómo aplicarlas** (desde `Sql/`, respaldo automático incluido):

```bash
# 1) Ver el plan sin tocar nada
python migraciones/aplicar.py --db dasauto.sqlite3 --revision

# 2) Aplicar (crea dasauto.sqlite3.bak antes de empezar)
python migraciones/aplicar.py --db dasauto.sqlite3

# 3) Verificar
python gestionar.py listar promociones
```

Ya lo probé sobre una copia de tu base: **`inventario` y `promociones` quedan
intactas con sus 32 registros**, `PRAGMA integrity_check` = `ok`, y el aplicador
es idempotente (si lo corres dos veces, la segunda dice "no hay migraciones pendientes").

### 🔴 Nivel 3 · Requiere `ALTER` (solo si tú lo autorizas)

Esto es lo que yo haría si me dejaras modificar el esquema. En SQLite el camino
seguro es **crear tabla nueva → copiar → soltar → renombrar** (patrón oficial), y
siempre dentro de una transacción:

| Cambio | Por qué | Cómo |
|---|---|---|
| `inventario.activo INTEGER DEFAULT 1` | Quitar del catálogo sin borrar historial | Recrear tabla |
| `inventario.existencias INTEGER NOT NULL DEFAULT 0` | Hoy `NULL` = "Por confirmar" en todo el catálogo | `UPDATE ... SET existencias=0 WHERE existencias IS NULL` y luego recrear |
| `inventario.actualizado_en TEXT` | Saber cuándo cambió un precio | Recrear + `UPDATE` |
| `promociones.inventario_id` sin `UNIQUE` | Permitir promos históricas en la misma tabla | Recrear (o quedarse con `promociones_historico`) |
| `usuarios.documento UNIQUE` | Evitar clientes duplicados | Primero buscar duplicados, luego recrear |
| Desencadenadores `updated_at` | Auditoría automática | `CREATE TRIGGER` (aditivo, sí se puede ya) |
| Pesos en centavos | Evitar errores de redondeo | Recrear + multiplicar ×100 |

**Nada de esto está aplicado.** Solo lo dejo documentado por si lo quieres.

---

## 4. Cómo queda el modelo

```
                    ┌──────────┐
                    │  sedes   │
                    └────┬─────┘
                         │ 1:N
        ┌────────────────┼─────────────────┐
        ▼                ▼                 ▼
┌───────────────┐ ┌──────────────┐ ┌──────────────┐
│ citas_taller  │ │pruebas_manejo│ │  (futuro)    │
└───────┬───────┘ └──────┬───────┘ └──────────────┘
        │                │
        │  N:1           │  N:1
        ▼                ▼
┌───────────────┐  ┌───────────┐      ┌────────────────────┐
│   usuarios    │◄─┤   pqrs    │◄─────┤    pqrs_eventos    │  (nuevo)
└───────┬───────┘  └───────────┘ N:1  └────────────────────┘
        │ 1:N
        ├──────────► contactos                     (nuevo)
        ├──────────► cotizaciones_financiacion     (nuevo)
        ├──────────► cotizaciones_seguro           (nuevo)
        └──────────► pedidos ──1:N──► pedidos_items (nuevo)
                                            │
                         ┌──────────────────┘ N:1
                         ▼
        ┌─────────────────────────────────────────┐
        │              inventario  (intacto)      │
        └───┬───────────┬──────────────┬──────────┘
            │1:1        │1:N           │1:N
            ▼           ▼              ▼
  ┌─────────────────┐ ┌──────────────────────┐ ┌────────────────┐
  │inventario_ficha │ │inventario_movimientos│ │  promociones   │ (intacto)
  └─────────────────┘ └──────────────────────┘ └───────┬────────┘
                                                       │1:N
                                                       ▼
                                            ┌──────────────────────┐
                                            │promociones_historico │
                                            └──────────────────────┘
```

---

## 5. Endpoints que faltarían en `servidor.py`

Solo el listado; no toqué el archivo. La idea es copiar el mismo patrón
exitoso de `/api/pqrs` (validación server-side + `envio_id` idempotente + CSRF):

| Endpoint | Tabla | Página que lo usaría |
|---|---|---|
| `POST /api/citas-taller` | `citas_taller` | `Taller.html` |
| `POST /api/pruebas-manejo` | `pruebas_manejo` | `Agendar prueba.html` |
| `POST /api/contacto` | `contactos` | `Contacto.html` |
| `POST /api/financiacion` | `cotizaciones_financiacion` | `Financiacion.html` |
| `POST /api/seguros` | `cotizaciones_seguro` | `Seguros.html` |
| `POST /api/pedidos` | `pedidos` + `pedidos_items` | `ordenar.html`, carrito |
| `GET /api/sedes` | `sedes` | `Agendar prueba.html`, `Taller.html` |
| `GET /api/catalogo` | vista `v_catalogo_publico` | todas las vitrinas |

---

## 6. Orden de trabajo sugerido

- [ ] **1.** Corregir P0-1, P0-2, P0-3 (el servidor no sirve el sitio y la BD apunta a otra ruta).
- [ ] **2.** Agregar `.gitignore` y sacar el `.sqlite3` del repositorio.
- [ ] **3.** Activar WAL y crear la vista `v_catalogo_publico`.
- [ ] **4.** `python migraciones/aplicar.py --db dasauto.sqlite3` (Nivel 2).
- [ ] **5.** Llenar `existencias` de los 32 vehículos y publicar las promos que correspondan.
- [ ] **6.** Conectar `Taller.html` y `Agendar prueba.html` (los dos formularios que hoy pierden los datos).
- [ ] **7.** Decidir si el Nivel 3 (ALTER) vale la pena o se queda así.

---

### Nota legal / cumplimiento

Al guardar nombres, documentos, correos y teléfonos estás tratando datos
personales (Ley 1581 de 2012 y Decreto 1377 de 2013): conserva el
`acepta_tratamiento`, no expongas esos datos en la web (tu `gestionar.py` ya lo
hace bien) y no subas el `.sqlite3` con datos reales a GitHub. Para las PQRS el
término general de respuesta de un derecho de petición es de 15 días hábiles
(Ley 1755 de 2015): con `pqrs_eventos` puedes medir ese SLA. Verifica ambos
puntos con tu asesor antes de presentarlo como requisito cumplido.

---

## 7. Bitácora: qué se terminó aplicando

Lo de arriba era la propuesta. Esto es lo que **ya quedó corregido y funcionando**.
En todos los casos se respetó lo que ya existía: las 5 tablas originales
(`usuarios`, `pqrs`, `inventario`, `promociones`, `migraciones`) **no se
modificaron ni se borró un solo dato**.

### 7.1 Correcciones P0 (el proyecto ahora sí levanta)

| # | Antes | Ahora |
|---|---|---|
| P0-1 | `PUBLIC = Sql/public` → 404 en todas las páginas | `PUBLIC = ROOT.parent`: sirve la raíz del repo |
| P0-2 | Dos bases: el código usaba `Sql/datos/…` y el archivo con datos era `Sql/dasauto.sqlite3` | Una sola base en `Sql/datos/dasauto.sqlite3`. Si no existe, **copia** la histórica (nunca la mueve ni la borra) |
| P0-3 | `INNER JOIN` escondía los vehículos sin promoción | `LEFT JOIN` + `COALESCE`, y vista `v_catalogo_publico` que solo publica promos `publicada` y vigentes |

### 7.2 Endurecimiento

- **Archivos privados bloqueados por HTTP**: `Sql/**`, `.git/**`, `.py`, `.sqlite3`, `.md`, `.json`, `.bak` → `403`.
- **Límite de envíos por IP** (8 cada 10 min; ajustable con `DASAUTO_MAX_ENVIOS`).
- **WAL + `busy_timeout`** en `conectar()`: lecturas concurrentes sin "database is locked".
- **Consentimiento explícito** (`terminos`) en todos los formularios, no solo en PQRS.
- Mensajes de error limpios (antes un `envio_id` inválido devolvía el error crudo de Python).

### 7.3 Esquema: 13 tablas nuevas (migraciones 0002–0005)

`citas_taller`, `pruebas_manejo`, `contactos`, `cotizaciones_financiacion`,
`cotizaciones_seguro`, `pedidos`, `pedidos_items`, `inventario_ficha`,
`inventario_movimientos`, `promociones_historico`, `pqrs_eventos`, `sedes`,
`auditoria` + índices.

Se aplican **solas** al arrancar (`iniciar()` ejecuta los `.sql` pendientes de
`Sql/migraciones/`), así que una base nueva nunca queda desactualizada.

### 7.4 Formularios que ahora sí guardan

| Página | Cambio |
|---|---|
| `Taller.html` | Sección nueva **"Agenda tu cita en el taller"** → `citas_taller` |
| `Agendar prueba.html` | El formulario ya no muestra un `alert()` falso: guarda en `pruebas_manejo` (con modelo y sede elegidos) |
| `Contacto.html` | Guarda en `contactos` (+ casilla de tratamiento de datos) |
| `Seguros.html` | El cotizador guarda en `cotizaciones_seguro` (+ casilla de tratamiento) |
| `Promociones.html` | El botón **"Proceder al Pago"** no hacía nada: ahora despliega el checkout y guarda el pedido en `pedidos` + `pedidos_items` + movimientos de inventario |

Todos siguen el mismo patrón que ya tenías en PQRS: token del servidor,
validación del lado del servidor y `envio_id` para no duplicar reintentos.

### 7.5 Herramientas

- `python gestionar.py resumen` → indicadores de un vistazo.
- `python gestionar.py respaldo` → copia coherente de la base (con fecha y hora).
- `python gestionar.py listar <tabla>` acepta las tablas nuevas.
- `python gestionar.py estado-cita|estado-prueba|estado-pedido|asignar-cita …`
- `python migraciones/aplicar.py --db ruta --revision` → aplica migraciones con respaldo.

### 7.6 Pendiente (no se tocó a propósito)

- `Financiacion.html` no tiene formulario: la tabla `cotizaciones_financiacion`
  queda lista para cuando lo crees.
- Nivel 3 de la sección 3 (`ALTER` sobre las tablas originales): sigue esperando tu visto bueno.
- Las promociones siguen en `borrador`; cuando quieras verlas en la vitrina:
  `python gestionar.py estado-promocion corolla publicada` (o `todas publicada`).

### 7.7 Precio de venta unificado (migración 0006)

| Antes | Ahora |
|---|---|
| El pedido cobraba `precio_promocional` siempre, aunque la promo estuviera en `borrador` o `finalizada` | Se cobra `precio_venta` de la vista `v_precios`: la oferta solo si está `publicada` y vigente |
| Las tarjetas mostraban la oferta de los borradores | Tarjetas y carrito usan `precio_venta`; sello, precio tachado y beneficio solo con promo vigente |
| La regla estaba repetida en `catalogo()` y `v_catalogo_publico` (y faltaba en el pedido) | Una sola definición en `v_precios`; `v_catalogo_publico` ya no expone datos de borradores |
| Vigencia comparada con la fecha UTC (`date('now')`) | Fecha local del servidor (`date('now','localtime')`), igual que `hoy()` en `servidor.py` |
| "Confirmar pedido" no estaba conectado: recargaba la página con los datos personales en la URL y **no guardaba nada** | El formulario se conecta al crearse y guarda en `pedidos` + `pedidos_items` |
| El carrito guardado en `localStorage` conservaba precios viejos | Se alinea con `precio_venta` al cargar la página |

Solo se recrearon **vistas** (no guardan datos): ninguna tabla se modificó.

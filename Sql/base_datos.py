from pathlib import Path
import sqlite3, json, shutil, time

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'datos' / 'dasauto.sqlite3'      # Base de trabajo (fuera de la carpeta de código)
LEGADO = ROOT / 'dasauto.sqlite3'            # Base histórica que estaba versionada en Git


def conectar():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    # WAL: permite leer mientras otro proceso escribe. NORMAL: seguro con WAL y más rápido.
    db.execute('PRAGMA journal_mode=WAL')
    db.execute('PRAGMA synchronous=NORMAL')
    db.execute('PRAGMA busy_timeout=15000')
    return db


def iniciar():
    DB.parent.mkdir(exist_ok=True)
    # P0-2: si aún no existe la base de trabajo pero sí la histórica, se rescata
    # (copia, nunca mueve: el archivo original se queda donde está).
    if not DB.exists() and LEGADO.exists():
        shutil.copy2(LEGADO, DB)
    with conectar() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS usuarios (
          id INTEGER PRIMARY KEY, nombre TEXT NOT NULL, documento TEXT NOT NULL,
          email TEXT NOT NULL UNIQUE, telefono TEXT NOT NULL,
          creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS pqrs (
          id INTEGER PRIMARY KEY, radicado TEXT NOT NULL UNIQUE,
          envio_id TEXT NOT NULL UNIQUE,
          usuario_id INTEGER REFERENCES usuarios(id),
          nombre TEXT NOT NULL, documento TEXT NOT NULL, email TEXT NOT NULL,
          telefono TEXT NOT NULL,
          tipo_pqrs TEXT NOT NULL CHECK(tipo_pqrs IN ('peticion','queja','reclamo','sugerencia')),
          descripcion TEXT NOT NULL, acepta_tratamiento INTEGER NOT NULL CHECK(acepta_tratamiento=1),
          estado TEXT NOT NULL DEFAULT 'radicada' CHECK(estado IN ('radicada','en_proceso','respondida','cerrada')),
          respuesta TEXT,
          creado_en TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS inventario (
          id INTEGER PRIMARY KEY, sku TEXT NOT NULL UNIQUE, nombre TEXT NOT NULL,
          categoria TEXT NOT NULL, propulsion TEXT,
          precio_base INTEGER NOT NULL CHECK(precio_base>=0),
          existencias INTEGER CHECK(existencias>=0), moneda TEXT NOT NULL DEFAULT 'COP'
        );
        CREATE TABLE IF NOT EXISTS promociones (
          id INTEGER PRIMARY KEY, inventario_id INTEGER NOT NULL UNIQUE REFERENCES inventario(id),
          titulo TEXT NOT NULL, beneficio TEXT,
          precio_promocional INTEGER NOT NULL CHECK(precio_promocional>=0),
          estado TEXT NOT NULL DEFAULT 'borrador' CHECK(estado IN ('borrador','publicada','finalizada')),
          fecha_inicio TEXT, fecha_fin TEXT,
          CHECK(fecha_inicio IS NULL OR fecha_fin IS NULL OR fecha_fin>=fecha_inicio)
        );
        CREATE TABLE IF NOT EXISTS migraciones (nombre TEXT PRIMARY KEY);
        ''')
        # P0-3 / P1-2: vista pública del catálogo. LEFT JOIN para que un vehículo sin
        # promoción no desaparezca, y solo se publiquen las promos vigentes.
        db.executescript('''
        CREATE VIEW IF NOT EXISTS v_catalogo_publico AS
        SELECT i.id AS inventario_id, i.sku, i.nombre, i.categoria, i.propulsion,
               i.precio_base, i.existencias, i.moneda,
               COALESCE(p.precio_promocional, i.precio_base) AS precio_promocional,
               CASE WHEN p.id IS NOT NULL
                     AND p.estado = 'publicada'
                     AND (p.fecha_inicio IS NULL OR p.fecha_inicio <= date('now'))
                     AND (p.fecha_fin   IS NULL OR p.fecha_fin   >= date('now'))
                    THEN COALESCE(p.precio_promocional, i.precio_base)
                    ELSE i.precio_base END AS precio_venta,
               p.titulo, p.beneficio
        FROM inventario i
        LEFT JOIN promociones p ON p.inventario_id = i.id;
        ''')
        if not db.execute("SELECT 1 FROM migraciones WHERE nombre='catalogo_inicial'").fetchone():
            for r in json.loads((ROOT/'catalogo_inicial.json').read_text(encoding='utf-8')):
                cur = db.execute('INSERT INTO inventario(sku,nombre,categoria,propulsion,precio_base) VALUES(?,?,?,?,?)', (r['sku'],r['nombre'],r['categoria'],r['propulsion'],r['precio']))
                db.execute('INSERT INTO promociones(inventario_id,titulo,beneficio,precio_promocional) VALUES(?,?,?,?)', (cur.lastrowid,r['titulo'],r['beneficio'],r['oferta']))
            db.execute("INSERT INTO migraciones VALUES('catalogo_inicial')")
        aplicar_migraciones(db)


def migraciones_pendientes(db):
    aplicadas = {r[0] for r in db.execute('SELECT nombre FROM migraciones')}
    return [p for p in sorted((ROOT/'migraciones').glob('*.sql')) if p.stem not in aplicadas]


def aplicar_migraciones(db):
    """Aplica los .sql de la carpeta migraciones/ que aún no estén anotados.

    Se llama sola al iniciar, así una base nueva queda siempre al día.
    """
    aplicadas = []
    for archivo in migraciones_pendientes(db):
        db.executescript(archivo.read_text(encoding='utf-8'))
        db.execute('INSERT OR IGNORE INTO migraciones(nombre) VALUES(?)', (archivo.stem,))
        aplicadas.append(archivo.stem)
    return aplicadas


def catalogo():
    """Catálogo para la tabla interna de Promociones.

    P0-3: antes era INNER JOIN y escondía todo vehículo sin promoción.
    Se conservan los campos originales y se añaden precio_venta (el precio que
    realmente se debe cobrar) y promo_vigente.
    """
    with conectar() as db:
        return [dict(r) for r in db.execute('''
        SELECT i.id AS inventario_id, i.sku, i.nombre, i.categoria, i.propulsion,
               i.precio_base, i.existencias, i.moneda,
               COALESCE(p.titulo, '—') AS titulo, p.beneficio,
               COALESCE(p.precio_promocional, i.precio_base) AS precio_promocional,
               COALESCE(p.estado, 'sin_promocion') AS estado,
               p.fecha_inicio, p.fecha_fin,
               CASE WHEN p.id IS NOT NULL
                     AND p.estado = 'publicada'
                     AND (p.fecha_inicio IS NULL OR p.fecha_inicio <= date('now'))
                     AND (p.fecha_fin   IS NULL OR p.fecha_fin   >= date('now'))
                    THEN COALESCE(p.precio_promocional, i.precio_base)
                    ELSE i.precio_base END AS precio_venta,
               CASE WHEN p.id IS NOT NULL
                     AND p.estado = 'publicada'
                     AND (p.fecha_inicio IS NULL OR p.fecha_inicio <= date('now'))
                     AND (p.fecha_fin   IS NULL OR p.fecha_fin   >= date('now'))
                    THEN 1 ELSE 0 END AS promo_vigente
        FROM inventario i
        LEFT JOIN promociones p ON p.inventario_id = i.id
        ORDER BY i.id''')]


def vitrina():
    """Catálogo público: solo precios de promociones realmente publicadas y vigentes."""
    with conectar() as db:
        return [dict(r) for r in db.execute('SELECT * FROM v_catalogo_publico ORDER BY inventario_id')]


def sedes():
    with conectar() as db:
        return [dict(r) for r in db.execute(
            'SELECT id, codigo, nombre, direccion, ciudad, telefono FROM sedes WHERE activa=1 ORDER BY id')]


def respaldo():
    """Copia segura de la base (snapshot coherente con la API de backup de SQLite)."""
    destino = DB.with_name(DB.stem + '-' + time.strftime('%Y%m%d-%H%M%S') + '.sqlite3')
    with conectar() as origen, sqlite3.connect(destino) as copia:
        origen.backup(copia)
    return destino

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
    # P02: si aún no existe la base de trabajo pero sí la histórica, se rescata
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
        # Las vistas de precios (v_precios y v_catalogo_publico) se crean en
        # migraciones/0006_precio_venta.sql: ahí vive la ÚNICA regla de precio.
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
    """Aplica las migraciones pendientes después de guardar un respaldo coherente."""
    pendientes = migraciones_pendientes(db)
    if not pendientes:
        return []
    db.commit()
    copia = DB.with_suffix(DB.suffix + '.bak')
    with sqlite3.connect(copia) as destino:
        db.backup(destino)
    aplicadas = []
    for archivo in pendientes:
        db.executescript(archivo.read_text(encoding='utf-8'))
        db.execute('INSERT OR IGNORE INTO migraciones(nombre) VALUES(?)', (archivo.stem,))
        aplicadas.append(archivo.stem)
    return aplicadas


def catalogo():
    """Catálogo para la tabla interna de Promociones (incluye borradores, para revisión).

    P0-3: antes era INNER JOIN y escondía todo vehículo sin promoción.
    Se conservan los campos originales. precio_venta y promo_vigente salen de la
    vista v_precios (migración 0006): la oferta solo aplica si la promoción está
    publicada y vigente, y ese es el precio que se muestra y se cobra.
    """
    with conectar() as db:
        return [dict(r) for r in db.execute('''
        SELECT inventario_id, sku, nombre, categoria, propulsion,
               precio_base, existencias, moneda,
               COALESCE(titulo, '—') AS titulo, beneficio,
               COALESCE(precio_promocional, precio_base) AS precio_promocional,
               estado, fecha_inicio, fecha_fin,
               precio_venta, promo_vigente
        FROM v_precios
        ORDER BY inventario_id''')]


def vitrina():
    """Catálogo público: precio_venta y datos de la promoción solo si está publicada y vigente."""
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

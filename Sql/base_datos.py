from pathlib import Path
import sqlite3, json
ROOT = Path(__file__).resolve().parent
DB = ROOT / 'datos' / 'dasauto.sqlite3'

def conectar():
    db = sqlite3.connect(DB, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    return db

def iniciar():
    DB.parent.mkdir(exist_ok=True)
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
        if not db.execute("SELECT 1 FROM migraciones WHERE nombre='catalogo_inicial'").fetchone():
            for r in json.loads((ROOT/'catalogo_inicial.json').read_text(encoding='utf-8')):
                cur = db.execute('INSERT INTO inventario(sku,nombre,categoria,propulsion,precio_base) VALUES(?,?,?,?,?)', (r['sku'],r['nombre'],r['categoria'],r['propulsion'],r['precio']))
                db.execute('INSERT INTO promociones(inventario_id,titulo,beneficio,precio_promocional) VALUES(?,?,?,?)', (cur.lastrowid,r['titulo'],r['beneficio'],r['oferta']))
            db.execute("INSERT INTO migraciones VALUES('catalogo_inicial')")

def catalogo():
    with conectar() as db:
        return [dict(r) for r in db.execute('''SELECT i.sku,i.nombre,i.categoria,i.propulsion,
        i.precio_base,i.existencias,i.moneda,p.titulo,p.beneficio,p.precio_promocional,p.estado,
        p.fecha_inicio,p.fecha_fin FROM inventario i JOIN promociones p ON p.inventario_id=i.id ORDER BY i.id''')]

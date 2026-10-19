"""Mantenimiento de la base de datos de DasAuto (no toca páginas ni código).

Uso (desde la carpeta Sql/):

    python mantenimiento.py informe
    python mantenimiento.py optimizar
    python mantenimiento.py limpiar
    python mantenimiento.py respaldo --conservar 10
    python mantenimiento.py vacio
    python mantenimiento.py --db otra.sqlite3 informe

Qué hace cada uno:

  informe     Revisa integridad, claves foráneas, índices que faltan o sobran,
              reservas descuadradas, sesiones vencidas y tamaño de las tablas.
  optimizar   ANALYZE + PRAGMA optimize y vuelca el WAL al archivo principal.
  limpiar     Borra sesiones vencidas del panel y libera reservas vencidas de
              pedidos pendientes (devuelve el stock y lo anota en el kardex).
  respaldo    Copia coherente con la API de SQLite y rota los respaldos viejos.
  vacio       Compacta el archivo (VACUUM). Conviene cerrar el servidor antes.

Es seguro ejecutarlo con el servidor encendido salvo `vacio`, que reescribe el
archivo completo (SQLite lo permite, pero es mejor con el sitio detenido).
"""
import argparse, os, sqlite3, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
POR_DEFECTO = AQUI / 'datos' / 'dasauto.sqlite3'


def conectar(ruta):
    db = sqlite3.connect(ruta, timeout=15)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    db.execute('PRAGMA busy_timeout=15000')
    return db


def tamano(bytes_):
    for unidad in ('B', 'KB', 'MB', 'GB'):
        if bytes_ < 1024:
            return '%.1f %s' % (bytes_, unidad)
        bytes_ /= 1024
    return '%.1f TB' % bytes_


def informe(db, ruta):
    print('Base de datos:', ruta)
    print('  archivo:', tamano(os.path.getsize(ruta)))
    wal = Path(str(ruta) + '-wal')
    if wal.exists():
        print('  WAL pendiente:', tamano(os.path.getsize(wal)))

    print('\nIntegridad')
    print('  integrity_check:', db.execute('PRAGMA integrity_check').fetchone()[0])
    print('  quick_check:    ', db.execute('PRAGMA quick_check').fetchone()[0])
    claves = db.execute('PRAGMA foreign_key_check').fetchall()
    print('  claves foráneas:', 'ok' if not claves else '%d problema(s)' % len(claves))
    for fila in claves[:10]:
        print('    ', tuple(fila))
    print('  journal_mode:   ', db.execute('PRAGMA journal_mode').fetchone()[0])

    print('\nObjetos')
    etiquetas = {'table': 'tablas', 'view': 'vistas', 'index': 'índices', 'trigger': 'triggers'}
    for tipo, etiqueta in etiquetas.items():
        total = db.execute("SELECT COUNT(*) FROM sqlite_master WHERE type=? AND name NOT LIKE 'sqlite_%'",
                           (tipo,)).fetchone()[0]
        print('  %-10s %3d' % (etiqueta, total))

    print('\nRegistros por tabla')
    tablas = [r[0] for r in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    for tabla in tablas:
        n = db.execute('SELECT COUNT(*) FROM ' + tabla).fetchone()[0]
        print('  %-30s %6d' % (tabla, n))

    print('\nRevisiones')
    problemas = 0

    # Reservas activas de pedidos que no están pendientes
    malas = db.execute("""
        SELECT COUNT(*) FROM inventario_reservas r JOIN pedidos p ON p.id = r.pedido_id
         WHERE r.estado = 'activa' AND p.estado <> 'pendiente'""").fetchone()[0]
    print('  reservas activas de pedidos no pendientes:', malas)
    problemas += malas

    # Reservas huérfanas (sin pedido)
    huerfanas = db.execute("""
        SELECT COUNT(*) FROM inventario_reservas r
         WHERE r.pedido_id IS NOT NULL AND NOT EXISTS (SELECT 1 FROM pedidos p WHERE p.id = r.pedido_id)""").fetchone()[0]
    print('  reservas sin pedido:', huerfanas)
    problemas += huerfanas

    # Existencias negativas
    negativas = db.execute('SELECT COUNT(*) FROM inventario WHERE existencias < 0').fetchone()[0]
    print('  vehículos con existencias negativas:', negativas)
    problemas += negativas

    # Vehículos sin ficha
    sin_ficha = db.execute("""
        SELECT COUNT(*) FROM inventario i
         WHERE NOT EXISTS (SELECT 1 FROM inventario_ficha f WHERE f.inventario_id = i.id)""").fetchone()[0]
    print('  vehículos sin ficha:', sin_ficha)

    # Kardex con saldo distinto al actual (solo el último movimiento de cada uno)
    descuadres = db.execute("""
        SELECT COUNT(*) FROM inventario i
         WHERE i.existencias IS NOT NULL
           AND EXISTS (SELECT 1 FROM inventario_movimientos m
                        WHERE m.inventario_id = i.id AND m.saldo_final IS NOT NULL
                          AND m.id = (SELECT MAX(id) FROM inventario_movimientos
                                       WHERE inventario_id = i.id AND saldo_final IS NOT NULL)
                          AND m.saldo_final <> i.existencias)""").fetchone()[0]
    print('  vehículos cuyo último saldo del kardex no coincide:', descuadres)
    problemas += descuadres

    sesiones = db.execute("SELECT COUNT(*) FROM admin_sesiones WHERE expira_en <= datetime('now','localtime')").fetchone()[0]
    reservas_vencidas = db.execute("""
        SELECT COUNT(*) FROM inventario_reservas r JOIN pedidos p ON p.id = r.pedido_id
         WHERE r.estado = 'activa' AND p.estado = 'pendiente'
           AND r.expira_en IS NOT NULL AND r.expira_en < datetime('now','localtime')""").fetchone()[0]
    print('  sesiones del panel vencidas:', sesiones)
    print('  reservas vencidas por liberar:', reservas_vencidas)

    print('\nÍndices duplicados (mismo nombre de columna en la misma tabla)')
    porTabla = {}
    for fila in db.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' AND sql IS NOT NULL"):
        columnas = fila['sql'].split('(', 1)[1].rsplit(')', 1)[0].strip().lower()
        porTabla.setdefault((fila['tbl_name'], columnas), []).append(fila['name'])
    duplicados = {k: v for k, v in porTabla.items() if len(v) > 1}
    if not duplicados:
        print('  ninguno')
    else:
        for (tabla, columnas), nombres in duplicados.items():
            print('  %s (%s): %s' % (tabla, columnas, ', '.join(nombres)))

    print('\nResultado:', 'sin problemas' if not problemas else '%d problema(s) para revisar' % problemas)
    return 1 if problemas else 0


def optimizar(db):
    db.execute('ANALYZE')
    db.execute('PRAGMA optimize')
    resultado = db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    db.commit()
    print('ANALYZE y optimizar: listo.')
    print('WAL volcado al archivo principal:', tuple(resultado))


def limpiar(db):
    db.execute('BEGIN IMMEDIATE')

    sesiones = db.execute("DELETE FROM admin_sesiones WHERE expira_en <= datetime('now','localtime')").rowcount

    reservas = db.execute("""
        SELECT r.id, r.inventario_id, r.cantidad, p.radicado
          FROM inventario_reservas r JOIN pedidos p ON p.id = r.pedido_id
         WHERE r.estado = 'activa' AND p.estado = 'pendiente'
           AND r.expira_en IS NOT NULL AND r.expira_en < datetime('now','localtime')""").fetchall()
    for reserva in reservas:
        db.execute('UPDATE inventario SET existencias = existencias + ? WHERE id = ? AND existencias IS NOT NULL',
                   (reserva['cantidad'], reserva['inventario_id']))
        saldo = db.execute('SELECT existencias FROM inventario WHERE id=?',
                           (reserva['inventario_id'],)).fetchone()
        db.execute("""INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
                      VALUES(?, 'entrada', ?, ?, 'Reserva vencida', ?)""",
                   (reserva['inventario_id'], reserva['cantidad'],
                    saldo['existencias'] if saldo else None, reserva['radicado']))
        db.execute("UPDATE inventario_reservas SET estado='vencida' WHERE id=?", (reserva['id'],))

    db.commit()
    print('Sesiones del panel borradas:', sesiones)
    print('Reservas vencidas liberadas:', len(reservas))
    for reserva in reservas:
        print('  %s · %d unidad(es) devuelta(s)' % (reserva['radicado'], reserva['cantidad']))


def respaldo(ruta, conservar):
    destino = Path(str(ruta).rsplit('.', 1)[0] + '-' + time.strftime('%Y%m%d-%H%M%S') + '.sqlite3')
    with conectar(ruta) as origen, sqlite3.connect(destino) as copia:
        origen.backup(copia)
    print('Respaldo creado:', destino, '(%s)' % tamano(os.path.getsize(destino)))

    if conservar > 0:
        # Solo los respaldos de esta misma base, del más viejo al más nuevo.
        patron = Path(str(ruta).rsplit('.', 1)[0] + '-*.sqlite3').name
        anteriores = [p for p in sorted(destino.parent.glob(patron)) if p != destino]
        sobrantes = anteriores[:max(0, len(anteriores) + 1 - conservar)]
        for viejo in sobrantes:
            viejo.unlink()
            print('Respaldo antiguo borrado:', viejo.name)
        conservados = destino.parent.glob(patron)
        print('Respaldos conservados: %d' % len(list(conservados)))
    return 0


def vacio(db, ruta):
    pendientes = db.execute('PRAGMA wal_checkpoint(TRUNCATE)').fetchone()
    db.execute('VACUUM')
    db.commit()
    print('VACUUM terminado. WAL:', tuple(pendientes))
    print('Tamaño final:', tamano(os.path.getsize(ruta)))


def main():
    p = argparse.ArgumentParser(description='Mantenimiento de la base de DasAuto')
    p.add_argument('accion', nargs='?', default='informe',
                   choices=['informe', 'optimizar', 'limpiar', 'respaldo', 'vacio'])
    p.add_argument('--db', default=str(POR_DEFECTO), help='Ruta a la base (por defecto Sql/datos/dasauto.sqlite3)')
    p.add_argument('--conservar', type=int, default=10, help='Respaldos a conservar (0 = todos)')
    args = p.parse_args()

    ruta = Path(args.db).expanduser().resolve()
    if not ruta.exists():
        sys.exit('No existe la base de datos: %s' % ruta)

    if args.accion == 'respaldo':
        return respaldo(ruta, args.conservar)

    with conectar(ruta) as db:
        if args.accion == 'informe':
            return informe(db, ruta)
        if args.accion == 'optimizar':
            return optimizar(db) or 0
        if args.accion == 'limpiar':
            return limpiar(db) or 0
        return vacio(db, ruta) or 0


if __name__ == '__main__':
    sys.exit(main())

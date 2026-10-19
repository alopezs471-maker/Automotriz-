"""Aplicador de migraciones SQL para DasAuto (solo aditivo).

Uso típico (desde la carpeta Sql/):

    python migraciones/aplicar.py --db dasauto.sqlite3
    python migraciones/aplicar.py --db dasauto.sqlite3 --revision   # solo muestra el plan

Qué hace:
  * Ejecuta los archivos .sql de esta carpeta en orden numérico.
  * Salta los que ya están anotados en la tabla `migraciones`.
  * Cada archivo corre en una transacción: si falla, no queda a medias.
  * Anota el nombre del archivo en `migraciones` (INSERTA una fila; no borra
    ni modifica nada de lo que ya existe).

Importante: apunta --db al archivo que REALMENTE usa tu proyecto.
Ojo: base_datos.py busca la base en Sql/datos/dasauto.sqlite3, pero el archivo
que hoy tiene los 32 vehículos está en Sql/dasauto.sqlite3. Revisa cuál quieres
usar antes de aplicar (ver PROPUESTA_BASE_DATOS.md, hallazgo P0-2).
"""
import argparse, sqlite3, sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent


def pendientes(db):
    aplicadas = {r[0] for r in db.execute('SELECT nombre FROM migraciones')}
    return [p for p in sorted(AQUI.glob('*.sql')) if p.stem not in aplicadas]


def main():
    p = argparse.ArgumentParser(description='Aplica migraciones SQL pendientes.')
    p.add_argument('--db', required=True, help='Ruta al archivo .sqlite3')
    p.add_argument('--revision', action='store_true', help='Muestra el plan y sale.')
    args = p.parse_args()

    ruta = Path(args.db).expanduser().resolve()
    if not ruta.exists():
        sys.exit(f'No existe la base de datos: {ruta}')

    copia = ruta.with_suffix(ruta.suffix + '.bak')
    db = sqlite3.connect(ruta)
    db.execute('PRAGMA foreign_keys=ON')
    lista = pendientes(db)

    if not lista:
        print('No hay migraciones pendientes.')
        return
    print('Base:', ruta)
    for f in lista:
        print('  aplicaría', f.name)

    if args.revision:
        db.close()
        return

    import shutil
    shutil.copy2(ruta, copia)
    print('Respaldo creado en', copia.name)

    for f in lista:
        sql = f.read_text(encoding='utf-8')
        try:
            db.executescript(sql)                       # autocommit: cada script es atómico
            db.execute('INSERT OR IGNORE INTO migraciones(nombre) VALUES(?)', (f.stem,))
            db.commit()
            print('OK  ', f.name)
        except sqlite3.Error as e:
            db.rollback()
            db.close()
            sys.exit(f'Falló {f.name}: {e}\nLa base quedó como estaba; respaldo en {copia}')

    print('Integridad:', db.execute('PRAGMA integrity_check').fetchone()[0])
    db.close()


if __name__ == '__main__':
    main()

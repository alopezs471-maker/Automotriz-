"""Cuentas del panel de administración, por terminal.

Uso:
    python admin.py usuarios
    python admin.py crear <usuario> "<nombre>" <rol>     (pide la clave)
    python admin.py clave <usuario>                      (pide la clave)
    python admin.py activar <usuario> si|no

La primera cuenta se crea sola la primera vez que arranca servidor.py; su clave
queda en Sql/datos/clave_admin_inicial.txt (o en DASAUTO_ADMIN_CLAVE).
"""
import argparse, getpass, sys
from base_datos import iniciar, conectar
import api_extra

p = argparse.ArgumentParser(description='Cuentas del panel de DasAuto')
s = p.add_subparsers(dest='accion', required=True)

s.add_parser('usuarios')
a = s.add_parser('crear'); a.add_argument('usuario'); a.add_argument('nombre')
a.add_argument('rol', choices=api_extra.ROLES)
a = s.add_parser('clave'); a.add_argument('usuario')
a = s.add_parser('activar'); a.add_argument('usuario'); a.add_argument('estado', choices=['si', 'no'])
args = p.parse_args()


def pedir_clave():
    clave = getpass.getpass('Clave (mínimo 8 caracteres): ')
    if len(clave) < 8:
        sys.exit('La clave debe tener al menos 8 caracteres.')
    if clave != getpass.getpass('Repite la clave: '):
        sys.exit('Las claves no coinciden.')
    return clave


iniciar()

with conectar() as db:
    if args.accion == 'usuarios':
        filas = db.execute('''SELECT usuario, nombre, rol, activo, ultimo_acceso
                                FROM admin_usuarios ORDER BY usuario''').fetchall()
        if not filas:
            print('Todavía no hay cuentas. Arranca servidor.py una vez o usa "crear".')
        for fila in filas:
            print('%-20s %-28s %-9s %-9s %s' % (
                fila['usuario'], fila['nombre'], fila['rol'],
                'activo' if fila['activo'] else 'inactivo', fila['ultimo_acceso'] or 'nunca'))

    elif args.accion == 'crear':
        usuario = args.usuario.lower()
        if not api_extra.USUARIO.fullmatch(usuario):
            sys.exit('Usuario inválido: 3 a 30 caracteres (letras, números, punto o guion).')
        if db.execute('SELECT 1 FROM admin_usuarios WHERE usuario=?', (usuario,)).fetchone():
            sys.exit('Ese usuario ya existe.')
        clave = pedir_clave()
        db.execute('INSERT INTO admin_usuarios(usuario,nombre,clave_hash,rol) VALUES(?,?,?,?)',
                   (usuario, args.nombre, api_extra.cifrar_clave(clave), args.rol))
        print('Usuario %s creado con rol %s.' % (usuario, args.rol))

    elif args.accion == 'clave':
        usuario = args.usuario.lower()
        fila = db.execute('SELECT id FROM admin_usuarios WHERE usuario=?', (usuario,)).fetchone()
        if not fila:
            sys.exit('Usuario no encontrado.')
        clave = pedir_clave()
        db.execute('UPDATE admin_usuarios SET clave_hash=? WHERE id=?',
                   (api_extra.cifrar_clave(clave), fila['id']))
        db.execute('DELETE FROM admin_sesiones WHERE usuario_id=?', (fila['id'],))
        print('Clave actualizada. Se cerraron las sesiones abiertas de %s.' % usuario)

    else:  # activar
        usuario = args.usuario.lower()
        activo = 1 if args.estado == 'si' else 0
        cur = db.execute('UPDATE admin_usuarios SET activo=? WHERE usuario=?', (activo, usuario))
        if not cur.rowcount:
            sys.exit('Usuario no encontrado.')
        if not activo:
            db.execute('DELETE FROM admin_sesiones WHERE usuario_id=(SELECT id FROM admin_usuarios WHERE usuario=?)',
                       (usuario,))
        print('Usuario %s %s.' % (usuario, 'activado' if activo else 'desactivado'))

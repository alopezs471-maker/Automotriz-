"""Servidor de desarrollo local. Python 3.10+, sin dependencias externas.

Correcciones aplicadas sobre la versión original:
  P0-1  PUBLIC apuntaba a Sql/public (no existe) -> ahora sirve la raíz del repo.
  P0-2  La base se unificó en Sql/datos/ y se rescata la histórica (ver base_datos.py).
  P0-3  El catálogo ya no esconde los vehículos sin promoción (LEFT JOIN).
  P1-2  Los pedidos cobran precio_venta (vista v_precios): la oferta solo se
        aplica si la promoción está publicada y vigente.
  P1-8  Límite de envíos por IP y bloqueo de archivos privados (.sqlite3, .py, .git).
  P2-1  Endpoints nuevos: citas de taller, pruebas de manejo, contacto, seguros y pedidos.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlsplit, unquote
from pathlib import Path
import argparse, json, os, secrets, re, sqlite3, uuid, time
from collections import defaultdict, deque
from base_datos import ROOT, DB, iniciar, conectar, catalogo, vitrina, sedes

PUBLIC = ROOT.parent                 # P0-1: el sitio vive en la raíz del repositorio
TOKEN = secrets.token_urlsafe(32)

# Nunca se sirven por HTTP: la base de datos, el código, los respaldos ni el .git.
PRIVADO = re.compile(r'(^\.|/\.|(^|/)Sql/|\.(sqlite3|sqlite3-wal|sqlite3-shm|bak|py|md|json|ini|bat)$)', re.I)

EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+')
FECHA = re.compile(r'\d{4}-\d{2}-\d{2}')
HORA = re.compile(r'([01]\d|2[0-3]):[0-5]\d')

SERVICIOS = ('mantenimiento', 'diagnostico', 'frenos', 'llantas', 'bateria',
             'aire_acondicionado', 'pintura', 'garantia', 'otro')
ASUNTOS = ('ventas', 'prueba', 'taller', 'financiacion', 'seguros', 'otro')
COBERTURAS = ('responsabilidad', 'basica', 'estandar', 'todo_riesgo')

# Se pueden ajustar por variable de entorno sin editar el archivo.
VENTANA = 600                                                    # segundos
MAX_ENVIOS = int(os.environ.get('DASAUTO_MAX_ENVIOS', 8))   # envíos por IP
intentos = defaultdict(deque)


def hoy():
    return time.strftime('%Y-%m-%d')


def radicar(prefijo):
    return '%s-%s-%s' % (prefijo, time.strftime('%Y'), uuid.uuid4().hex[:12].upper())


def id_usuario(db, datos):
    """Usuarios son fichas de contacto, no cuentas autenticadas."""
    db.execute('INSERT OR IGNORE INTO usuarios(nombre,documento,email,telefono) VALUES(?,?,?,?)',
               tuple(datos[k] for k in ('nombre', 'documento', 'email', 'telefono')))
    return db.execute('SELECT id FROM usuarios WHERE email=?', (datos['email'],)).fetchone()['id']


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def list_directory(self, path):
        self.send_error(403, 'Listado de carpetas deshabilitado')

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'same-origin')
        super().end_headers()

    def json(self, status, data):
        payload = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    # ------------------------- utilidades de validación -------------------------
    def leer(self, limites, opcionales=()):
        """Lee y valida el cuerpo JSON. `limites` fija el largo máximo de cada campo."""
        longitud = int(self.headers.get('Content-Length', '0'))
        if not 0 < longitud <= 24000:
            raise ValueError('Solicitud demasiado grande o vacía.')
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            raise ValueError('Se requiere JSON.')
        try:
            datos = json.loads(self.rfile.read(longitud))
        except ValueError:
            raise ValueError('Formato inválido.')
        if not isinstance(datos, dict):
            raise ValueError('Formato inválido.')
        for campo, limite in limites.items():
            valor = datos.get(campo)
            if valor is None and campo in opcionales:
                datos[campo] = None
                continue
            if not isinstance(valor, str) or not 1 <= len(valor.strip()) <= limite:
                raise ValueError('Revisa el campo ' + campo + '.')
            datos[campo] = valor.strip()
        if 'email' in limites:
            datos['email'] = datos['email'].lower()
            if not EMAIL.fullmatch(datos['email']):
                raise ValueError('Correo electrónico inválido.')
        if datos.get('terminos') is not True:
            raise ValueError('Debes aceptar el tratamiento de datos.')
        # La clave identifica reintentos; no es una identidad de usuario.
        try:
            uuid.UUID(datos['envio_id'])
        except (ValueError, AttributeError, TypeError):
            raise ValueError('El formulario no es válido. Recarga la página.')
        return datos

    def fecha_futura(self, valor):
        if not FECHA.fullmatch(valor):
            raise ValueError('La fecha debe tener formato AAAA-MM-DD.')
        if valor < hoy():
            raise ValueError('La fecha no puede ser anterior a hoy.')
        return valor

    def hora_valida(self, valor):
        if not HORA.fullmatch(valor):
            raise ValueError('La hora debe tener formato HH:MM.')
        return valor

    def ip(self):
        return self.client_address[0]

    def permitido(self):
        ahora = time.monotonic()
        cola = intentos[self.ip()]
        while cola and ahora - cola[0] > VENTANA:
            cola.popleft()
        if len(cola) >= MAX_ENVIOS:
            return False
        cola.append(ahora)
        return True

    # ------------------------------- inserciones -------------------------------
    def guardar_pqrs(self, db, datos):
        previo = db.execute('SELECT radicado FROM pqrs WHERE envio_id=?', (datos['envio_id'],)).fetchone()
        if previo:
            return previo['radicado']
        if datos['tipo_pqrs'] not in ('peticion', 'queja', 'reclamo', 'sugerencia'):
            raise ValueError('Tipo de solicitud inválido.')
        uid = id_usuario(db, datos)
        radicado = radicar('PQRS')
        db.execute('''INSERT INTO pqrs(radicado,envio_id,usuario_id,nombre,documento,email,telefono,tipo_pqrs,descripcion,acepta_tratamiento)
        VALUES(?,?,?,?,?,?,?,?,?,1)''',
            (radicado, datos['envio_id'], uid,
             *(datos[k] for k in ('nombre', 'documento', 'email', 'telefono', 'tipo_pqrs', 'descripcion'))))
        db.execute('INSERT INTO pqrs_eventos(pqrs_id,estado,nota,responsable) VALUES(?,\'radicada\',\'Radicado automáticamente desde la web\',\'web\')',
                   (db.execute('SELECT id FROM pqrs WHERE radicado=?', (radicado,)).fetchone()['id'],))
        return radicado

    def guardar_cita(self, db, datos):
        previo = db.execute('SELECT radicado FROM citas_taller WHERE envio_id=?', (datos['envio_id'],)).fetchone()
        if previo:
            return previo['radicado']
        if datos['servicio'] not in SERVICIOS:
            raise ValueError('Servicio no disponible.')
        datos['fecha_programada'] = self.fecha_futura(datos['fecha_programada'])
        datos['hora_programada'] = self.hora_valida(datos['hora_programada'])
        uid = id_usuario(db, datos)
        radicado = radicar('T')
        db.execute('''INSERT INTO citas_taller(radicado,envio_id,usuario_id,nombre,documento,email,telefono,
        placa,servicio,descripcion,fecha_programada,hora_programada,acepta_tratamiento)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)''',
            (radicado, datos['envio_id'], uid,
             *(datos[k] for k in ('nombre', 'documento', 'email', 'telefono')),
             datos.get('placa'), datos['servicio'], datos.get('descripcion'),
             datos['fecha_programada'], datos['hora_programada']))
        return radicado

    def guardar_prueba(self, db, datos):
        previo = db.execute('SELECT radicado FROM pruebas_manejo WHERE envio_id=?', (datos['envio_id'],)).fetchone()
        if previo:
            return previo['radicado']
        datos['fecha_programada'] = self.fecha_futura(datos['fecha_programada'])
        datos['hora_programada'] = self.hora_valida(datos['hora_programada'])
        uid = id_usuario(db, datos) if datos.get('documento') else None
        sede_id, sede_texto = None, (datos.get('sede') or None)
        if sede_texto:
            fila = db.execute('SELECT id FROM sedes WHERE nombre=? OR nombre LIKE ?',
                              (sede_texto, sede_texto.split(' (')[0] + '%')).fetchone()
            sede_id = fila['id'] if fila else None
        radicado = radicar('PM')
        db.execute('''INSERT INTO pruebas_manejo(radicado,envio_id,usuario_id,sede_id,nombre,apellido,documento,email,telefono,
        modelo_interes,sede_texto,fecha_programada,hora_programada,acepta_tratamiento)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,1)''',
            (radicado, datos['envio_id'], uid, sede_id,
             datos['nombre'], datos['apellido'], datos.get('documento'),
             datos['email'], datos['telefono'], datos['modelo_interes'],
             sede_texto, datos['fecha_programada'], datos['hora_programada']))
        return radicado

    def guardar_contacto(self, db, datos):
        if db.execute('SELECT 1 FROM contactos WHERE envio_id=?', (datos['envio_id'],)).fetchone():
            return None
        if datos['asunto'] not in ASUNTOS:
            raise ValueError('Asunto no disponible.')
        db.execute('''INSERT INTO contactos(envio_id,nombre,email,telefono,asunto,mensaje,acepta_tratamiento)
        VALUES(?,?,?,?,?,?,1)''',
            (datos['envio_id'],
             *(datos[k] for k in ('nombre', 'email', 'telefono', 'asunto', 'mensaje'))))
        return None

    def guardar_seguro(self, db, datos):
        if db.execute('SELECT 1 FROM cotizaciones_seguro WHERE envio_id=?', (datos['envio_id'],)).fetchone():
            return None
        if datos['tipo_cobertura'] not in COBERTURAS:
            raise ValueError('Cobertura no disponible.')
        db.execute('''INSERT INTO cotizaciones_seguro(envio_id,nombre,email,telefono,tipo_vehiculo,tipo_cobertura,valor_asegurado)
        VALUES(?,?,?,?,?,?,?)''',
            (datos['envio_id'],
             *(datos[k] for k in ('nombre', 'email', 'telefono', 'tipo_vehiculo', 'tipo_cobertura')),
             datos.get('valor_asegurado') or 0))
        return None

    def guardar_pedido(self, db, datos):
        previo = db.execute('SELECT radicado FROM pedidos WHERE envio_id=?', (datos['envio_id'],)).fetchone()
        if previo:
            return previo['radicado']
        items = datos.get('items')
        if not isinstance(items, list) or not 1 <= len(items) <= 30:
            raise ValueError('El pedido debe tener entre 1 y 30 vehículos.')
        uid = id_usuario(db, datos)
        radicado = radicar('PED')
        detalle, total = [], 0
        for item in items:
            if not isinstance(item, dict):
                raise ValueError('Formato de pedido inválido.')
            sku = str(item.get('sku', '')).strip().lower()
            try:
                cantidad = int(item.get('cantidad', 1))
            except (TypeError, ValueError):
                raise ValueError('Cantidad inválida.')
            if not 1 <= cantidad <= 99:
                raise ValueError('La cantidad debe estar entre 1 y 99.')
            # Se cobra precio_venta (vista v_precios): la oferta solo si la promoción
            # está publicada y vigente. Nunca se usa el precio que manda el navegador.
            vehiculo = db.execute('''SELECT inventario_id AS id, nombre, precio_venta AS precio
                   FROM v_precios WHERE sku=?''', (sku,)).fetchone()
            if not vehiculo:
                raise ValueError('Vehículo no disponible: ' + sku + '.')
            detalle.append((vehiculo['id'], sku, vehiculo['nombre'], cantidad, vehiculo['precio']))
            total += vehiculo['precio'] * cantidad
        db.execute('''INSERT INTO pedidos(radicado,envio_id,usuario_id,nombre,documento,email,telefono,subtotal,total)
        VALUES(?,?,?,?,?,?,?,?,?)''',
            (radicado, datos['envio_id'], uid,
             *(datos[k] for k in ('nombre', 'documento', 'email', 'telefono')), total, total))
        pid = db.execute('SELECT id FROM pedidos WHERE radicado=?', (radicado,)).fetchone()['id']
        for inventario_id, sku, nombre, cantidad, precio in detalle:
            db.execute('INSERT INTO pedidos_items(pedido_id,inventario_id,sku,nombre,cantidad,precio_unitario) VALUES(?,?,?,?,?,?)',
                       (pid, inventario_id, sku, nombre, cantidad, precio))
            db.execute('INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,motivo,referencia) VALUES(?,?,?,?,?)',
                       (inventario_id, 'salida', -cantidad, 'Pedido web', radicado))
        return radicado

    # --------------------------------- rutas ----------------------------------
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/api/sesion':
            return self.json(200, {'token': TOKEN})
        if path == '/api/promociones':
            return self.json(200, {'promociones': catalogo()})
        if path == '/api/catalogo':
            return self.json(200, {'vehiculos': vitrina()})
        if path == '/api/sedes':
            try:
                return self.json(200, {'sedes': sedes()})
            except sqlite3.Error:
                return self.json(200, {'sedes': []})
        if path.startswith('/api/'):
            return self.json(404, {'error': 'Ruta no disponible.'})
        # P1-8: nada de código, base de datos, respaldos ni .git por HTTP.
        if PRIVADO.search(path):
            return self.json(403, {'error': 'Acceso denegado.'})
        resolved = (PUBLIC / unquote(path).lstrip('/')).resolve()
        if not resolved.is_relative_to(PUBLIC.resolve()):
            return self.json(403, {'error': 'Acceso denegado.'})
        return super().do_GET()

    RUTAS = {
        '/api/pqrs': (
            'guardar_pqrs',
            {'nombre': 150, 'documento': 30, 'email': 190, 'telefono': 30,
             'tipo_pqrs': 20, 'descripcion': 10000, 'envio_id': 80},
        ),
        '/api/citas-taller': (
            'guardar_cita',
            {'nombre': 150, 'documento': 30, 'email': 190, 'telefono': 30,
             'servicio': 30, 'fecha_programada': 10, 'hora_programada': 5, 'envio_id': 80},
            ('placa', 'descripcion'),
        ),
        '/api/pruebas-manejo': (
            'guardar_prueba',
            {'nombre': 150, 'apellido': 150, 'documento': 30, 'email': 190, 'telefono': 30,
             'modelo_interes': 120, 'fecha_programada': 10, 'hora_programada': 5, 'envio_id': 80},
            ('documento', 'sede'),
        ),
        '/api/contacto': (
            'guardar_contacto',
            {'nombre': 150, 'email': 190, 'telefono': 30, 'asunto': 20, 'mensaje': 4000, 'envio_id': 80},
            (),
        ),
        '/api/seguros': (
            'guardar_seguro',
            {'nombre': 150, 'email': 190, 'telefono': 30, 'tipo_vehiculo': 40,
             'tipo_cobertura': 20, 'envio_id': 80},
            (),
        ),
        '/api/pedidos': (
            'guardar_pedido',
            {'nombre': 150, 'documento': 30, 'email': 190, 'telefono': 30, 'envio_id': 80},
            (),
        ),
    }

    def do_POST(self):
        # No CORS. Solo peticiones del mismo sitio con token entregado por el servidor.
        if not secrets.compare_digest(self.headers.get('X-CSRF-Token', ''), TOKEN):
            return self.json(403, {'error': 'Sesión inválida. Recarga la página.'})
        ruta = urlsplit(self.path).path
        if ruta not in self.RUTAS:
            return self.json(404, {'error': 'Ruta no disponible.'})
        if not self.permitido():
            return self.json(429, {'error': 'Demasiados envíos desde tu conexión. Espera unos minutos.'})
        metodo, limites, *resto = self.RUTAS[ruta]
        opcionales = resto[0] if resto else ()
        try:
            datos = self.leer(limites, opcionales)
            with conectar() as db:
                db.execute('BEGIN IMMEDIATE')
                radicado = getattr(self, metodo)(db, datos)
            return self.json(201, {'radicado': radicado} if radicado else {'ok': True})
        except ValueError as e:
            return self.json(400, {'error': str(e) or 'Revisa los datos del formulario.'})
        except (KeyError, TypeError, UnicodeDecodeError):
            return self.json(400, {'error': 'Faltan datos del formulario. Recárgalo e inténtalo de nuevo.'})
        except sqlite3.Error:
            return self.json(500, {'error': 'No fue posible guardar la solicitud. Reintenta más tarde.'})


if __name__ == '__main__':
    args = argparse.ArgumentParser(description='DasAuto local')
    args.add_argument('--host', default='127.0.0.1')
    args.add_argument('--port', default=8000, type=int)
    opt = args.parse_args()
    iniciar()
    print(f'DasAuto: http://localhost:{opt.port}/index.html', flush=True)
    print(f'Base de datos: {DB}', flush=True)
    print('Detener: Ctrl+C. Respaldo manual: python gestionar.py respaldo', flush=True)
    ThreadingHTTPServer((opt.host, opt.port), Handler).serve_forever()

"""Funciones nuevas de DasAuto — todas aditivas.

Aquí viven los servicios que no existían:

  · Financiación     cotizador con tasas guardadas en la base
  · Ficha            ficha técnica, precio e historial por vehículo
  · Inventario real  control de existencias, kardex y reservas de 48 h
  · Agenda           cupos por hora con control de sobrecupo
  · Panel            acceso con usuario y clave, sesiones y auditoría

`servidor.py` solo delega las rutas que empiezan por los prefijos de abajo;
las rutas anteriores siguen funcionando exactamente igual.
"""
from base_datos import DB, conectar
from collections import defaultdict, deque
from datetime import datetime, timedelta
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit
import hashlib, hmac, json, math, os, re, secrets, sqlite3, time, uuid

COOKIE = 'DASAUTO_PANEL'
SESION_HORAS = 8
ITERACIONES = 240_000

HORAS = ('08:00', '09:00', '10:00', '11:00', '12:00',
         '14:00', '15:00', '16:00', '17:00')
CUPO_DEFECTO = 2
DIAS_AGENDA = 60
SERVICIOS = ('mantenimiento', 'diagnostico', 'frenos', 'llantas', 'bateria',
             'aire_acondicionado', 'pintura', 'garantia', 'otro')
ESTADOS_CITA = ('solicitada', 'confirmada', 'en_taller', 'finalizada', 'cancelada', 'no_show')
ESTADOS_PEDIDO = ('pendiente', 'confirmado', 'facturado', 'cancelado')
ESTADOS_COTIZACION = ('simulada', 'enviada', 'aprobada', 'rechazada')
ROLES = ('admin', 'ventas', 'taller', 'consulta')

FECHA = re.compile(r'\d{4}-\d{2}-\d{2}')
HORA = re.compile(r'([01]\d|2[0-3]):[0-5]\d')
EMAIL = re.compile(r'[^\s@]+@[^\s@]+\.[^\s@]+')
USUARIO = re.compile(r'[a-z0-9._-]{3,30}')

_intentos = defaultdict(deque)


class ErrorValidacion(ValueError):
    """Error que se devuelve al navegador como 400 con un mensaje claro."""


class LimiteExcedido(ErrorValidacion):
    """Demasiados intentos: se responde 429."""


# --------------------------------------------------------------- utilidades
def hoy():
    return time.strftime('%Y-%m-%d')


def ahora():
    return time.strftime('%Y-%m-%d %H:%M:%S')


def fecha_mas(dias, desde=None):
    base = datetime.strptime(desde or hoy(), '%Y-%m-%d')
    return (base + timedelta(days=dias)).strftime('%Y-%m-%d')


def limitar(llave, maximo, ventana):
    """Límite sencillo por IP para los formularios públicos y el ingreso."""
    instante = time.monotonic()
    cola = _intentos[llave]
    while cola and instante - cola[0] > ventana:
        cola.popleft()
    if len(cola) >= maximo:
        raise LimiteExcedido('Demasiados intentos desde tu conexión. Espera unos minutos.')
    cola.append(instante)


def responder(h, estado, datos, cabeceras=()):
    payload = json.dumps(datos, ensure_ascii=False).encode()
    h.send_response(estado)
    h.send_header('Content-Type', 'application/json; charset=utf-8')
    h.send_header('Cache-Control', 'no-store')
    h.send_header('Content-Length', str(len(payload)))
    for cabecera in cabeceras:
        h.send_header('Set-Cookie', cabecera)
    h.end_headers()
    h.wfile.write(payload)


def leer_json(h, limite=24000):
    try:
        longitud = int(h.headers.get('Content-Length', '0'))
    except ValueError:
        raise ErrorValidacion('Solicitud inválida.')
    if not 0 < longitud <= limite:
        raise ErrorValidacion('Solicitud demasiado grande o vacía.')
    if h.headers.get('Content-Type', '').split(';')[0] != 'application/json':
        raise ErrorValidacion('Se requiere JSON.')
    try:
        datos = json.loads(h.rfile.read(longitud))
    except ValueError:
        raise ErrorValidacion('Formato inválido.')
    if not isinstance(datos, dict):
        raise ErrorValidacion('Formato inválido.')
    return datos


def texto(datos, campo, maximo, obligatorio=True, defecto=''):
    valor = datos.get(campo, defecto)
    if valor is None:
        valor = ''
    if not isinstance(valor, str):
        raise ErrorValidacion('Revisa el campo ' + campo + '.')
    valor = valor.strip()
    if obligatorio and not valor:
        raise ErrorValidacion('Falta el campo ' + campo + '.')
    if len(valor) > maximo:
        raise ErrorValidacion('El campo ' + campo + ' es demasiado largo.')
    return valor


def entero(datos, campo, minimo, maximo, obligatorio=True):
    valor = datos.get(campo)
    if valor is None or valor == '':
        if obligatorio:
            raise ErrorValidacion('Falta el campo ' + campo + '.')
        return None
    try:
        valor = int(valor)
    except (TypeError, ValueError):
        raise ErrorValidacion('El campo ' + campo + ' debe ser un número entero.')
    if not minimo <= valor <= maximo:
        raise ErrorValidacion('El campo %s debe estar entre %d y %d.' % (campo, minimo, maximo))
    return valor


def correo(datos, obligatorio=True):
    valor = texto(datos, 'email', 190, obligatorio).lower()
    if valor and not EMAIL.fullmatch(valor):
        raise ErrorValidacion('Correo electrónico inválido.')
    return valor


def identificador(datos):
    """Clave de reintento del formulario: evita duplicados por doble clic."""
    try:
        uuid.UUID(str(datos.get('envio_id')))
    except (ValueError, AttributeError, TypeError):
        raise ErrorValidacion('El formulario no es válido. Recarga la página.')
    return str(datos['envio_id'])


def terminos(datos):
    if datos.get('terminos') is not True:
        raise ErrorValidacion('Debes autorizar el tratamiento de datos.')


def fecha_valida(valor, permitir_pasado=False):
    if not valor or not FECHA.fullmatch(valor):
        raise ErrorValidacion('La fecha debe tener formato AAAA-MM-DD.')
    try:
        datetime.strptime(valor, '%Y-%m-%d')
    except ValueError:
        raise ErrorValidacion('La fecha no existe en el calendario.')
    if not permitir_pasado and valor < hoy():
        raise ErrorValidacion('La fecha no puede ser anterior a hoy.')
    if valor > fecha_mas(DIAS_AGENDA):
        raise ErrorValidacion('Solo se puede agendar hasta %d días adelante.' % DIAS_AGENDA)
    return valor


def asegurar_usuario(db, nombre, documento, email, telefono):
    db.execute('INSERT OR IGNORE INTO usuarios(nombre,documento,email,telefono) VALUES(?,?,?,?)',
               (nombre, documento or '', email, telefono or ''))
    return db.execute('SELECT id FROM usuarios WHERE email=?', (email,)).fetchone()['id']


# ------------------------------------------------------------ claves/sesiones
def cifrar_clave(clave):
    sal = secrets.token_hex(16)
    derivada = hashlib.pbkdf2_hmac('sha256', clave.encode(), bytes.fromhex(sal), ITERACIONES)
    return 'pbkdf2_sha256$%d$%s$%s' % (ITERACIONES, sal, derivada.hex())


def clave_correcta(clave, guardada):
    try:
        algoritmo, iteraciones, sal, esperado = guardada.split('$')
        if algoritmo != 'pbkdf2_sha256':
            return False
        derivada = hashlib.pbkdf2_hmac('sha256', clave.encode(), bytes.fromhex(sal), int(iteraciones))
        return hmac.compare_digest(derivada.hex(), esperado)
    except (ValueError, AttributeError):
        return False


def hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def cookie_sesion(token):
    return '%s=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d' % (COOKIE, token, SESION_HORAS * 3600)


def cookie_borrada():
    return '%s=; Path=/; HttpOnly; SameSite=Strict; Max-Age=0' % COOKIE


def sesion_actual(h):
    galletas = SimpleCookie()
    try:
        galletas.load(h.headers.get('Cookie', ''))
    except Exception:
        return None
    morsel = galletas.get(COOKIE)
    if not morsel or not morsel.value:
        return None
    with conectar() as db:
        fila = db.execute('''SELECT s.id AS sesion_id, s.expira_en, u.id AS usuario_id,
                                    u.usuario, u.nombre, u.rol, u.activo
                               FROM admin_sesiones s
                               JOIN admin_usuarios u ON u.id = s.usuario_id
                              WHERE s.token_hash = ?''', (hash_token(morsel.value),)).fetchone()
    if not fila or not fila['activo'] or fila['expira_en'] <= ahora():
        return None
    return dict(fila)


def exigir_sesion(h, escritura=False):
    datos = sesion_actual(h)
    if not datos:
        responder(h, 401, {'error': 'Inicia sesión para usar el panel.', 'sesion': False})
        return None
    if escritura and datos['rol'] == 'consulta':
        responder(h, 403, {'error': 'Tu usuario es de solo consulta: no puede modificar datos.'})
        return None
    return datos


def auditar(db, tabla, registro_id, detalle, usuario):
    db.execute("INSERT INTO auditoria(tabla,registro_id,accion,detalle,origen) VALUES(?,?,'update',?,?)",
               (tabla, registro_id, '%s: %s' % (usuario, detalle), 'panel'))


def cerrar_sesiones_vencidas(db):
    db.execute("DELETE FROM admin_sesiones WHERE expira_en <= datetime('now','localtime')")


def iniciar():
    """Se llama una vez al arrancar el servidor. Es idempotente."""
    with conectar() as db:
        cerrar_sesiones_vencidas(db)
        if not db.execute('SELECT 1 FROM admin_usuarios LIMIT 1').fetchone():
            usuario = (os.environ.get('DASAUTO_ADMIN_USUARIO') or 'admin').strip().lower()
            clave = os.environ.get('DASAUTO_ADMIN_CLAVE')
            generada = clave is None
            if generada:
                clave = secrets.token_urlsafe(9)
            db.execute('INSERT INTO admin_usuarios(usuario,nombre,clave_hash,rol) VALUES(?,?,?,?)',
                       (usuario, 'Administrador', cifrar_clave(clave), 'admin'))
            if generada:
                ruta = DB.parent / 'clave_admin_inicial.txt'
                ruta.write_text('Usuario: %s\nClave: %s\n\nCambia esta clave al ingresar al panel.\n'
                                % (usuario, clave), encoding='utf-8')
                try:
                    ruta.chmod(0o600)
                except OSError:
                    pass
                print('Panel de administración: usuario "%s" creado.' % usuario, flush=True)
                print('Clave inicial guardada en: %s' % ruta, flush=True)
        liberar_vencidas(db)


# ------------------------------------------------------------- financiación
def plan_para(db, plazo):
    fila = db.execute('''SELECT * FROM tasas_financiacion
                          WHERE activo = 1 AND plazo_min <= ? AND plazo_max >= ?
                          ORDER BY tasa_anual LIMIT 1''', (plazo, plazo)).fetchone()
    if not fila:
        raise ErrorValidacion('No hay un plan de financiación para ese plazo.')
    return fila


def calcular_cuota(precio, inicial, plazo, tasa):
    capital = precio - inicial
    if capital <= 0:
        raise ErrorValidacion('La cuota inicial debe ser menor que el precio del vehículo.')
    interes = tasa / 100 / 12
    if interes == 0:
        cuota = capital / plazo
    else:
        cuota = capital * interes / (1 - (1 + interes) ** -plazo)
    return int(math.ceil(cuota / 1000) * 1000)


def cotizar(db, datos, guardar=False):
    sku = texto(datos, 'sku', 40).lower()
    plazo = entero(datos, 'plazo_meses', 6, 84)
    vehiculo = db.execute('SELECT inventario_id, sku, nombre, precio_venta FROM v_precios WHERE sku=?',
                          (sku,)).fetchone()
    if not vehiculo:
        raise ErrorValidacion('Vehículo no encontrado.')
    plan = plan_para(db, plazo)
    precio = vehiculo['precio_venta']
    minimo = int(math.ceil(precio * plan['inicial_min_pct'] / 100))
    inicial = entero(datos, 'cuota_inicial', 0, precio)
    if inicial < minimo:
        raise ErrorValidacion('La cuota inicial mínima para este plan es de %s.' % money(minimo))
    cuota = calcular_cuota(precio, inicial, plazo, plan['tasa_anual'])
    resultado = {
        'sku': vehiculo['sku'], 'nombre': vehiculo['nombre'],
        'precio': precio, 'cuota_inicial': inicial, 'capital': precio - inicial,
        'plazo_meses': plazo, 'tasa_anual': plan['tasa_anual'], 'plan': plan['nombre'],
        'inicial_min_pct': plan['inicial_min_pct'],
        'cuota_mensual': cuota,
        'total_intereses': cuota * plazo - (precio - inicial),
        'total_a_pagar': cuota * plazo + inicial,
    }
    if not guardar:
        return resultado, None

    terminos(datos)
    envio = identificador(datos)
    previo = db.execute('SELECT id FROM cotizaciones_financiacion WHERE envio_id=?', (envio,)).fetchone()
    if previo:
        return resultado, 'COT-%d-%06d' % (datetime.now().year, previo['id'])
    nombre = texto(datos, 'nombre', 150)
    email = correo(datos)
    telefono = texto(datos, 'telefono', 30)
    documento = texto(datos, 'documento', 30, obligatorio=False)
    usuario_id = asegurar_usuario(db, nombre, documento, email, telefono)
    fila = db.execute('''INSERT INTO cotizaciones_financiacion
        (envio_id,usuario_id,inventario_id,nombre,email,telefono,precio_vehiculo,
         cuota_inicial,plazo_meses,tasa_anual,cuota_mensual,estado)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,'simulada')''',
        (envio, usuario_id, vehiculo['inventario_id'], nombre, email, telefono, precio,
         inicial, plazo, plan['tasa_anual'], cuota))
    resultado['radicado'] = 'COT-%d-%06d' % (datetime.now().year, fila.lastrowid)
    return resultado, resultado['radicado']


def money(valor):
    return '$ %s' % format(int(valor), ',').replace(',', '.')


# ------------------------------------------------------------------- ficha
def ficha_vehiculo(db, sku):
    fila = db.execute('SELECT * FROM v_inventario_publico WHERE sku=?', (sku,)).fetchone()
    if not fila:
        return None
    vehiculo = dict(fila)
    try:
        vehiculo['especificaciones'] = json.loads(vehiculo.get('especificaciones') or '{}')
    except ValueError:
        vehiculo['especificaciones'] = {}
    if not isinstance(vehiculo['especificaciones'], dict):
        vehiculo['especificaciones'] = {}
    vehiculo['historial'] = [dict(r) for r in db.execute(
        '''SELECT campo, valor_anterior, valor_nuevo, origen, creado_en
             FROM precios_historico WHERE inventario_id = ?
            ORDER BY id DESC LIMIT 8''', (fila['inventario_id'],))]
    vehiculo['similares'] = [dict(r) for r in db.execute(
        '''SELECT sku, nombre, precio_venta, imagen_url
             FROM v_inventario_publico
            WHERE categoria = ? AND sku <> ?
            ORDER BY precio_venta LIMIT 3''', (fila['categoria'], sku))]
    plan = db.execute('''SELECT * FROM tasas_financiacion
                          WHERE activo = 1 ORDER BY plazo_max DESC LIMIT 1''').fetchone()
    if plan:
        inicial = int(math.ceil(fila['precio_venta'] * max(plan['inicial_min_pct'], 20) / 100))
        vehiculo['financiacion_estimada'] = {
            'plazo_meses': plan['plazo_max'], 'tasa_anual': plan['tasa_anual'],
            'cuota_inicial': inicial, 'cuota_mensual': calcular_cuota(
                fila['precio_venta'], inicial, plan['plazo_max'], plan['tasa_anual']),
        }
    return vehiculo


# ------------------------------------------------------------------ agenda
def ocupacion(db, fecha):
    cupos = {r['hora']: r for r in db.execute(
        'SELECT hora, capacidad, activo FROM agenda_cupos WHERE fecha=?', (fecha,))}
    ocupados = {r['hora']: r['n'] for r in db.execute(
        '''SELECT hora_programada AS hora, COUNT(*) AS n FROM citas_taller
            WHERE fecha_programada=? AND estado NOT IN ('cancelada','no_show')
            GROUP BY hora_programada''', (fecha,))}
    franjas = []
    for hora in HORAS:
        cupo = cupos.get(hora)
        capacidad = cupo['capacidad'] if cupo else CUPO_DEFECTO
        activo = bool(cupo['activo']) if cupo else True
        usados = ocupados.get(hora, 0)
        franjas.append({
            'hora': hora, 'capacidad': capacidad, 'ocupados': usados,
            'disponibles': max(0, capacidad - usados),
            'activo': activo, 'abierta': activo and usados < capacidad,
        })
    return franjas


def agendar(db, datos):
    fecha = fecha_valida(texto(datos, 'fecha', 10))
    hora = texto(datos, 'hora', 5)
    if hora not in HORAS:
        raise ErrorValidacion('Elige una hora disponible de la agenda.')
    servicio = texto(datos, 'servicio', 30)
    if servicio not in SERVICIOS:
        raise ErrorValidacion('Servicio no disponible.')
    terminos(datos)
    envio = identificador(datos)
    previo = db.execute('SELECT radicado FROM citas_taller WHERE envio_id=?', (envio,)).fetchone()
    if previo:
        return previo['radicado']
    nombre = texto(datos, 'nombre', 150)
    documento = texto(datos, 'documento', 30)
    email = correo(datos)
    telefono = texto(datos, 'telefono', 30)
    placa = texto(datos, 'placa', 10, obligatorio=False)
    descripcion = texto(datos, 'descripcion', 2000, obligatorio=False)

    cupo = db.execute('SELECT capacidad, activo FROM agenda_cupos WHERE fecha=? AND hora=?',
                      (fecha, hora)).fetchone()
    capacidad = cupo['capacidad'] if cupo else CUPO_DEFECTO
    if cupo and not cupo['activo']:
        raise ErrorValidacion('Esa franja no está disponible.')
    usados = db.execute('''SELECT COUNT(*) FROM citas_taller
                            WHERE fecha_programada=? AND hora_programada=?
                              AND estado NOT IN ('cancelada','no_show')''', (fecha, hora)).fetchone()[0]
    if usados >= capacidad:
        raise ErrorValidacion('Esa hora ya está llena. Elige otra franja.')
    usuario_id = asegurar_usuario(db, nombre, documento, email, telefono)
    radicado = 'T-%s-%s' % (time.strftime('%Y'), uuid.uuid4().hex[:12].upper())
    db.execute('''INSERT INTO citas_taller(radicado,envio_id,usuario_id,nombre,documento,email,telefono,
                  placa,servicio,descripcion,fecha_programada,hora_programada,acepta_tratamiento)
                  VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)''',
               (radicado, envio, usuario_id, nombre, documento, email, telefono,
                placa or None, servicio, descripcion or None, fecha, hora))
    return radicado


# ---------------------------------------------------------------- inventario
def liberar(db, reserva, motivo, estado='liberada'):
    db.execute('UPDATE inventario SET existencias = existencias + ? WHERE id=? AND existencias IS NOT NULL',
               (reserva['cantidad'], reserva['inventario_id']))
    saldo = db.execute('SELECT existencias FROM inventario WHERE id=?',
                       (reserva['inventario_id'],)).fetchone()
    db.execute('''INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo,referencia)
                  VALUES(?,?,?,?,?,?)''',
               (reserva['inventario_id'], 'entrada', reserva['cantidad'],
                saldo['existencias'] if saldo else None, motivo, reserva.get('radicado')))
    db.execute('UPDATE inventario_reservas SET estado=? WHERE id=?', (estado, reserva['id']))


def liberar_vencidas(db):
    filas = db.execute('''SELECT r.id, r.inventario_id, r.cantidad, p.radicado
                            FROM inventario_reservas r JOIN pedidos p ON p.id = r.pedido_id
                           WHERE r.estado='activa'
                             AND r.expira_en IS NOT NULL
                             AND r.expira_en < datetime('now','localtime')
                             AND p.estado='pendiente' ''').fetchall()
    for fila in filas:
        liberar(db, dict(fila), 'Reserva vencida', 'vencida')
    return len(filas)


def ajustar_stock(db, sku, cantidad, motivo, usuario):
    fila = db.execute('SELECT id, existencias FROM inventario WHERE sku=?', (sku,)).fetchone()
    if not fila:
        raise ErrorValidacion('SKU no encontrado.')
    actual = fila['existencias'] or 0
    if cantidad < 0:
        raise ErrorValidacion('Las existencias no pueden quedar negativas.')
    delta = cantidad - actual
    db.execute('UPDATE inventario SET existencias=? WHERE id=?', (cantidad, fila['id']))
    db.execute('''INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo)
                  VALUES(?,?,?,?,?)''',
               (fila['id'], 'ajuste', delta, cantidad, motivo))
    auditar(db, 'inventario', fila['id'], 'existencias %s → %s (%s)' % (actual, cantidad, motivo), usuario)


# ------------------------------------------------------- consultas del panel
def datos_panel(db, seccion):
    if seccion == 'promociones':
        filas = [dict(r) for r in db.execute('''SELECT inventario_id, sku, nombre, precio_base,
                       precio_promocional, precio_venta, promo_vigente, estado, titulo, beneficio,
                       fecha_inicio, fecha_fin, existencias FROM v_precios ORDER BY nombre''')]
        archivo = [dict(r) for r in db.execute('''SELECT h.*, i.sku, i.nombre FROM promociones_historico h
                       JOIN inventario i ON i.id = h.inventario_id ORDER BY h.id DESC LIMIT 30''')]
        return {'filas': filas, 'archivo': archivo}
    if seccion == 'precios':
        return {'filas': [dict(r) for r in db.execute('SELECT * FROM v_historial_precios LIMIT 300')]}
    if seccion == 'inventario':
        return {
            'filas': [dict(r) for r in db.execute(
                '''SELECT inventario_id, sku, nombre, categoria, marca, modelo, anio, precio_venta,
                          precio_base, existencias, estado_stock, imagen_url, descripcion,
                          especificaciones, destacado
                     FROM v_inventario_publico ORDER BY nombre''')],
            'reservas': [dict(r) for r in db.execute(
                '''SELECT r.id, r.inventario_id, r.cantidad, r.estado, r.expira_en, r.creado_en,
                          i.sku, i.nombre, p.radicado
                     FROM inventario_reservas r
                     JOIN inventario i ON i.id = r.inventario_id
                     LEFT JOIN pedidos p ON p.id = r.pedido_id
                    ORDER BY r.id DESC LIMIT 100''')],
            'movimientos': [dict(r) for r in db.execute(
                '''SELECT m.id, m.tipo, m.cantidad, m.saldo_final, m.motivo, m.referencia, m.creado_en,
                          i.sku, i.nombre
                     FROM inventario_movimientos m JOIN inventario i ON i.id = m.inventario_id
                    ORDER BY m.id DESC LIMIT 100''')],
        }
    if seccion == 'agenda':
        return {
            'citas': [dict(r) for r in db.execute(
                '''SELECT id, radicado, nombre, telefono, placa, servicio, fecha_programada,
                          hora_programada, estado, creado_en
                     FROM citas_taller ORDER BY fecha_programada DESC, hora_programada DESC LIMIT 200''')],
            'cupos': [dict(r) for r in db.execute(
                '''SELECT * FROM agenda_cupos WHERE fecha >= date('now','localtime')
                    ORDER BY fecha, hora LIMIT 200''')],
            'hoy': {r['hora_programada']: r['n'] for r in db.execute(
                '''SELECT hora_programada, COUNT(*) n FROM citas_taller
                    WHERE fecha_programada = date('now','localtime')
                      AND estado NOT IN ('cancelada','no_show')
                    GROUP BY hora_programada''')},
            'servicios': list(SERVICIOS),
            'horas': list(HORAS),
        }
    if seccion == 'financiacion':
        return {
            'filas': [dict(r) for r in db.execute(
                '''SELECT c.*, i.sku, i.nombre AS vehiculo FROM cotizaciones_financiacion c
                     LEFT JOIN inventario i ON i.id = c.inventario_id
                    ORDER BY c.id DESC LIMIT 200''')],
            'planes': [dict(r) for r in db.execute('SELECT * FROM tasas_financiacion ORDER BY plazo_min')],
        }
    if seccion == 'pedidos':
        pedidos = [dict(r) for r in db.execute('SELECT * FROM pedidos ORDER BY id DESC LIMIT 200')]
        lineas = defaultdict(list)
        for r in db.execute('SELECT pedido_id, sku, nombre, cantidad, precio_unitario FROM pedidos_items'):
            lineas[r['pedido_id']].append(dict(r))
        for pedido in pedidos:
            pedido['items'] = lineas.get(pedido['id'], [])
        return {'filas': pedidos}
    if seccion == 'usuarios':
        return {'filas': [dict(r) for r in db.execute(
            '''SELECT id, usuario, nombre, rol, activo, creado_en, ultimo_acceso
                 FROM admin_usuarios ORDER BY usuario''')], 'roles': list(ROLES)}
    raise ErrorValidacion('Sección desconocida.')


def resumen(db):
    def uno(sql, *parametros):
        return db.execute(sql, parametros).fetchone()[0]

    return {
        'pedidos': uno('SELECT COUNT(*) FROM pedidos'),
        'pedidos_pendientes': uno("SELECT COUNT(*) FROM pedidos WHERE estado='pendiente'"),
        'citas_hoy': uno("SELECT COUNT(*) FROM citas_taller WHERE fecha_programada=date('now','localtime') AND estado NOT IN ('cancelada','no_show')"),
        'citas_semana': uno("SELECT COUNT(*) FROM citas_taller WHERE fecha_programada BETWEEN date('now','localtime') AND date('now','localtime','+7 days') AND estado NOT IN ('cancelada','no_show')"),
        'financiacion': uno('SELECT COUNT(*) FROM cotizaciones_financiacion'),
        'financiacion_nuevas': uno("SELECT COUNT(*) FROM cotizaciones_financiacion WHERE estado='simulada'"),
        'stock_bajo': uno('SELECT COUNT(*) FROM inventario WHERE existencias IS NOT NULL AND existencias <= 3'),
        'agotados': uno('SELECT COUNT(*) FROM inventario WHERE existencias = 0'),
        'reservas_activas': uno("SELECT COUNT(*) FROM inventario_reservas WHERE estado='activa'"),
        'promos_vigentes': uno('SELECT COUNT(*) FROM v_precios WHERE promo_vigente=1'),
        'promos_borrador': uno("SELECT COUNT(*) FROM promociones WHERE estado='borrador'"),
        'admin_usuarios': uno('SELECT COUNT(*) FROM admin_usuarios'),
        'actualizado': ahora(),
    }


# ----------------------------------------------------------------- acciones
def accion_panel(db, cuerpo, admin):
    nombre_accion = texto(cuerpo, 'accion', 40)
    usuario = admin['usuario']
    datos = cuerpo.get('datos') or {}
    if not isinstance(datos, dict):
        raise ErrorValidacion('Datos inválidos.')

    if nombre_accion == 'promocion_estado':
        sku = texto(datos, 'sku', 40).lower()
        estado = texto(datos, 'estado', 20)
        if estado not in ('borrador', 'publicada', 'finalizada'):
            raise ErrorValidacion('Estado de promoción inválido.')
        inicio = texto(datos, 'fecha_inicio', 10, obligatorio=False) or None
        fin = texto(datos, 'fecha_fin', 10, obligatorio=False) or None
        for valor in (inicio, fin):
            if valor and not FECHA.fullmatch(valor):
                raise ErrorValidacion('Las fechas deben tener formato AAAA-MM-DD.')
        if inicio and fin and fin < inicio:
            raise ErrorValidacion('La fecha final no puede ser anterior a la inicial.')
        fila = db.execute('SELECT id FROM promociones WHERE inventario_id=(SELECT id FROM inventario WHERE sku=?)',
                          (sku,)).fetchone()
        if not fila:
            raise ErrorValidacion('Ese vehículo no tiene promoción registrada.')
        db.execute('UPDATE promociones SET estado=?, fecha_inicio=?, fecha_fin=? WHERE id=?',
                   (estado, inicio, fin, fila['id']))
        auditar(db, 'promociones', fila['id'], '%s → %s (%s a %s)' % (sku, estado, inicio or 'sin inicio', fin or 'sin fin'), usuario)

    elif nombre_accion == 'promocion_precio':
        sku = texto(datos, 'sku', 40).lower()
        precio = entero(datos, 'precio', 0, 10 ** 12)
        fila = db.execute('''SELECT p.id, i.precio_base FROM promociones p
                             JOIN inventario i ON i.id = p.inventario_id WHERE i.sku=?''', (sku,)).fetchone()
        if not fila:
            raise ErrorValidacion('Ese vehículo no tiene promoción registrada.')
        if precio > fila['precio_base']:
            raise ErrorValidacion('La oferta no puede superar el precio base.')
        db.execute('UPDATE promociones SET precio_promocional=? WHERE id=?', (precio, fila['id']))
        auditar(db, 'promociones', fila['id'], 'oferta de %s: %s' % (sku, money(precio)), usuario)

    elif nombre_accion == 'precio_base':
        sku = texto(datos, 'sku', 40).lower()
        precio = entero(datos, 'precio', 1, 10 ** 12)
        fila = db.execute('SELECT id FROM inventario WHERE sku=?', (sku,)).fetchone()
        if not fila:
            raise ErrorValidacion('SKU no encontrado.')
        db.execute('UPDATE inventario SET precio_base=? WHERE id=?', (precio, fila['id']))
        auditar(db, 'inventario', fila['id'], 'precio base de %s: %s' % (sku, money(precio)), usuario)

    elif nombre_accion == 'stock_fijar':
        sku = texto(datos, 'sku', 40).lower()
        cantidad = entero(datos, 'cantidad', 0, 999)
        ajustar_stock(db, sku, cantidad, 'Ajuste desde el panel', usuario)

    elif nombre_accion == 'ficha_editar':
        sku = texto(datos, 'sku', 40).lower()
        fila = db.execute('SELECT inventario_id FROM inventario WHERE sku=?', (sku,)).fetchone()
        if not fila:
            raise ErrorValidacion('SKU no encontrado.')
        descripcion = texto(datos, 'descripcion', 1000, obligatorio=False)
        imagen = texto(datos, 'imagen_url', 200, obligatorio=False)
        destacado = entero(datos, 'destacado', 0, 1)
        if imagen and not (imagen.startswith('img/') or imagen.startswith('http')):
            raise ErrorValidacion('La imagen debe empezar por img/ o http.')
        db.execute('''UPDATE inventario_ficha SET descripcion=?, imagen_url=?, destacado=?,
                      actualizado_en=datetime('now','localtime') WHERE inventario_id=?''',
                   (descripcion or None, imagen or None, destacado, fila['inventario_id']))
        auditar(db, 'inventario_ficha', fila['inventario_id'], 'ficha de %s actualizada' % sku, usuario)

    elif nombre_accion == 'pedido_estado':
        radicado = texto(datos, 'radicado', 40)
        estado = texto(datos, 'estado', 20)
        if estado not in ESTADOS_PEDIDO:
            raise ErrorValidacion('Estado de pedido inválido.')
        fila = db.execute('SELECT id, estado FROM pedidos WHERE radicado=?', (radicado,)).fetchone()
        if not fila:
            raise ErrorValidacion('Pedido no encontrado.')
        db.execute('UPDATE pedidos SET estado=? WHERE id=?', (estado, fila['id']))
        auditar(db, 'pedidos', fila['id'], '%s: %s → %s' % (radicado, fila['estado'], estado), usuario)

    elif nombre_accion == 'reserva_liberar':
        reserva_id = entero(datos, 'id', 1, 10 ** 9)
        fila = db.execute('''SELECT r.id, r.inventario_id, r.cantidad, r.estado, p.radicado
                               FROM inventario_reservas r LEFT JOIN pedidos p ON p.id = r.pedido_id
                              WHERE r.id=?''', (reserva_id,)).fetchone()
        if not fila or fila['estado'] != 'activa':
            raise ErrorValidacion('La reserva no existe o ya no está activa.')
        liberar(db, dict(fila), 'Liberada desde el panel')
        auditar(db, 'inventario_reservas', reserva_id, 'reserva liberada', usuario)

    elif nombre_accion == 'reservas_vencidas':
        total = liberar_vencidas(db)
        auditar(db, 'inventario_reservas', None, 'reservas vencidas liberadas: %d' % total, usuario)
        return {'liberadas': total}

    elif nombre_accion == 'cita_estado':
        radicado = texto(datos, 'radicado', 40)
        estado = texto(datos, 'estado', 20)
        if estado not in ESTADOS_CITA:
            raise ErrorValidacion('Estado de cita inválido.')
        fila = db.execute('SELECT id FROM citas_taller WHERE radicado=?', (radicado,)).fetchone()
        if not fila:
            raise ErrorValidacion('Cita no encontrada.')
        db.execute('UPDATE citas_taller SET estado=?, actualizado_en=datetime(\'now\',\'localtime\') WHERE id=?',
                   (estado, fila['id']))
        auditar(db, 'citas_taller', fila['id'], '%s → %s' % (radicado, estado), usuario)

    elif nombre_accion == 'cupo_fijar':
        fecha = fecha_valida(texto(datos, 'fecha', 10))
        hora = texto(datos, 'hora', 5)
        if hora not in HORAS:
            raise ErrorValidacion('Hora fuera de la agenda.')
        capacidad = entero(datos, 'capacidad', 0, 20)
        db.execute('''INSERT INTO agenda_cupos(fecha,hora,capacidad,activo,actualizado_en)
                      VALUES(?,?,?,1,datetime('now','localtime'))
                      ON CONFLICT(fecha,hora) DO UPDATE SET capacidad=excluded.capacidad,
                        activo=1, actualizado_en=excluded.actualizado_en''',
                   (fecha, hora, capacidad))
        auditar(db, 'agenda_cupos', None, 'cupo %s %s: %d' % (fecha, hora, capacidad), usuario)

    elif nombre_accion == 'financiacion_estado':
        cotizacion = entero(datos, 'id', 1, 10 ** 9)
        estado = texto(datos, 'estado', 20)
        if estado not in ESTADOS_COTIZACION:
            raise ErrorValidacion('Estado de cotización inválido.')
        fila = db.execute('SELECT id FROM cotizaciones_financiacion WHERE id=?', (cotizacion,)).fetchone()
        if not fila:
            raise ErrorValidacion('Cotización no encontrada.')
        db.execute('UPDATE cotizaciones_financiacion SET estado=? WHERE id=?', (estado, cotizacion))
        auditar(db, 'cotizaciones_financiacion', cotizacion, 'estado → ' + estado, usuario)

    elif nombre_accion == 'tasa_actualizar':
        tasa_id = entero(datos, 'id', 1, 10 ** 6)
        try:
            tasa = float(datos.get('tasa_anual'))
        except (TypeError, ValueError):
            raise ErrorValidacion('La tasa debe ser un número.')
        if not 0 <= tasa <= 100:
            raise ErrorValidacion('Tasa fuera de rango.')
        activo = entero(datos, 'activo', 0, 1)
        fila = db.execute('SELECT id, nombre FROM tasas_financiacion WHERE id=?', (tasa_id,)).fetchone()
        if not fila:
            raise ErrorValidacion('Plan no encontrado.')
        db.execute('UPDATE tasas_financiacion SET tasa_anual=?, activo=? WHERE id=?',
                   (round(tasa, 2), activo, tasa_id))
        auditar(db, 'tasas_financiacion', tasa_id, '%s: tasa %.2f %s' % (fila['nombre'], tasa, 'activa' if activo else 'inactiva'), usuario)

    elif nombre_accion == 'usuario_crear':
        if admin['rol'] != 'admin':
            raise ErrorValidacion('Solo un administrador puede crear usuarios.')
        cuenta = texto(datos, 'usuario', 30).lower()
        if not USUARIO.fullmatch(cuenta):
            raise ErrorValidacion('El usuario debe tener de 3 a 30 caracteres (letras, números, punto, guion).')
        clave = texto(datos, 'clave', 200)
        if len(clave) < 8:
            raise ErrorValidacion('La clave debe tener al menos 8 caracteres.')
        nombre = texto(datos, 'nombre', 150)
        rol = texto(datos, 'rol', 20)
        if rol not in ROLES:
            raise ErrorValidacion('Rol inválido.')
        try:
            fila = db.execute('INSERT INTO admin_usuarios(usuario,nombre,clave_hash,rol) VALUES(?,?,?,?)',
                              (cuenta, nombre, cifrar_clave(clave), rol))
        except sqlite3.IntegrityError:
            raise ErrorValidacion('Ese usuario ya existe.')
        auditar(db, 'admin_usuarios', fila.lastrowid, 'usuario %s (%s) creado' % (cuenta, rol), usuario)

    elif nombre_accion == 'usuario_clave':
        cuenta = texto(datos, 'usuario', 30).lower()
        clave = texto(datos, 'clave', 200)
        if len(clave) < 8:
            raise ErrorValidacion('La clave debe tener al menos 8 caracteres.')
        if admin['rol'] != 'admin' and cuenta != admin['usuario']:
            raise ErrorValidacion('Solo puedes cambiar tu propia clave.')
        fila = db.execute('SELECT id FROM admin_usuarios WHERE usuario=?', (cuenta,)).fetchone()
        if not fila:
            raise ErrorValidacion('Usuario no encontrado.')
        db.execute('UPDATE admin_usuarios SET clave_hash=? WHERE id=?', (cifrar_clave(clave), fila['id']))
        if cuenta == admin['usuario']:
            db.execute('DELETE FROM admin_sesiones WHERE usuario_id=? AND id<>?',
                       (fila['id'], admin['sesion_id']))
        auditar(db, 'admin_usuarios', fila['id'], 'clave cambiada de %s' % cuenta, usuario)

    elif nombre_accion == 'usuario_activo':
        if admin['rol'] != 'admin':
            raise ErrorValidacion('Solo un administrador puede activar o desactivar usuarios.')
        cuenta = texto(datos, 'usuario', 30).lower()
        activo = entero(datos, 'activo', 0, 1)
        if cuenta == admin['usuario'] and not activo:
            raise ErrorValidacion('No puedes desactivar tu propia cuenta.')
        fila = db.execute('SELECT id FROM admin_usuarios WHERE usuario=?', (cuenta,)).fetchone()
        if not fila:
            raise ErrorValidacion('Usuario no encontrado.')
        db.execute('UPDATE admin_usuarios SET activo=? WHERE id=?', (activo, fila['id']))
        if not activo:
            db.execute('DELETE FROM admin_sesiones WHERE usuario_id=?', (fila['id'],))
        auditar(db, 'admin_usuarios', fila['id'], 'usuario %s %s' % (cuenta, 'activado' if activo else 'desactivado'), usuario)

    else:
        raise ErrorValidacion('Acción desconocida.')
    return {'ok': True}


# -------------------------------------------------------------------- rutas
def manejar_get(h, ruta):
    """Devuelve True si la ruta era de este módulo y ya respondió."""
    consulta = parse_qs(urlsplit(h.path).query)
    try:
        if ruta == '/api/financiacion/datos':
            with conectar() as db:
                vehiculos = [dict(r) for r in db.execute(
                    '''SELECT sku, nombre, categoria, propulsion, precio_venta, promo_vigente,
                              existencias, estado_stock, imagen_url, marca, modelo
                         FROM v_inventario_publico ORDER BY categoria, precio_venta''')]
                planes = [dict(r) for r in db.execute(
                    '''SELECT id, nombre, plazo_min, plazo_max, tasa_anual, inicial_min_pct
                         FROM tasas_financiacion WHERE activo=1 ORDER BY plazo_min''')]
            responder(h, 200, {'vehiculos': vehiculos, 'planes': planes})
            return True

        if ruta == '/api/ficha':
            sku = (consulta.get('sku') or [''])[0].strip().lower()
            if not sku:
                raise ErrorValidacion('Falta el vehículo.')
            with conectar() as db:
                vehiculo = ficha_vehiculo(db, sku)
            if not vehiculo:
                responder(h, 404, {'error': 'Vehículo no encontrado.'})
            else:
                responder(h, 200, {'vehiculo': vehiculo})
            return True

        if ruta == '/api/inventario/disponibilidad':
            with conectar() as db:
                filas = [dict(r) for r in db.execute(
                    '''SELECT sku, nombre, categoria, propulsion, precio_venta, precio_base,
                              promo_vigente, existencias, estado_stock, imagen_url, marca, modelo, anio
                         FROM v_inventario_publico ORDER BY categoria, nombre''')]
                liberadas = liberar_vencidas(db)
            responder(h, 200, {'vehiculos': filas, 'reservas_vencidas_liberadas': liberadas,
                               'actualizado': ahora()})
            return True

        if ruta == '/api/agenda/disponibilidad':
            fecha = (consulta.get('fecha') or [hoy()])[0]
            fecha_valida(fecha)
            with conectar() as db:
                franjas = ocupacion(db, fecha)
            responder(h, 200, {'fecha': fecha, 'hoy': hoy(), 'max_fecha': fecha_mas(DIAS_AGENDA),
                               'franjas': franjas, 'servicios': list(SERVICIOS)})
            return True

        if ruta == '/api/admin/estado':
            datos = sesion_actual(h)
            if not datos:
                responder(h, 200, {'sesion': False})
            else:
                responder(h, 200, {'sesion': True, 'usuario': datos['usuario'],
                                   'nombre': datos['nombre'], 'rol': datos['rol']})
            return True

        if ruta == '/api/admin/resumen':
            admin = exigir_sesion(h)
            if not admin:
                return True
            with conectar() as db:
                responder(h, 200, {'resumen': resumen(db), 'admin': {'usuario': admin['usuario'], 'rol': admin['rol']}})
            return True

        if ruta == '/api/admin/datos':
            admin = exigir_sesion(h)
            if not admin:
                return True
            seccion = (consulta.get('seccion') or ['promociones'])[0]
            with conectar() as db:
                responder(h, 200, datos_panel(db, seccion))
            return True

        if ruta == '/api/admin/exportar':
            admin = exigir_sesion(h)
            if not admin:
                return True
            seccion = (consulta.get('seccion') or ['promociones'])[0]
            with conectar() as db:
                datos = datos_panel(db, seccion)
            filas = datos.get('filas', [])
            encabezados = list(filas[0].keys()) if filas else []
            lineas = [','.join(encabezados)]
            for fila in filas:
                lineas.append(','.join('"%s"' % str(fila.get(c, '')).replace('"', '""') for c in encabezados))
            contenido = '\ufeff' + '\n'.join(lineas) + '\n'
            cuerpo = contenido.encode('utf-8')
            h.send_response(200)
            h.send_header('Content-Type', 'text/csv; charset=utf-8')
            h.send_header('Content-Disposition', 'attachment; filename="%s.csv"' % seccion)
            h.send_header('Content-Length', str(len(cuerpo)))
            h.end_headers()
            h.wfile.write(cuerpo)
            return True

    except LimiteExcedido as e:
        responder(h, 429, {'error': str(e)})
        return True
    except ErrorValidacion as e:
        responder(h, 400, {'error': str(e)})
        return True
    except sqlite3.Error:
        responder(h, 500, {'error': 'No fue posible consultar la base de datos.'})
        return True
    return False


def manejar_post(h, ruta):
    """Devuelve True si la ruta era de este módulo y ya respondió."""
    if not ruta.startswith(('/api/financiacion/', '/api/agenda/', '/api/admin/')):
        return False
    ip = h.client_address[0] if h.client_address else '?'
    try:
        cuerpo = leer_json(h)

        if ruta == '/api/financiacion/simular':
            limitar('fin-sim:' + ip, 60, 600)
            with conectar() as db:
                resultado, _ = cotizar(db, cuerpo, guardar=False)
            responder(h, 200, {'simulacion': resultado})
            return True

        if ruta == '/api/financiacion/solicitar':
            limitar('fin-sol:' + ip, 10, 600)
            with conectar() as db:
                db.execute('BEGIN IMMEDIATE')
                resultado, radicado = cotizar(db, cuerpo, guardar=True)
            responder(h, 201, {'simulacion': resultado, 'radicado': radicado})
            return True

        if ruta == '/api/agenda/citas':
            limitar('agenda:' + ip, 10, 600)
            with conectar() as db:
                db.execute('BEGIN IMMEDIATE')
                radicado = agendar(db, cuerpo)
            responder(h, 201, {'radicado': radicado})
            return True

        if ruta == '/api/admin/login':
            limitar('login:' + ip, 10, 900)
            cuenta = texto(cuerpo, 'usuario', 30).lower()
            clave = texto(cuerpo, 'clave', 200)
            with conectar() as db:
                fila = db.execute('SELECT id, usuario, nombre, rol, clave_hash, activo FROM admin_usuarios WHERE usuario=?',
                                  (cuenta,)).fetchone()
                if not fila or not fila['activo'] or not clave_correcta(clave, fila['clave_hash']):
                    raise ErrorValidacion('Usuario o clave incorrectos.')
                cerrar_sesiones_vencidas(db)
                token = secrets.token_urlsafe(32)
                db.execute('''INSERT INTO admin_sesiones(token_hash,usuario_id,ip,expira_en)
                              VALUES(?,?,?,?)''',
                           (hash_token(token), fila['id'], ip,
                            (datetime.now() + timedelta(hours=SESION_HORAS)).strftime('%Y-%m-%d %H:%M:%S')))
                db.execute("UPDATE admin_usuarios SET ultimo_acceso=datetime('now','localtime') WHERE id=?",
                           (fila['id'],))
                auditar(db, 'admin_sesiones', fila['id'], 'ingreso al panel', fila['usuario'])
            responder(h, 200, {'usuario': fila['usuario'], 'nombre': fila['nombre'], 'rol': fila['rol']},
                      cabeceras=(cookie_sesion(token),))
            return True

        if ruta == '/api/admin/logout':
            galletas = SimpleCookie()
            try:
                galletas.load(h.headers.get('Cookie', ''))
            except Exception:
                galletas = SimpleCookie()
            morsel = galletas.get(COOKIE)
            if morsel and morsel.value:
                with conectar() as db:
                    db.execute('DELETE FROM admin_sesiones WHERE token_hash=?', (hash_token(morsel.value),))
            responder(h, 200, {'ok': True}, cabeceras=(cookie_borrada(),))
            return True

        if ruta == '/api/admin/accion':
            admin = exigir_sesion(h, escritura=True)
            if not admin:
                return True
            with conectar() as db:
                db.execute('BEGIN IMMEDIATE')
                resultado = accion_panel(db, cuerpo, admin)
            responder(h, 200, resultado)
            return True

        responder(h, 404, {'error': 'Ruta no disponible.'})
        return True

    except LimiteExcedido as e:
        responder(h, 429, {'error': str(e)})
        return True
    except ErrorValidacion as e:
        responder(h, 400, {'error': str(e)})
        return True
    except sqlite3.Error as e:
        mensaje = 'No fue posible guardar los datos.'
        if 'existencias' in str(e).lower():
            mensaje = 'No hay existencias suficientes para ese vehículo.'
        responder(h, 500, {'error': mensaje})
        return True

"""Gestión local por terminal. No publica información personal en la web."""
import argparse, json, sys
from base_datos import iniciar, conectar, respaldo, aplicar_migraciones

TABLAS = ['usuarios', 'pqrs', 'inventario', 'promociones',
          'citas_taller', 'pruebas_manejo', 'contactos',
          'cotizaciones_financiacion', 'cotizaciones_seguro',
          'pedidos', 'pedidos_items', 'inventario_movimientos',
          'inventario_ficha', 'pqrs_eventos', 'sedes', 'auditoria',
          'v_precios']  # vista: precio_venta = lo que se muestra y se cobra hoy

p = argparse.ArgumentParser(description='Gestión local de DasAuto')
s = p.add_subparsers(dest='accion', required=True)

a = s.add_parser('listar'); a.add_argument('tabla', choices=TABLAS)
a = s.add_parser('stock'); a.add_argument('sku'); a.add_argument('cantidad', type=int)
a = s.add_parser('precio'); a.add_argument('sku'); a.add_argument('pesos', type=int)
a = s.add_parser('responder'); a.add_argument('radicado'); a.add_argument('respuesta')
a = s.add_parser('estado-pqrs'); a.add_argument('radicado')
a.add_argument('estado', choices=['radicada', 'en_proceso', 'respondida', 'cerrada'])
a = s.add_parser('estado-promocion'); a.add_argument('sku', help="SKU del vehículo, o 'todas'")
a.add_argument('estado', choices=['borrador', 'publicada', 'finalizada'])
a = s.add_parser('estado-cita'); a.add_argument('radicado')
a.add_argument('estado', choices=['solicitada', 'confirmada', 'en_taller', 'finalizada', 'cancelada', 'no_show'])
a = s.add_parser('estado-prueba'); a.add_argument('radicado')
a.add_argument('estado', choices=['solicitada', 'confirmada', 'realizada', 'cancelada', 'no_show'])
a.add_argument('--costo', type=int, help='Costo estimado del servicio (solo citas)')
a = s.add_parser('estado-pedido'); a.add_argument('radicado')
a.add_argument('estado', choices=['pendiente', 'confirmado', 'facturado', 'cancelado'])
a = s.add_parser('asignar-cita'); a.add_argument('radicado')
a.add_argument('fecha', help='AAAA-MM-DD'); a.add_argument('hora', help='HH:MM')
a = s.add_parser('resumen')
a = s.add_parser('respaldo')
args = p.parse_args()

iniciar()

with conectar() as db:
    if args.accion == 'listar':
        # Nombre de tabla restringido por choices, nunca texto libre.
        print(json.dumps([dict(r) for r in db.execute('SELECT * FROM ' + args.tabla)],
                         ensure_ascii=False, indent=2))

    elif args.accion == 'resumen':
        consultas = [
            ('PQRS', 'SELECT COUNT(*) FROM pqrs'),
            ('  radicadas', "SELECT COUNT(*) FROM pqrs WHERE estado='radicada'"),
            ('  respondidas', "SELECT COUNT(*) FROM pqrs WHERE estado='respondida'"),
            ('Citas de taller', 'SELECT COUNT(*) FROM citas_taller'),
            ('  hoy', "SELECT COUNT(*) FROM citas_taller WHERE fecha_programada=date('now')"),
            ('Pruebas de manejo', 'SELECT COUNT(*) FROM pruebas_manejo'),
            ('Mensajes de contacto', 'SELECT COUNT(*) FROM contactos'),
            ('Cotizaciones de seguro', 'SELECT COUNT(*) FROM cotizaciones_seguro'),
            ('Pedidos', 'SELECT COUNT(*) FROM pedidos'),
            ('  pendientes', "SELECT COUNT(*) FROM pedidos WHERE estado='pendiente'"),
            ('Vehículos en catálogo', 'SELECT COUNT(*) FROM inventario'),
            ('Promociones publicadas', "SELECT COUNT(*) FROM promociones WHERE estado='publicada'"),
            ('  vigentes hoy', 'SELECT COUNT(*) FROM v_precios WHERE promo_vigente=1'),
        ]
        for etiqueta, sql in consultas:
            try:
                print(f'{etiqueta:<26}{db.execute(sql).fetchone()[0]:>6}')
            except Exception:
                print(f'{etiqueta:<26}{"n/d":>6}')

    elif args.accion == 'respaldo':
        print('Respaldo creado en', respaldo())

    elif args.accion == 'asignar-cita':
        import re
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', args.fecha) or not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', args.hora):
            p.error('Formato inválido. Fecha AAAA-MM-DD y hora HH:MM.')
        cur = db.execute('UPDATE citas_taller SET fecha_programada=?, hora_programada=?, estado=\'confirmada\' WHERE radicado=?',
                         (args.fecha, args.hora, args.radicado))

    else:
        if args.accion == 'stock':
            if args.cantidad < 0:
                p.error('Las existencias no pueden ser negativas.')
            anterior = db.execute('SELECT id, existencias FROM inventario WHERE sku=?', (args.sku,)).fetchone()
            if not anterior:
                p.error('SKU no encontrado.')
            cur = db.execute('UPDATE inventario SET existencias=? WHERE sku=?', (args.cantidad, args.sku))
            db.execute('INSERT INTO inventario_movimientos(inventario_id,tipo,cantidad,saldo_final,motivo) VALUES(?,?,?,?,?)',
                       (anterior['id'], 'ajuste', args.cantidad - (anterior['existencias'] or 0),
                        args.cantidad, 'Ajuste desde gestionar.py'))

        elif args.accion == 'precio':
            row = db.execute('SELECT id,precio_base FROM inventario WHERE sku=?', (args.sku,)).fetchone()
            if not row:
                p.error('SKU no encontrado.')
            if not 0 <= args.pesos <= row['precio_base']:
                p.error('Precio fuera del rango: 0 a precio base.')
            cur = db.execute('UPDATE promociones SET precio_promocional=? WHERE inventario_id=?', (args.pesos, row['id']))

        elif args.accion == 'responder':
            if not args.respuesta.strip():
                p.error('La respuesta no puede estar vacía.')
            cur = db.execute("UPDATE pqrs SET respuesta=?,estado='respondida' WHERE radicado=?", (args.respuesta, args.radicado))
            fila = db.execute('SELECT id FROM pqrs WHERE radicado=?', (args.radicado,)).fetchone()
            if fila:
                db.execute("INSERT INTO pqrs_eventos(pqrs_id,estado,nota,responsable) VALUES(?,?,?,?)",
                           (fila['id'], 'respondida', args.respuesta, 'gestionar.py'))

        elif args.accion == 'estado-pqrs':
            cur = db.execute('UPDATE pqrs SET estado=? WHERE radicado=?', (args.estado, args.radicado))
            fila = db.execute('SELECT id FROM pqrs WHERE radicado=?', (args.radicado,)).fetchone()
            if fila:
                db.execute('INSERT INTO pqrs_eventos(pqrs_id,estado,responsable) VALUES(?,?,?)',
                           (fila['id'], args.estado, 'gestionar.py'))

        elif args.accion == 'estado-promocion':
            # La oferta solo se muestra y se cobra si queda 'publicada' y vigente.
            if args.sku == 'todas':
                cur = db.execute('UPDATE promociones SET estado=?', (args.estado,))
            else:
                cur = db.execute('UPDATE promociones SET estado=? WHERE inventario_id=(SELECT id FROM inventario WHERE sku=?)',
                                 (args.estado, args.sku))

        elif args.accion == 'estado-cita':
            cur = db.execute('UPDATE citas_taller SET estado=? WHERE radicado=?', (args.estado, args.radicado))

        elif args.accion == 'estado-prueba':
            cur = db.execute('UPDATE pruebas_manejo SET estado=? WHERE radicado=?', (args.estado, args.radicado))

        else:  # estado-pedido
            cur = db.execute('UPDATE pedidos SET estado=? WHERE radicado=?', (args.estado, args.radicado))

        if not cur.rowcount:
            p.error('Registro no encontrado.')
        print('Cambio guardado correctamente.' + (f' ({cur.rowcount} registros)' if cur.rowcount > 1 else ''))

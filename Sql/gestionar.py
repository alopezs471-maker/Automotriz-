"""Gestión local por terminal. No publica información personal en la web."""
import argparse, json
from base_datos import iniciar, conectar
p=argparse.ArgumentParser(description='Gestión local de DasAuto')
s=p.add_subparsers(dest='accion',required=True)
a=s.add_parser('listar');a.add_argument('tabla',choices=['usuarios','pqrs','inventario','promociones'])
a=s.add_parser('stock');a.add_argument('sku');a.add_argument('cantidad',type=int)
a=s.add_parser('precio');a.add_argument('sku');a.add_argument('pesos',type=int)
a=s.add_parser('responder');a.add_argument('radicado');a.add_argument('respuesta')
a=s.add_parser('estado-pqrs');a.add_argument('radicado');a.add_argument('estado',choices=['radicada','en_proceso','respondida','cerrada'])
a=s.add_parser('estado-promocion');a.add_argument('sku');a.add_argument('estado',choices=['borrador','publicada','finalizada'])
args=p.parse_args();iniciar()
with conectar() as db:
    if args.accion=='listar':
        # Nombre de tabla restringido por choices, nunca texto libre.
        print(json.dumps([dict(r) for r in db.execute('SELECT * FROM '+args.tabla)],ensure_ascii=False,indent=2))
    else:
        if args.accion=='stock':
            if args.cantidad<0:p.error('Las existencias no pueden ser negativas.')
            cur=db.execute('UPDATE inventario SET existencias=? WHERE sku=?',(args.cantidad,args.sku))
        elif args.accion=='precio':
            row=db.execute('SELECT id,precio_base FROM inventario WHERE sku=?',(args.sku,)).fetchone()
            if not row:p.error('SKU no encontrado.')
            if not 0<=args.pesos<=row['precio_base']:p.error('Precio fuera del rango: 0 a precio base.')
            cur=db.execute('UPDATE promociones SET precio_promocional=? WHERE inventario_id=?',(args.pesos,row['id']))
        elif args.accion=='responder':
            if not args.respuesta.strip():p.error('La respuesta no puede estar vacía.')
            cur=db.execute("UPDATE pqrs SET respuesta=?,estado='respondida' WHERE radicado=?",(args.respuesta,args.radicado))
        elif args.accion=='estado-pqrs':
            cur=db.execute('UPDATE pqrs SET estado=? WHERE radicado=?',(args.estado,args.radicado))
        else:
            cur=db.execute('UPDATE promociones SET estado=? WHERE inventario_id=(SELECT id FROM inventario WHERE sku=?)',(args.estado,args.sku))
        if not cur.rowcount:p.error('Registro no encontrado.')
        print('Cambio guardado correctamente.')

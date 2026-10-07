"""Servidor de desarrollo local. Python 3.10+, sin dependencias externas."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlsplit, unquote
from pathlib import Path
import argparse, json, secrets, re, sqlite3, uuid, time
from base_datos import ROOT, iniciar, conectar, catalogo

PUBLIC = ROOT/'public'
TOKEN = secrets.token_urlsafe(32)

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(PUBLIC),**kwargs)
    def list_directory(self,path):
        self.send_error(403, 'Listado de carpetas deshabilitado')
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        super().end_headers()
    def json(self,status,data):
        payload=json.dumps(data,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        self.send_header('Content-Length',str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/api/sesion':
            return self.json(200,{'token':TOKEN})
        if path=='/api/promociones':
            return self.json(200,{'promociones':catalogo()})
        if path.startswith('/api/'):
            return self.json(404,{'error':'Ruta no disponible.'})
        resolved=(PUBLIC/unquote(path).lstrip('/')).resolve()
        if not resolved.is_relative_to(PUBLIC.resolve()):
            return self.json(403,{'error':'Acceso denegado.'})
        return super().do_GET()
    def do_POST(self):
        if urlsplit(self.path).path!='/api/pqrs':
            return self.json(404,{'error':'Ruta no disponible.'})
        # No CORS. Solo peticiones del mismo sitio con token entregado por el servidor.
        if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),TOKEN):
            return self.json(403,{'error':'Sesión inválida. Recarga la página.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if not 0<length<=24000: raise ValueError('Solicitud demasiado grande o vacía.')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                raise ValueError('Se requiere JSON.')
            data=json.loads(self.rfile.read(length))
            if not isinstance(data,dict): raise ValueError('Formato inválido.')
            limits={'nombre':150,'documento':30,'email':190,'telefono':30,'tipo_pqrs':20,'descripcion':10000,'envio_id':80}
            for key,limit in limits.items():
                if not isinstance(data.get(key),str) or not 1<=len(data[key].strip())<=limit:
                    raise ValueError('Revisa el campo '+key+'.')
                data[key]=data[key].strip()
            data['email']=data['email'].lower()
            if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',data['email']):
                raise ValueError('Correo electrónico inválido.')
            if data['tipo_pqrs'] not in ('peticion','queja','reclamo','sugerencia'):
                raise ValueError('Tipo de solicitud inválido.')
            if data.get('terminos') is not True: raise ValueError('Debes aceptar el tratamiento de datos.')
            # La clave identifica reintentos; no es una identidad de usuario.
            uuid.UUID(data['envio_id'])
            with conectar() as db:
                db.execute('BEGIN IMMEDIATE')
                prev=db.execute('SELECT radicado FROM pqrs WHERE envio_id=?',(data['envio_id'],)).fetchone()
                if prev: return self.json(200,{'radicado':prev['radicado']})
                # Usuarios son fichas de contacto, no cuentas autenticadas.
                db.execute('INSERT OR IGNORE INTO usuarios(nombre,documento,email,telefono) VALUES(?,?,?,?)',tuple(data[k] for k in ('nombre','documento','email','telefono')))
                uid=db.execute('SELECT id FROM usuarios WHERE email=?',(data['email'],)).fetchone()['id']
                radicado='PQRS-'+time.strftime('%Y')+'-'+uuid.uuid4().hex[:12].upper()
                db.execute('''INSERT INTO pqrs(radicado,envio_id,usuario_id,nombre,documento,email,telefono,tipo_pqrs,descripcion,acepta_tratamiento)
                VALUES(?,?,?,?,?,?,?,?,?,1)''',(radicado,data['envio_id'],uid,*(data[k] for k in ('nombre','documento','email','telefono','tipo_pqrs','descripcion'))))
            return self.json(201,{'radicado':radicado})
        except (ValueError,UnicodeDecodeError) as e:
            return self.json(400,{'error':str(e)})
        except sqlite3.Error:
            return self.json(500,{'error':'No fue posible guardar la solicitud. Reintenta más tarde.'})

if __name__=='__main__':
    args=argparse.ArgumentParser(description='DasAuto local')
    args.add_argument('--host',default='127.0.0.1')
    args.add_argument('--port',default=8000,type=int)
    opt=args.parse_args()
    iniciar()
    print(f'DasAuto: http://localhost:{opt.port}/index.html',flush=True)
    print('Detener: Ctrl+C. La base de datos permanece en datos/dasauto.sqlite3.',flush=True)
    ThreadingHTTPServer((opt.host,opt.port),Handler).serve_forever()

import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SQL_DIR = Path(__file__).resolve().parents[1]
if str(SQL_DIR) not in sys.path:
    sys.path.insert(0, str(SQL_DIR))

import base_datos


class AmpliacionProfesionalTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "dasauto_test.sqlite3"
        self.legacy_path = Path(self.tempdir.name) / "no_existe.sqlite3"
        with patch.object(base_datos, "DB", self.db_path), patch.object(base_datos, "LEGADO", self.legacy_path):
            base_datos.iniciar()

    def tearDown(self):
        self.tempdir.cleanup()

    def conectar_prueba(self):
        db = sqlite3.connect(self.db_path)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def test_nuevas_tablas_vistas_y_permisos(self):
        with self.conectar_prueba() as db:
            tablas = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            vistas = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='view'")}
            self.assertTrue({"facturas", "pagos", "servicios_taller", "ordenes_taller",
                             "ordenes_taller_items", "seguimientos_clientes", "roles",
                             "permisos", "rol_permisos"}.issubset(tablas))
            self.assertTrue({"v_reporte_ventas_mensual", "v_reporte_vehiculos_ventas",
                             "v_reporte_pagos", "v_reporte_taller_mensual",
                             "v_reporte_cotizaciones", "v_reporte_clientes"}.issubset(vistas))
            self.assertGreater(db.execute("SELECT COUNT(*) FROM permisos").fetchone()[0], 0)
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_factura_requiere_pedido_valido_y_pago_no_supera_total(self):
        with self.conectar_prueba() as db:
            vehiculo = db.execute("SELECT id,sku,nombre FROM inventario LIMIT 1").fetchone()
            db.execute("UPDATE inventario SET existencias=3 WHERE id=?", (vehiculo[0],))
            db.execute("""INSERT INTO pedidos
                (radicado,envio_id,nombre,documento,email,telefono,subtotal,descuento,total,estado)
                VALUES ('PED-FACT-1','ENVIO-FACT-1','Cliente','DOC-1','cliente@example.com','3000000000',1000,0,1000,'facturado')""")
            pedido = db.execute("SELECT id FROM pedidos WHERE radicado='PED-FACT-1'").fetchone()[0]
            db.execute("""INSERT INTO facturas
                (pedido_id,numero,nombre_cliente,documento_cliente,email_cliente,subtotal,descuento,impuestos,total)
                VALUES (?, 'FAC-TEST-1','Cliente','DOC-1','cliente@example.com',1000,0,0,1000)""", (pedido,))
            factura = db.execute("SELECT id FROM facturas WHERE pedido_id=?", (pedido,)).fetchone()[0]
            db.execute("""INSERT INTO pagos(factura_id,metodo,valor,estado)
                VALUES (?,'transferencia',600,'confirmado')""", (factura,))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "supera el saldo"):
                db.execute("""INSERT INTO pagos(factura_id,metodo,valor,estado)
                    VALUES (?,'efectivo',500,'confirmado')""", (factura,))
            with self.assertRaisesRegex(sqlite3.IntegrityError, "saldo"):
                db.execute("UPDATE facturas SET estado='pagada' WHERE id=?", (factura,))
            db.execute("""INSERT INTO pagos(factura_id,metodo,valor,estado)
                VALUES (?,'efectivo',400,'confirmado')""", (factura,))
            db.execute("UPDATE facturas SET estado='pagada' WHERE id=?", (factura,))
            self.assertEqual(db.execute("SELECT estado FROM facturas WHERE id=?", (factura,)).fetchone()[0], "pagada")

    def test_orden_taller_recalcula_totales_y_registra_cliente(self):
        with self.conectar_prueba() as db:
            cliente = db.execute("SELECT id FROM usuarios LIMIT 1").fetchone()
            if cliente is None:
                db.execute("""INSERT INTO usuarios(nombre,documento,email,telefono)
                    VALUES ('Cliente','DOC-T','taller@example.com','3000000000')""")
                cliente = db.execute("SELECT id FROM usuarios WHERE email='taller@example.com'").fetchone()
            orden = db.execute("""INSERT INTO ordenes_taller(numero,usuario_id,estado)
                VALUES ('OT-TEST-1',?,'recibida')""", (cliente[0],)).lastrowid
            servicio = db.execute("SELECT id FROM servicios_taller LIMIT 1").fetchone()[0]
            db.execute("""INSERT INTO ordenes_taller_items
                (orden_id,servicio_id,tipo,descripcion,cantidad,precio_unitario,costo_unitario,total_linea)
                VALUES (?,?,'servicio','Mantenimiento',1,250000,90000,250000)""", (orden,servicio))
            valores = db.execute("SELECT subtotal,costo_interno FROM ordenes_taller WHERE id=?", (orden,)).fetchone()
            self.assertEqual(tuple(valores), (250000,90000))
            db.execute("UPDATE ordenes_taller SET estado='entregada',fecha_cierre=CURRENT_TIMESTAMP WHERE id=?", (orden,))
            self.assertEqual(db.execute("SELECT COUNT(*) FROM v_reporte_taller_mensual").fetchone()[0], 1)

    def test_permisos_separan_roles(self):
        with self.conectar_prueba() as db:
            ventas = db.execute("""SELECT COUNT(*) FROM rol_permisos rp
                JOIN roles r ON r.id=rp.rol_id JOIN permisos p ON p.id=rp.permiso_id
                WHERE r.codigo='ventas' AND p.codigo='ventas.gestionar'""").fetchone()[0]
            consulta = db.execute("""SELECT COUNT(*) FROM rol_permisos rp
                JOIN roles r ON r.id=rp.rol_id JOIN permisos p ON p.id=rp.permiso_id
                WHERE r.codigo='consulta' AND p.codigo='ventas.gestionar'""").fetchone()[0]
            self.assertEqual(ventas, 1)
            self.assertEqual(consulta, 0)


if __name__ == "__main__":
    unittest.main()

"""Pruebas de humo para el esquema SQLite de DasAuto.

Ejecutar desde la raíz del repositorio:
    python -m unittest discover -s Sql/tests -v

Todas las pruebas usan una base temporal; nunca modifican la base real.
"""
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SQL_DIR = Path(__file__).resolve().parents[1]
if str(SQL_DIR) not in sys.path:
    sys.path.insert(0, str(SQL_DIR))

import base_datos  # noqa: E402


class IntegridadBaseDatosTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "dasauto_test.sqlite3"
        self.legacy_path = Path(self.tempdir.name) / "no_existe.sqlite3"
        # Reutiliza el inicializador y las migraciones reales, pero apunta a un
        # archivo temporal para no tocar los datos del proyecto.
        with patch.object(base_datos, "DB", self.db_path), patch.object(
            base_datos, "LEGADO", self.legacy_path
        ):
            base_datos.iniciar()

    def tearDown(self):
        self.tempdir.cleanup()

    def conectar_prueba(self):
        db = sqlite3.connect(self.db_path)
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def test_integridad_sqlite_y_claves_foraneas(self):
        with self.conectar_prueba() as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(), [])

    def test_catalogo_inicial_y_vistas_de_precio(self):
        with self.conectar_prueba() as db:
            inventario = db.execute("SELECT COUNT(*) FROM inventario").fetchone()[0]
            self.assertGreater(inventario, 0)
            objetos = {
                fila[0]
                for fila in db.execute(
                    "SELECT name FROM sqlite_master WHERE type='view'"
                )
            }
            self.assertIn("v_precios", objetos)
            self.assertIn("v_catalogo_publico", objetos)
            self.assertEqual(
                db.execute("SELECT COUNT(*) FROM v_precios").fetchone()[0],
                inventario,
            )

    def test_rechaza_precio_negativo(self):
        with self.conectar_prueba() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    """INSERT INTO inventario
                       (sku, nombre, categoria, precio_base)
                       VALUES ('TEST-NEG', 'Vehículo de prueba', 'Prueba', -1)"""
                )

    def test_rechaza_sku_duplicado(self):
        with self.conectar_prueba() as db:
            sku = db.execute("SELECT sku FROM inventario LIMIT 1").fetchone()[0]
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    """INSERT INTO inventario
                       (sku, nombre, categoria, precio_base)
                       VALUES (?, 'Duplicado de prueba', 'Prueba', 1)""",
                    (sku,),
                )

    def test_rechaza_promocion_con_vehiculo_inexistente(self):
        with self.conectar_prueba() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute(
                    """INSERT INTO promociones
                       (inventario_id, titulo, precio_promocional)
                       VALUES (999999, 'Promoción de prueba', 100)"""
                )

    def test_todas_las_migraciones_sql_quedaron_registradas(self):
        esperadas = {
            archivo.stem
            for archivo in (SQL_DIR / "migraciones").glob("*.sql")
        }
        with self.conectar_prueba() as db:
            aplicadas = {
                fila[0] for fila in db.execute("SELECT nombre FROM migraciones")
            }
        self.assertTrue(esperadas.issubset(aplicadas), esperadas - aplicadas)


if __name__ == "__main__":
    unittest.main()

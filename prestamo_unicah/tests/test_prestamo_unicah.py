from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import TransactionCase, tagged

from odoo.addons.prestamo_unicah.models.prestamo_prestamo import (
    DIAS_MAXIMOS_ESTUDIANTE,
    LIMITE_EQUIPOS_ESTUDIANTE,
)


@tagged("post_install", "-at_install")
class TestPrestamoUnicahBase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.equipos = cls.env["prestamo.equipo"].search([])
        cls.estudiante = cls.env["res.partner"].create(
            {"name": "Estudiante Prueba UNICAH"}
        )
        cls.docente = cls.env["res.partner"].create({"name": "Docente Prueba UNICAH"})

    def _crear_prestamo(self, tipo="estudiante", dias=5, equipos=None, partner=None):
        hoy = fields.Date.context_today(self)
        vals = {
            "name": "Prueba " + tipo,
            "partner_id": (partner or self.estudiante).id,
            "tipo_solicitante": tipo,
            "fecha_prestamo": hoy,
            "fecha_devolucion": hoy + timedelta(days=dias),
        }
        if equipos:
            vals["linea_ids"] = [
                (0, 0, {"equipo_id": equipo.id}) for equipo in equipos
            ]
        return self.env["prestamo.prestamo"].create(vals)


class TestCatalogoEquipos(TestPrestamoUnicahBase):
    def test_01_datos_iniciales(self):
        nombres = self.equipos.mapped("name")
        for nombre in (
            "Laptop Dell 01",
            "Laptop Dell 02",
            "Proyector Epson 01",
            "Bocina portátil 01",
        ):
            self.assertIn(nombre, nombres)

    def test_02_codigo_unico(self):
        with self.assertRaises(Exception):
            self.env["prestamo.equipo"].create(
                {"name": "Duplicado", "codigo": "LAP-001", "categoria": "laptop"}
            )

    def test_03_mantenimiento_y_disponible(self):
        equipo = self.equipos.filtered(lambda e: e.estado == "disponible")[0]
        equipo.action_mantenimiento()
        self.assertEqual(equipo.estado, "mantenimiento")
        equipo.action_disponible()
        self.assertEqual(equipo.estado, "disponible")

    def test_04_mantenimiento_bloqueado_si_prestado(self):
        equipo = self.equipos.filtered(lambda e: e.estado == "disponible")[0]
        equipo.estado = "prestado"
        with self.assertRaises(UserError):
            equipo.action_mantenimiento()


class TestPrestamos(TestPrestamoUnicahBase):
    def test_01_campos_calculados(self):
        prestamo = self._crear_prestamo(dias=5, equipos=self.equipos[:2])
        self.assertEqual(prestamo.cantidad_equipos, 2)
        self.assertEqual(prestamo.dias_prestamo, 5)

    def test_02_fechas_invertidas(self):
        hoy = fields.Date.context_today(self)
        with self.assertRaises(ValidationError):
            self.env["prestamo.prestamo"].create(
                {
                    "name": "Fechas invertidas",
                    "partner_id": self.estudiante.id,
                    "fecha_prestamo": hoy,
                    "fecha_devolucion": hoy - timedelta(days=1),
                }
            )

    def test_03_limite_dias_estudiante(self):
        with self.assertRaises(ValidationError):
            self._crear_prestamo(dias=DIAS_MAXIMOS_ESTUDIANTE + 1)

    def test_04_docente_puede_superar_limite_dias(self):
        prestamo = self._crear_prestamo(
            tipo="docente", dias=10, partner=self.docente
        )
        self.assertEqual(prestamo.dias_prestamo, 10)

    def test_05_equipos_repetidos(self):
        equipo = self.equipos[0]
        hoy = fields.Date.context_today(self)
        with self.assertRaises(ValidationError):
            self.env["prestamo.prestamo"].create(
                {
                    "name": "Equipo repetido",
                    "partner_id": self.estudiante.id,
                    "fecha_prestamo": hoy,
                    "fecha_devolucion": hoy + timedelta(days=2),
                    "linea_ids": [
                        (0, 0, {"equipo_id": equipo.id}),
                        (0, 0, {"equipo_id": equipo.id}),
                    ],
                }
            )

    def test_06_flujo_prestar_devolver(self):
        equipos = self.equipos[:2]
        prestamo = self._crear_prestamo(equipos=equipos)
        prestamo.action_prestar()
        self.assertEqual(prestamo.state, "prestado")
        self.assertTrue(all(e.estado == "prestado" for e in equipos))
        prestamo.action_devolver()
        self.assertEqual(prestamo.state, "devuelto")
        self.assertTrue(all(e.estado == "disponible" for e in equipos))

    def test_07_prestar_sin_equipos(self):
        prestamo = self._crear_prestamo()
        with self.assertRaises(UserError):
            prestamo.action_prestar()

    def test_08_limite_equipos_estudiante(self):
        prestamo = self._crear_prestamo(equipos=self.equipos[:3])
        with self.assertRaises(UserError):
            prestamo.action_prestar()

    def test_09_docente_puede_prestar_tres_equipos(self):
        prestamo = self._crear_prestamo(
            tipo="docente", dias=10, equipos=self.equipos[:3], partner=self.docente
        )
        prestamo.action_prestar()
        self.assertEqual(prestamo.state, "prestado")
        prestamo.action_devolver()

    def test_10_equipo_en_mantenimiento_al_prestar(self):
        equipo = self.equipos.filtered(lambda e: e.estado == "disponible")[0]
        prestamo = self._crear_prestamo(equipos=equipo)
        equipo.action_mantenimiento()
        with self.assertRaises(UserError):
            prestamo.action_prestar()

    def test_11_marcar_atrasado(self):
        hoy = fields.Date.context_today(self)
        prestamo = self.env["prestamo.prestamo"].create(
            {
                "name": "Atrasado",
                "partner_id": self.docente.id,
                "tipo_solicitante": "docente",
                "fecha_prestamo": hoy - timedelta(days=10),
                "fecha_devolucion": hoy - timedelta(days=1),
                "linea_ids": [(0, 0, {"equipo_id": self.equipos[0].id})],
            }
        )
        prestamo.action_prestar()
        prestamo.action_marcar_atrasado()
        self.assertEqual(prestamo.state, "atrasado")
        prestamo.action_devolver()
        self.assertEqual(prestamo.state, "devuelto")

    def test_12_marcar_atrasado_fechas_vigentes(self):
        prestamo = self._crear_prestamo(
            tipo="docente", dias=5, equipos=self.equipos[:1], partner=self.docente
        )
        prestamo.action_prestar()
        with self.assertRaises(UserError):
            prestamo.action_marcar_atrasado()

    def test_13_ondelete_cascade(self):
        prestamo = self._crear_prestamo(equipos=self.equipos[:2])
        lineas = prestamo.linea_ids
        prestamo.unlink()
        self.assertFalse(lineas.exists())

    def test_14_veces_prestado(self):
        equipo = self.equipos.filtered(lambda e: e.estado == "disponible")[0]
        prestamo = self._crear_prestamo(equipos=equipo)
        prestamo.action_prestar()
        prestamo.action_devolver()
        self.assertGreaterEqual(equipo.veces_prestado, 1)

    def test_15_herencia_partner(self):
        prestamo = self._crear_prestamo(equipos=self.equipos[:1])
        self.assertIn(prestamo, self.estudiante.prestamo_equipo_ids)

    def test_16_vistas_y_menus(self):
        for xmlid in (
            "prestamo_equipo_view_list",
            "prestamo_equipo_view_form",
            "prestamo_equipo_view_kanban",
            "prestamo_prestamo_view_list",
            "prestamo_prestamo_view_form",
            "prestamo_prestamo_view_search",
            "view_partner_form_prestamo_unicah",
        ):
            self.assertTrue(
                self.env.ref(f"prestamo_unicah.{xmlid}").exists(), xmlid
            )
        self.assertTrue(self.env.ref("prestamo_unicah.prestamo_menu_root"))
        self.assertTrue(self.env.ref("prestamo_unicah.prestamo_equipo_menu"))
        self.assertTrue(self.env.ref("prestamo_unicah.prestamo_prestamo_menu"))

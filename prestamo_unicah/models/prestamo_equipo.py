from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class PrestamoEquipo(models.Model):
    _name = "prestamo.equipo"
    _description = "Equipo para préstamo"
    _order = "categoria, name"

    name = fields.Char(string="Nombre", required=True)
    codigo = fields.Char(string="Código de inventario", required=True, copy=False)
    categoria = fields.Selection(
        [
            ("laptop", "Laptop"),
            ("proyector", "Proyector"),
            ("audio", "Audio"),
            ("laboratorio", "Laboratorio"),
        ],
        string="Categoría",
        required=True,
        default="laptop",
    )
    estado = fields.Selection(
        [
            ("disponible", "Disponible"),
            ("prestado", "Prestado"),
            ("mantenimiento", "En mantenimiento"),
        ],
        string="Estado",
        required=True,
        default="disponible",
    )
    notas = fields.Text(string="Notas")
    active = fields.Boolean(string="Activo", default=True)
    veces_prestado = fields.Integer(
        string="Veces prestado",
        compute="_compute_veces_prestado",
        help="Cantidad de préstamos en los que ha aparecido este equipo.",
    )

    @api.constrains("codigo")
    def _check_codigo_unico(self):
        for equipo in self:
            if equipo.codigo and self.search_count(
                [("codigo", "=", equipo.codigo), ("id", "!=", equipo.id)]
            ):
                raise ValidationError(
                    "El código de inventario debe ser único."
                )

    @api.depends("codigo")
    def _compute_veces_prestado(self):
        for equipo in self:
            equipo.veces_prestado = self.env["prestamo.linea"].search_count(
                [("equipo_id", "=", equipo.id)]
            )

    def action_mantenimiento(self):
        for equipo in self:
            if equipo.estado == "prestado":
                raise UserError(
                    "Un equipo prestado no puede enviarse a mantenimiento."
                )
            equipo.estado = "mantenimiento"

    def action_disponible(self):
        for equipo in self:
            equipo.estado = "disponible"

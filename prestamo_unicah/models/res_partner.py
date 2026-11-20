from odoo import fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"

    # Se usa un nombre propio para no sobrescribir `prestamo_ids`, que ya es
    # definido por el módulo anterior `unicah_prestamos` (otro modelo).
    prestamo_equipo_ids = fields.One2many(
        "prestamo.prestamo", "partner_id", string="Préstamos de equipo (UNICAH)"
    )

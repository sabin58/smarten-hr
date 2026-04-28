from odoo import models, fields


ROLE = [
    ("driver", "Driver"),
    ("manager", "Manager"),
    ("supervisor", "Supervisor"),
    ("fuel_incharge", "Fuel Incharge"),
]


class ResUser(models.Model):
    _inherit = "res.users"

    role = fields.Selection(ROLE, string="Role(Mining App)", default="driver")
    hr_app_role = fields.Selection(
        [
            ("admin", "Admin"),
            ("manager", "Manager"),
            ("user", "User"),
        ],
        default="user",
        string="Role(HR App)",
    )
    employee_no = fields.Char(related="employee_id.barcode")
    work_phone = fields.Char(related="employee_id.work_phone")

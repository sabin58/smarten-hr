from odoo import fields, models

ROLE = [
    ("driver", "Driver"),
    ("manager", "Manager"),
    ("supervisor", "Supervisor"),
    ("fuel_incharge", "Fuel Incharge"),
]


class ResUser(models.Model):
    _inherit = "res.users"

    mining_app_role = fields.Selection(
        ROLE, string="Role(Mining App)", default="driver"
    )
    hr_app_role = fields.Selection(
        [
            ("admin", "Admin"),
            ("manager", "Manager"),
            ("user", "User"),
        ],
        default="user",
        string="Role(HR App)",
    )
    employee_no = fields.Char(related="employee_id.barcode", string="Employee No")

    department_id = fields.Many2one(
        related="employee_id.department_id",
        readonly=False,
        related_sudo=False,
    )

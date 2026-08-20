from odoo import fields, models


APPROVAL_TYPE_REQUIRED_FIELDS = {
    "attendance": ("has_period",),
    "advance_salary": ("has_amount",),
}


class ApprovalCategory(models.Model):
    _inherit = "approval.category"

    approval_type = fields.Selection(
        selection_add=[
            ("attendance", "Attendance Request"),
            ("advance_salary", "Advance Salary"),
        ]
    )

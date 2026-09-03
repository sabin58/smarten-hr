# -*- coding: utf-8 -*-

from odoo import fields, models


class HrExpense(models.Model):
    """19.0 folded hr.expense.sheet into hr.expense.

    ``approved_by`` and ``approved_on`` used to be related to the report the
    expense belonged to. The report is gone but the mobile app still reads
    both keys off an expense, so they are kept pointing at the fields that
    replaced them.
    """

    _inherit = "hr.expense"

    approved_by = fields.Many2one(
        comodel_name="res.users",
        string="Approved By",
        related="manager_id",
        tracking=False,
    )
    approved_on = fields.Datetime(string="Approved On", related="approval_date")

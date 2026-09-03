# -*- coding: utf-8 -*-

from odoo import fields, models


class HrPayslip(models.Model):
    """19.0 removed hr.payslip.number.

    The mobile app lists payslips by that reference and orders on it, so the
    field and the sequence that used to fill it are kept here. Existing
    references are left untouched by the upgrade.
    """

    _inherit = "hr.payslip"

    number = fields.Char(string="Reference", readonly=True, copy=False)

    def action_payslip_done(self):
        res = super().action_payslip_done()
        for payslip in self.filtered(lambda p: not p.number):
            payslip.number = self.env["ir.sequence"].next_by_code("salary.slip")
        return res

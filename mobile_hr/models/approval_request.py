# -*- coding: utf-8 -*-

from odoo import _, models
from odoo.exceptions import UserError


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    def _check_required_values(self):

        for request in self:
            if request.approval_type == "attendance":
                if not request.date_start or not request.date_end:
                    raise UserError(
                        _("The period is required on an attendance request.")
                    )
            elif request.approval_type == "advance_salary":
                if not request.amount:
                    raise UserError(
                        _("The amount is required on an advance salary request.")
                    )
                if request.amount < 0:
                    raise UserError(
                        _("The amount of an advance salary request must be positive.")
                    )

    def action_confirm(self):
        self._check_required_values()
        return super().action_confirm()

    def action_approve(self, approver=None):
        self._check_required_values()
        return super().action_approve(approver)

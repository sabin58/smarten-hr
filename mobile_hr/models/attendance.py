from odoo import models, fields, api


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    date = fields.Date(string="Date", compute="_compute_date", store=True)

    @api.depends("check_in")
    def _compute_date(self):
        for attendance in self:
            attendance.date = attendance.check_in.date()

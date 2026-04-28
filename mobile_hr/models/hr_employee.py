from collections import defaultdict
from odoo import fields, models, api
from odoo.addons.mobile_auth.controllers.auth import generate_image
from datetime import datetime, time, timedelta


class HREmployee(models.Model):
    _inherit = "hr.employee"

    mobile_image_url = fields.Char(compute="_compute_mobile_url", store=False)

    is_present = fields.Boolean(compute="_compute_is_present", store=False)

    def _compute_is_present(self):
        for rec in self:
            attendance = self.env["hr.attendance"].search(
                [("date", "=", datetime.today()), ("employee_id", "=", rec.id)], limit=1
            )
            if attendance:
                rec.is_present = True
            else:
                rec.is_present = False

    @api.depends("image_256")
    def _compute_mobile_url(self, **kw):
        for rec in self:
            if rec.image_256:
                rec.mobile_image_url = generate_image(
                    "hr.employee", "image_256", rec.id
                )
            else:
                rec.mobile_image_url = None

    @api.model
    def _get_employee_status_at_date(self, employee_domain=[], date=None):

        self = self.sudo()
        # Get all active employees
        employees = self.env["hr.employee"].search(employee_domain)

        # Get attendance records for the date
        if len(employee_domain) > 0:
            attendances = self.env["hr.attendance"].search(
                [("date", "=", date), ("employee_id", "in", employees.ids)]
            )
        else:
            attendances = self.env["hr.attendance"].search([("date", "=", date)])

        present_employee_ids = attendances.mapped("employee_id").ids

        present_count = len(set(present_employee_ids))
        absent_count = len(employees) - present_count

        leave = len(employees.filtered(lambda emp: emp.is_absent))

        return {
            "present": present_count,
            "absent": absent_count,
            "leave": leave,
        }

    @api.model
    def _get_emloyee_aged_report(self, date_from, domain=[]):
        hired_domain = domain.copy()
        fired_domain = domain.copy()

        hired_domain.append(("joined_date", ">=", date_from))

        hired = self.env["hr.employee"].sudo().search_count(hired_domain)

        fired_domain.append(("departure_date", ">=", date_from))

        fired = self.env["hr.employee"].sudo().search_count(fired_domain)

        current = self.env["hr.employee"].sudo().search_count(domain)

        return {"hired": hired, "fired": fired, "current": current}

    def get_attendance_report(self, date_from, date_to):

        self.ensure_one()

        calendar = self.resource_calendar_id

        if not calendar:
            raise ValueError("Employee has no working schedule assigned.")

        attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "=", self.id),
                ("check_in", ">=", date_from),
                ("check_in", "<=", date_to),
            ]
        )

        present_days = {att.check_in.date() for att in attendances}

        all_days = set()
        current = date_from.date()
        while current <= date_to.date():
            all_days.add(current)
            current += timedelta(days=1)

        work_intervals = self._get_expected_attendances(date_from, date_to)

        working_times = defaultdict(lambda: [])
        for expected_attendance in work_intervals:
            working_times[expected_attendance[0].date()].append(expected_attendance[:2])
        working_days = working_times.keys()

        non_working_days = all_days - working_days

        absent_days = working_days - present_days

        weekend_present = present_days - working_days

        weekend_absent = non_working_days - weekend_present
        attendance_percentage = round(
            (len(present_days - weekend_present) / len(working_days) * 100), 2
        )
        return {
            "total_days": len(all_days),
            "working_days": len(working_days),
            "present": len(present_days),
            "absent": len(absent_days),
            "weekend_present": len(weekend_present),
            "weekend_absent": len(weekend_absent),
            "attendance_percentage": attendance_percentage,
        }

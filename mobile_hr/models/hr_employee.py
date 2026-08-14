from collections import defaultdict

import pytz
from odoo import fields, models, api
from odoo.addons.mobile_auth.controllers.auth import generate_image
from datetime import datetime, time, timedelta


class HREmployeePublic(models.Model):
    _inherit = "hr.employee.public"

    joined_date = fields.Datetime("Joined Date", related="employee_id.joined_date")


class HREmployee(models.Model):
    _inherit = "hr.employee"

    mobile_image_url = fields.Char(compute="_compute_mobile_url", store=False)

    is_present = fields.Boolean(compute="_compute_is_present", store=False)

    joined_date = fields.Datetime("Joined Date")

    def _compute_is_present(self):
        # sudo: mobile app users may be portal users, who have no ACL on
        # hr.attendance. Read in one query instead of one per employee.
        attendances = (
            self.env["hr.attendance"]
            .sudo()
            .search(
                [
                    ("date", "=", fields.Date.context_today(self)),
                    ("employee_id", "in", self.ids),
                ]
            )
        )
        present_ids = set(attendances.mapped("employee_id").ids)

        for rec in self:
            rec.is_present = rec.id in present_ids

    @api.depends("image_256")
    def _compute_mobile_url(self, **kw):
        # sudo: image_256 and write_date live on hr.employee.public, which is
        # readable by internal users only, and mobile app users may be portal
        # users. Values are read through sudo but assigned on self.
        values = {rec.id: (rec.image_256, rec.write_date) for rec in self.sudo()}

        for rec in self:
            image, write_date = values.get(rec.id, (None, None))
            if image:
                rec.mobile_image_url = generate_image(
                    "hr.employee",
                    "image_256",
                    rec.id,
                    write_date and write_date.timestamp(),
                )
            else:
                rec.mobile_image_url = None

    @api.model
    def _get_employees_on_leave(self, employees, date):
        """Employees with a validated leave covering ``date``.

        ``hr.employee.is_absent`` only ever answers for today, so it cannot be
        used when the dashboard compares against a past date.
        """
        leaves = (
            self.env["hr.leave"]
            .sudo()
            .search(
                [
                    ("employee_id", "in", employees.ids),
                    ("state", "=", "validate"),
                    ("date_from", "<=", datetime.combine(date, time.max)),
                    ("date_to", ">=", datetime.combine(date, time.min)),
                ]
            )
        )
        return leaves.mapped("employee_id")

    @api.model
    def _get_late_count(self, attendances):
        """Employees whose first check-in is after their scheduled start."""
        late_count = 0

        for employee, employee_attendances in attendances.grouped(
            "employee_id"
        ).items():
            calendar = employee.resource_calendar_id
            if not calendar:
                continue

            tz = pytz.timezone(calendar.tz or employee.tz or "UTC")
            check_in = pytz.utc.localize(
                min(employee_attendances.mapped("check_in"))
            ).astimezone(tz)

            working_slots = calendar.attendance_ids.filtered(
                lambda a: a.dayofweek == str(check_in.weekday())
            )
            if not working_slots:
                continue

            expected_start = min(working_slots.mapped("hour_from"))
            if check_in.hour + check_in.minute / 60 > expected_start:
                late_count += 1

        return late_count

    @api.model
    def _get_employee_status_at_date(self, employee_domain=None, date=None):

        self = self.sudo()
        date = date or fields.Date.context_today(self)

        # Get all active employees
        employees = self.env["hr.employee"].search(employee_domain or [])

        # Get attendance records for the date. Always restricted to the
        # employees above, otherwise archived employees inflate the head count.
        attendances = self.env["hr.attendance"].search(
            [("date", "=", date), ("employee_id", "in", employees.ids)]
        )

        present_employees = attendances.mapped("employee_id")

        # present / leave / absent are kept mutually exclusive so the three
        # cards add up to the head count.
        on_leave = self._get_employees_on_leave(employees, date) - present_employees

        present_count = len(present_employees)
        leave_count = len(on_leave)

        return {
            "present": present_count,
            "absent": len(employees) - present_count - leave_count,
            "late": self._get_late_count(attendances),
            "leave": leave_count,
        }

    @api.model
    def _get_emloyee_aged_report(self, date_from, domain=None):
        domain = domain or []
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

        # sudo: mobile app users may be portal users, who have no ACL on
        # hr.attendance nor on the resource calendar.
        self = self.sudo()

        all_days = set()
        current = date_from.date()
        while current <= date_to.date():
            all_days.add(current)
            current += timedelta(days=1)

        empty_report = {
            "total_days": len(all_days),
            "working_days": 0,
            "present": 0,
            "absent": 0,
            "weekend_present": 0,
            "weekend_absent": 0,
            "attendance_percentage": 0,
        }

        # An employee without a working schedule has nothing to report on; the
        # dashboard should still render rather than fail.
        if not self.resource_calendar_id:
            return empty_report

        attendances = self.env["hr.attendance"].search(
            [
                ("employee_id", "=", self.id),
                ("check_in", ">=", date_from),
                ("check_in", "<=", date_to),
            ]
        )

        present_days = {att.check_in.date() for att in attendances}

        work_intervals = self._get_expected_attendances(date_from, date_to)

        working_times = defaultdict(lambda: [])
        for expected_attendance in work_intervals:
            working_times[expected_attendance[0].date()].append(expected_attendance[:2])
        working_days = working_times.keys()

        if not working_days:
            return empty_report

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

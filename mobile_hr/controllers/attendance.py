from odoo import fields
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Controller, route
from datetime import date as date_type, datetime, time, timedelta

import pytz

# Keys the app may send along with a punch. ``_attendance_action_change``
# prefixes each of them with ``in_``/``out_``, so only keys that exist on both
# sides of hr.attendance may be forwarded.
GEO_KEYS = ("latitude", "longitude", "city", "country_name")


class AttendanceController(Controller):
    def _get_parent_company_id(self):
        return request.env.company.parent_id.id or request.env.company.id

    def _get_my_employee(self):
        """The employee behind the token.

        sudo: mobile app users may be portal users, who have no ACL on
        hr.employee nor hr.attendance.
        """
        return (
            request.env.user.sudo()
            .with_company(self._get_parent_company_id())
            .employee_id
        )

    def _get_geo_information(self, kwargs):
        geo_information = {
            key: kwargs[key] for key in GEO_KEYS if kwargs.get(key) is not None
        }
        if geo_information:
            geo_information["mode"] = "manual"
        return geo_information or None

    def _get_attendance_status(self, employee):
        """Punch state of ``employee`` plus what the app shows next to it.

        ``attendance_state`` follows the last attendance whenever it happened,
        the way Odoo does, while the hours are for today only.
        """
        today = fields.Date.context_today(employee)

        attendances = (
            request.env["hr.attendance"]
            .sudo()
            .search(
                [("employee_id", "=", employee.id), ("date", "=", today)],
                order="check_in asc",
            )
        )

        # worked_hours stays 0 until check_out is written, so a running
        # attendance has to be counted against now.
        now = fields.Datetime.now()
        worked_hours = sum(
            attendance.worked_hours
            if attendance.check_out
            else (now - attendance.check_in).total_seconds() / 3600
            for attendance in attendances
        )

        last_attendance = employee.last_attendance_id

        return {
            "employee_id": employee.id,
            "employee_name": employee.display_name,
            "date": fields.Date.to_string(today),
            "attendance_state": employee.attendance_state,
            "attendance_id": last_attendance.id or False,
            "check_in": fields.Datetime.to_string(last_attendance.check_in),
            "check_out": fields.Datetime.to_string(last_attendance.check_out),
            "worked_hours_today": round(worked_hours, 2),
            "attendance_count_today": len(attendances),
        }

    @route(
        "/mobile/api/attendance-status",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_attendance_status(self, **kwargs):
        employee = self._get_my_employee()

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "No employee profile is linked to your account !!",
            }

        return {
            "status": 200,
            "data": self._get_attendance_status(employee),
            "message": "attendance status",
        }

    @route("/mobile/api/check-in", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def check_in(self, **kwargs):
        employee = self._get_my_employee()

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "No employee profile is linked to your account !!",
            }

        # The toggle in _attendance_action_change would check the employee out
        # instead of refusing, so the state is checked here first.
        if employee.attendance_state == "checked_in":
            return {
                "status": 400,
                "data": self._get_attendance_status(employee),
                "message": "You are already checked in !!",
            }

        try:
            employee._attendance_action_change(self._get_geo_information(kwargs))
        except (UserError, ValidationError) as error:
            return {"status": 400, "data": None, "message": error.args[0]}

        return {
            "status": 200,
            "data": self._get_attendance_status(employee),
            "message": "checked in",
        }

    @route("/mobile/api/check-out", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def check_out(self, **kwargs):
        employee = self._get_my_employee()

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "No employee profile is linked to your account !!",
            }

        if employee.attendance_state != "checked_in":
            return {
                "status": 400,
                "data": self._get_attendance_status(employee),
                "message": "You are not checked in !!",
            }

        try:
            employee._attendance_action_change(self._get_geo_information(kwargs))
        except (UserError, ValidationError) as error:
            return {"status": 400, "data": None, "message": error.args[0]}

        return {
            "status": 200,
            "data": self._get_attendance_status(employee),
            "message": "checked out",
        }

    def _parse_date(self, value):
        """``value`` as a date, accepting both dates and datetimes from the app."""
        if isinstance(value, date_type) and not isinstance(value, datetime):
            return value
        if isinstance(value, datetime):
            return value.date()
        return datetime.strptime(value[:10], "%Y-%m-%d").date()

    def _get_working_weekdays(self, employee):
        """Weekday numbers (Monday=0) the employee is expected to work on.

        Anything outside of them is reported as a weekend, so a calendar
        without working hours falls back to Monday-Friday.
        """
        calendar = (
            employee.resource_calendar_id or employee.company_id.resource_calendar_id
        )
        weekdays = {int(slot.dayofweek) for slot in calendar.attendance_ids}
        return weekdays or set(range(5))

    def _get_public_holiday_dates(self, employee, date_from, date_to):
        """Every date in the range covered by a company wide time off.

        resource.calendar.leaves holds utc datetimes, so the bounds are widened
        to whole days and the result is turned back into local dates.
        """
        holidays = employee._get_public_holidays(
            datetime.combine(date_from, time.min),
            datetime.combine(date_to, time.max),
        )

        employee_tz = pytz.timezone(employee._get_tz() or "UTC")

        def to_local_date(value):
            return pytz.utc.localize(value).astimezone(employee_tz).date()

        holiday_dates = set()
        for holiday in holidays:
            day = to_local_date(holiday.date_from)
            last_day = to_local_date(holiday.date_to)
            while day <= last_day:
                holiday_dates.add(day)
                day += timedelta(days=1)
        return holiday_dates

    @route(
        "/mobile/api/my-attendances", type="json", auth="public", csrf=False, cors="*"
    )
    @login_required()
    def get_my_attendance(self, **kwargs):
        """One entry per calendar day of the requested range.

        The app draws a calendar, so every day is returned - even the ones
        without an attendance - qualified as present, absent, holiday or
        weekend. Days in the future are left out, they are not absences yet.
        """
        employee = self._get_my_employee()

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "No employee profile is linked to your account !!",
            }

        today = fields.Date.context_today(employee)

        date_from = (
            self._parse_date(kwargs["startDate"])
            if kwargs.get("startDate")
            else today.replace(day=1)
        )
        date_to = (
            self._parse_date(kwargs["endDate"]) if kwargs.get("endDate") else today
        )
        # No day is absent before it is over.
        date_to = min(date_to, today)

        if date_to < date_from:
            return {"status": 200, "data": [], "message": "attendance"}

        attendances = (
            request.env["hr.attendance"]
            .sudo()
            .with_company(self._get_parent_company_id())
            .search(
                [
                    ("employee_id", "=", employee.id),
                    ("date", ">=", date_from),
                    ("date", "<=", date_to),
                ],
                order="check_in asc",
            )
        )

        # A day may hold several punches, the app shows the span of the day.
        attendances_by_date = {}
        for attendance in attendances:
            attendances_by_date.setdefault(attendance.date, []).append(attendance)

        holiday_dates = self._get_public_holiday_dates(employee, date_from, date_to)
        working_weekdays = self._get_working_weekdays(employee)

        data = []
        day = date_from
        while day <= date_to:
            day_attendances = attendances_by_date.get(day)

            if day_attendances:
                data.append(
                    {
                        "date": fields.Date.to_string(day),
                        "type": "present",
                        "check_in": fields.Datetime.to_string(
                            day_attendances[0].check_in
                        ),
                        "check_out": fields.Datetime.to_string(
                            day_attendances[-1].check_out
                        ),
                        "worked_hours": round(
                            sum(a.worked_hours for a in day_attendances), 2
                        ),
                    }
                )
            else:
                if day in holiday_dates:
                    day_type = "holiday"
                elif day.weekday() not in working_weekdays:
                    day_type = "weekend"
                else:
                    day_type = "absent"

                data.append(
                    {
                        "date": fields.Date.to_string(day),
                        "type": day_type,
                        "check_in": False,
                        "check_out": False,
                        "worked_hours": 0.0,
                    }
                )

            day += timedelta(days=1)

        return {"status": 200, "data": {"records": data}, "message": "attendance"}

    @route(
        "/mobile/api/mark-present/<int:employee_id>",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def post_attendance(self, employee_id, **kwargs):
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        if request.env.user.hr_app_role not in ["admin", "manager"]:
            return {
                "status": 403,
                "data": None,
                "message": "Only managers are allowed to create attendance !!",
            }

        today = datetime.now().date()

        employee = (
            request.env["hr.employee"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .browse(employee_id)
        )
        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "Employee not found !!",
            }

        # if employee.branch_id.biometric_available:
        #     return {
        #         "status": 403,
        #         "data": None,
        #         "message": "Your branch's attendance must be done from attendance device !!",
        #     }

        weekday = str(today.weekday())  # Monday=0 ... Sunday=6

        working_slots = employee.resource_calendar_id.attendance_ids.filtered(
            lambda a: a.dayofweek == weekday
        )

        check_in = datetime.combine(today, time(3, 15))
        check_out = datetime.combine(today, time(11, 15))

        if working_slots:
            first_slot = working_slots[0]
            hours = int(first_slot.hour_from)
            minutes = int((first_slot.hour_from - hours) * 60)
            check_in = datetime.combine(today, time(hours, minutes)) - timedelta(
                hours=5, minutes=45
            )

            last_slot = working_slots[-1]
            hours = int(last_slot.hour_to)
            minutes = int((last_slot.hour_to - hours) * 60)
            check_out = datetime.combine(today, time(hours, minutes)) - timedelta(
                hours=5, minutes=45
            )

        request.env["hr.attendance"].with_company(PARENT_COMPANY_ID).sudo().create(
            {
                "employee_id": employee_id,
                "check_in": check_in,
                "check_out": check_out,
            }
        )

        return {
            "status": 200,
            "data": {
                "employee_id": employee_id,
            },
            "message": "mark as present",
        }

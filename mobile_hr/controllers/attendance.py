from odoo import fields
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Controller, route
from datetime import datetime, time, timedelta

ATTENDANCE_SPECIFICATIONS = {
    "check_in": {},
    "check_out": {},
    "employee_id": {"fields": {"display_name": {}}},
    "worked_hours": {"fields": {"display_name": {}}},
    "date": {},
}

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
        "/mobile/api/attendance-status", type="json", auth="public", csrf=False, cors="*"
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

    @route(
        "/mobile/api/my-attendances", type="json", auth="public", csrf=False, cors="*"
    )
    @login_required()
    def get_my_attendance(self, **kwargs):
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )

        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        # data = []
        domain = [("employee_id", "=", employee_id.id)]

        if kwargs.get("startDate"):
            domain.append(("date", ">=", kwargs.get("startDate")))

        if kwargs.get("endDate"):
            domain.append(("date", "<=", kwargs.get("endDate")))

        data = (
            request.env["hr.attendance"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .web_search_read(
                domain,
                ATTENDANCE_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
                order="date desc",
            )
        )

        return {"status": 200, "data": data, "message": "attendance"}

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

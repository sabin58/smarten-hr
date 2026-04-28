from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.http import request, Controller, route
from datetime import datetime, time, timedelta

ATTENDANCE_SPECIFICATIONS = {
    "check_in": {},
    "check_out": {},
    "employee_id": {"fields": {"display_name": {}}},
    "worked_hours": {"fields": {"display_name": {}}},
    "date": {},
}


class AttendanceController(Controller):
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

        if employee.branch_id.biometric_available:
            return {
                "status": 403,
                "data": None,
                "message": "Your branch's attendance must be done from attendance device !!",
            }

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

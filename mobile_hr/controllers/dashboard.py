from odoo import http, models
from odoo.http import request
from odoo.addons.mobile_auth.controllers.auth import login_required
from datetime import date, datetime, timedelta

COMPARISON_PERIOD = {
    30: "Last 30 Days",
    1: "Yesterday",
    365: "Last 365 Days",
    60: "Last 60 Days",
}

EMPLOYEE_SPECIFICATION = {
    "name": {},
    "mobile_image_url": {},
    "email": {},
    "mobile_phone": {},
    "work_email": {},
    "department_id": {"fields": {"display_name": {}, "name": {}}},
    "job_id": {
        "fields": {
            "display_name": {},
        }
    },
    "is_absent": {},
    "is_present": {},
}


class HRDashboardController(http.Controller):
    def _get_child_department_ids(self, department_id):
        """Get all child department IDs recursively for a given department."""
        department = request.env["hr.department"].sudo().browse(int(department_id))
        child_departments = department.child_ids
        all_department_ids = [department_id]

        for child_dept in child_departments:
            all_department_ids.extend(self._get_child_department_ids(child_dept.id))

        return all_department_ids

    def _get_model_comparison(
        self,
        model_name: str,
        comparison_day: int = 1,
        date_field: str = "date",
        domain=[],
        groupby=[],
        aggregates=[],
    ):
        today = datetime.today()
        start_range_today = today - timedelta(days=comparison_day)

        current_stats = (
            request.env[model_name]
            .sudo()
            ._read_group(
                domain=domain
                + [(date_field, "<=", today), (date_field, ">", start_range_today)],
                groupby=groupby,
                aggregates=aggregates,
            )
        )

        current_stats_count = sum([tupple[1] for tupple in current_stats])
        start_range_before = start_range_today - timedelta(days=comparison_day)

        before_stats = (
            request.env[model_name]
            .sudo()
            ._read_group(
                domain=domain
                + [
                    (date_field, "<=", start_range_today),
                    (date_field, ">", start_range_before),
                ],
                groupby=groupby,
                aggregates=aggregates,
            )
        )

        before_stats_count = sum([tupple[1] for tupple in before_stats])
        return {
            "current": round(current_stats_count, 2),
            "before": round(before_stats_count, 2),
            "growth": round(
                (current_stats_count - before_stats_count) / before_stats_count * 100, 2
            )
            if before_stats_count
            else 0,
            "period": COMPARISON_PERIOD[comparison_day],
        }

    @http.route(
        "/mobile/api/my/dashboard",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def get_my_dashbord(self, **kw):
        user = request.env.user
        role = user.hr_app_role
        data = dict()

        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )

        if role == "admin":
            attendance_statuses_today = request.env[
                "hr.employee"
            ]._get_employee_status_at_date(date=date.today())
            attendance_statuses_yesterday = request.env[
                "hr.employee"
            ]._get_employee_status_at_date(date=date.today() - timedelta(days=1))

            data["present"] = {
                "label": "Present Today",
                "current": attendance_statuses_today["present"],
                "before": attendance_statuses_yesterday["present"],
                "growth": round(
                    (
                        attendance_statuses_today["present"]
                        - attendance_statuses_yesterday["present"]
                    )
                    / attendance_statuses_yesterday["present"]
                    * 100,
                    2,
                )
                if attendance_statuses_yesterday["present"]
                else 0,
                "period": "Yesterday",
            }
            data["absent"] = {
                "label": "Absent Today",
                "current": attendance_statuses_today["absent"],
                "before": attendance_statuses_yesterday["absent"],
                "growth": round(
                    (
                        attendance_statuses_today["absent"]
                        - attendance_statuses_yesterday["absent"]
                    )
                    / attendance_statuses_yesterday["absent"]
                    * 100,
                    2,
                )
                if attendance_statuses_yesterday["absent"]
                else 0,
                "period": "Yesterday",
            }
            data["late_arrival"] = {
                "label": "Late Arrivals",
                "current": attendance_statuses_today["late"],
                "before": attendance_statuses_yesterday["late"],
                "growth": round(
                    (
                        attendance_statuses_today["late"]
                        - attendance_statuses_yesterday["late"]
                    )
                    / attendance_statuses_yesterday["late"]
                    * 100,
                    2,
                )
                if attendance_statuses_yesterday["late"]
                else 0,
                "period": "Yesterday",
                "isNegativeGood": True,
            }

            employee_aged_report = request.env["hr.employee"]._get_emloyee_aged_report(
                date_from=date.today() - timedelta(days=365)
            )

            data["employee"] = {
                "label": "Employee",
                "current": employee_aged_report["current"],
                "growth": round(
                    (employee_aged_report["hired"] - employee_aged_report["fired"])
                    / employee_aged_report["current"]
                    * 100,
                    2,
                ),
                "period": COMPARISON_PERIOD[365],
            }
            data["leaves"] = {
                "label": "Leaves(days)",
                **self._get_model_comparison(
                    "hr.leave",
                    60,
                    date_field="date_from",
                    groupby=["holiday_status_id"],
                    domain=[("state", "=", "validate")],
                    aggregates=["number_of_days:sum"],
                ),
            }

            data["timesheet"] = {
                "label": "Timesheet(hrs)",
                **self._get_model_comparison(
                    "account.analytic.line",
                    30,
                    groupby=["project_id"],
                    aggregates=["unit_amount:sum"],
                ),
            }
        elif role == "manager":
            attendance_statuses_today = (
                request.env["hr.employee"]
                .sudo()
                .with_company(PARENT_COMPANY_ID)
                ._get_employee_status_at_date(
                    date=date.today(),
                    employee_domain=[],
                )
            )

            employee_aged_report = (
                request.env["hr.employee"]
                .sudo()
                .with_company(PARENT_COMPANY_ID)
                ._get_emloyee_aged_report(
                    date_from=date.today() - timedelta(days=365),
                    domain=[],
                )
            )

            data["present"] = {
                "label": "Present Today",
                "current": attendance_statuses_today["present"],
            }
            data["absent"] = {
                "label": "Absent Today",
                "current": attendance_statuses_today["absent"],
            }

            data["employee"] = {
                "label": "Employee",
                "current": employee_aged_report["current"],
            }
            data["leave"] = {
                "label": "Leave",
                "current": attendance_statuses_today["leave"],
            }

        return {
            "status": 200,
            "data": data,
            "message": "data",
        }

    @http.route(
        "/mobile/api/today/summary",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def today_dashbord(self, **kw):

        attendance_statuses_today = request.env[
            "hr.employee"
        ]._get_employee_status_at_date(date=date.today())

        data = dict()
        data = {
            "employee": attendance_statuses_today,
            "timesheet": {
                **self._get_model_comparison(
                    "account.analytic.line",
                    1,
                    groupby=["project_id"],
                    aggregates=["unit_amount:sum"],
                ),
            },
        }

        return {
            "status": 200,
            "data": data,
            "message": "data",
        }

    def _get_child_department_ids(self, department_id):
        """Get all child department IDs recursively for a given department."""
        department = request.env["hr.department"].sudo().browse(int(department_id))
        child_departments = department.child_ids
        all_department_ids = [department_id]

        for child_dept in child_departments:
            all_department_ids.extend(self._get_child_department_ids(child_dept.id))

        return all_department_ids

    @http.route(
        "/mobile/api/employee",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def get_all_employee(self, **kw):

        state = kw.get("state")
        # department_id = kw.get("department_id")
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        # employee_id = (
        #     request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        # )

        domain = []
        # if request.env.user.hr_app_role != "admin":
        #     domain.append(("branch_id", "=", employee_id.branch_id.id))

        total_employees = (
            request.env["hr.employee"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .search(domain)
        )

        # Get attendance records for the date
        attendances = (
            request.env["hr.attendance"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .search([("date", "=", datetime.today())])
        )

        present_employee_ids = attendances.mapped("employee_id").filtered(
            lambda emp: emp in total_employees
        )

        # late_employee_ids = request.env["hr.employee"].sudo()

        # for employee_attendance in attendances.grouped("employee_id"):
        #     if attendances.grouped("employee_id")[employee_attendance][0].late_in_hrs:
        #         late_employee_ids |= employee_attendance

        # late_employee_ids = late_employee_ids.filtered(
        #     lambda emp: emp in total_employees
        # )

        absent_employee_ids = (
            request.env["hr.employee"]
            .sudo()
            .search([("id", "not in", present_employee_ids.ids)])
            .filtered(lambda emp: emp in total_employees)
        )

        leave_employee_ids = total_employees.filtered(lambda emp: emp.is_absent)

        if not state:
            employee = total_employees
        elif state == "present":
            employee = present_employee_ids
        elif state == "absent":
            employee = absent_employee_ids
        elif state == "leave":
            employee = leave_employee_ids

        return {
            "status": 200,
            "message": "Employee",
            "data": employee.web_read(EMPLOYEE_SPECIFICATION),
        }

    @http.route(
        "/mobile/api/departments",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def get_all_departments(self, **kw):
        departments = request.env["hr.department"].sudo().search([])
        return {
            "status": 200,
            "message": "Departments",
            "data": departments.read(["id", "name", "display_name"]),
        }

    @http.route(
        "/mobile/api/branches",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def get_all_branches(self, **kw):
        branches = request.env["hr.branch"].sudo().search([])
        return {
            "status": 200,
            "message": "branches",
            "data": branches.read(["id", "name", "display_name"]),
        }

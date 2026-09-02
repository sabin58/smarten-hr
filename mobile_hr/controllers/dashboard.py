import pytz
from odoo import http
from odoo.http import request
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.addons.mobile_auth.utils import get_hr_company_id, get_hr_employee
from datetime import datetime, timedelta

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

    def _get_local_now(self):
        """Now in the user's timezone.

        Stored datetimes are UTC while the dashboard reasons in calendar days,
        so every window boundary has to be built from a localized 'now'.
        """
        return datetime.now(pytz.utc).astimezone(
            pytz.timezone(request.env.user.tz or "UTC")
        )

    def _get_local_today(self):
        return self._get_local_now().date()

    def _get_aggregate_sum(
        self, model_name, domain, groupby, aggregates, count_groups=False
    ):
        """Sum the first aggregate of a ``_read_group`` over all its groups.

        ``_read_group`` returns the groupby values first and the aggregates
        after them, so the aggregate column is at index ``len(groupby)``. With
        ``count_groups`` the number of groups is returned instead, which is how
        distinct days are counted.
        """
        rows = (
            request.env[model_name]
            .sudo()
            ._read_group(domain=domain, groupby=groupby, aggregates=aggregates)
        )
        if count_groups:
            return len(rows)
        return sum((row[len(groupby)] or 0) for row in rows)

    def _growth_card(self, label, current, before, period, is_negative_good=False):
        card = {
            "label": label,
            "current": current,
            "before": before,
            "growth": round((current - before) / before * 100, 2) if before else 0,
            "period": period,
        }
        if is_negative_good:
            card["isNegativeGood"] = True
        return card

    def _get_model_comparison(
        self,
        model_name: str,
        comparison_day: int = 1,
        date_field: str = "date",
        domain=None,
        groupby=None,
        aggregates=None,
        count_groups=False,
    ):
        domain = domain or []
        groupby = groupby or []
        aggregates = aggregates or ["__count"]

        local_now = self._get_local_now()
        boundaries = [
            local_now - timedelta(days=comparison_day * offset) for offset in range(3)
        ]

        # Date fields are compared on calendar days, datetime fields are stored
        # in UTC and must be compared against naive UTC boundaries.
        if request.env[model_name]._fields[date_field].type == "date":
            boundaries = [boundary.date() for boundary in boundaries]
        else:
            boundaries = [
                boundary.astimezone(pytz.utc).replace(tzinfo=None)
                for boundary in boundaries
            ]

        today, start_range_today, start_range_before = boundaries

        current_stats_count = self._get_aggregate_sum(
            model_name,
            domain + [(date_field, "<=", today), (date_field, ">", start_range_today)],
            groupby,
            aggregates,
            count_groups,
        )
        before_stats_count = self._get_aggregate_sum(
            model_name,
            domain
            + [
                (date_field, "<=", start_range_today),
                (date_field, ">", start_range_before),
            ],
            groupby,
            aggregates,
            count_groups,
        )

        return {
            "current": round(current_stats_count, 2),
            "before": round(before_stats_count, 2),
            "growth": round(
                (current_stats_count - before_stats_count) / before_stats_count * 100, 2
            )
            if before_stats_count
            else 0,
            "period": COMPARISON_PERIOD.get(
                comparison_day, f"Last {comparison_day} Days"
            ),
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
        role = request.env.user.hr_app_role
        data = dict()

        PARENT_COMPANY_ID = get_hr_company_id()

        employee_id = get_hr_employee()

        today = self._get_local_today()
        yesterday = today - timedelta(days=1)
        last_year = today - timedelta(days=365)

        HrEmployee = request.env["hr.employee"].sudo().with_company(PARENT_COMPANY_ID)

        if role in ("admin", "manager", "user"):
            # An admin sees the whole company, a manager only their own
            # department tree.
            employee_domain = []
            if role == "manager":
                if employee_id.department_id:
                    employee_domain = [
                        (
                            "department_id",
                            "in",
                            self._get_child_department_ids(
                                employee_id.department_id.id
                            ),
                        )
                    ]
                else:
                    employee_domain = [("id", "=", employee_id.id)]

            attendance_statuses_today = HrEmployee._get_employee_status_at_date(
                date=today, employee_domain=employee_domain
            )
            attendance_statuses_yesterday = HrEmployee._get_employee_status_at_date(
                date=yesterday, employee_domain=employee_domain
            )

            employee_aged_report = HrEmployee._get_emloyee_aged_report(
                date_from=last_year, domain=employee_domain
            )

            data["present"] = self._growth_card(
                "Present Today",
                attendance_statuses_today["present"],
                attendance_statuses_yesterday["present"],
                "Yesterday",
            )
            data["absent"] = self._growth_card(
                "Absent Today",
                attendance_statuses_today["absent"],
                attendance_statuses_yesterday["absent"],
                "Yesterday",
            )
            data["employee"] = self._growth_card(
                "Employee",
                employee_aged_report["current"],
                # Head count a year ago, derived from the net movement since.
                employee_aged_report["current"]
                - (employee_aged_report["hired"] - employee_aged_report["fired"]),
                COMPARISON_PERIOD[365],
            )

            data["leave"] = {
                "label": "Leave",
                "current": attendance_statuses_today["leave"],
            }

        else:
            # Regular employee: the same cards, scoped to their own record.
            if not employee_id:
                return {
                    "status": 400,
                    "data": None,
                    "message": "No employee profile is linked to your account !!",
                }

            employee_domain = [("employee_id", "=", employee_id.id)]

            data["present"] = {
                "label": "Present(days)",
                # Grouped per day so several check-ins in a day count once.
                **self._get_model_comparison(
                    "hr.attendance",
                    30,
                    domain=employee_domain,
                    groupby=["date:day"],
                    count_groups=True,
                ),
            }
            data["leaves"] = {
                "label": "Leaves(days)",
                **self._get_model_comparison(
                    "hr.leave",
                    60,
                    date_field="date_from",
                    domain=employee_domain + [("state", "=", "validate")],
                    aggregates=["number_of_days:sum"],
                ),
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
        ]._get_employee_status_at_date(date=self._get_local_today())

        data = dict()
        data = {
            "employee": attendance_statuses_today,
            "timesheet": {
                **self._get_model_comparison(
                    "account.analytic.line",
                    1,
                    aggregates=["unit_amount:sum"],
                ),
            },
        }

        return {
            "status": 200,
            "data": data,
            "message": "data",
        }

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
        PARENT_COMPANY_ID = get_hr_company_id()

        # employee_id = (
        #     get_hr_employee()
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

from datetime import date, datetime, timedelta

import pytz
from odoo import SUPERUSER_ID
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.http import request, Controller, route
from odoo.exceptions import UserError, ValidationError


TIME_OFF_SPECIFICATIONS = {
    "id": {},
    "employee_id": {"fields": {"display_name": {}, "mobile_image_url": {}}},
    "holiday_status_id": {
        "fields": {
            "display_name": {},
        },
    },
    "date_from": {},
    "date_to": {},
    "name": {},
    "display_name": {},
    "duration_display": {},
    "state": {},
    "number_of_days": {},
    "number_of_hours": {},
    "request_date_from": {},
    "request_date_to": {},
    "notes": {},
    "attachment_ids": {},
    "can_cancel": {},
    "can_approve": {},
    "private_name": {},
}


class TimeOffController(Controller):
    def _get_child_department_ids(self, department_id):
        """Get all child department IDs recursively for a given department."""
        department = request.env["hr.department"].sudo().browse(int(department_id))
        child_departments = department.child_ids
        all_department_ids = [department_id]

        for child_dept in child_departments:
            all_department_ids.extend(self._get_child_department_ids(child_dept.id))

        return all_department_ids

    @route("/mobile/api/timeoff", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def get_all_timeoff(self, **kwargs):

        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )

        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1
        branch_id = kwargs.get("branch_id")
        state = kwargs.get("state")

        domain = []
        user = request.env.user

        if user.hr_app_role != "admin" and user.hr_app_role != "manager":
            domain.append(("employee_id", "=", employee_id.id))

        if user.hr_app_role == "admin" and branch_id:
            domain.append(("employee_id.branch_id", "=", branch_id))

        if user.hr_app_role == "manager":
            domain.append(("employee_id.branch_id", "=", employee_id.branch_id.id))

        if state:
            domain.append(("state", "=", state))

        leaves = (
            request.env["hr.leave"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .web_search_read(
                domain,
                TIME_OFF_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
            )
        )

        return {"status": 200, "data": leaves, "message": "timeoff"}

    @route(
        "/mobile/api/timeoff/<int:id>", type="json", auth="public", csrf=False, cors="*"
    )
    @login_required()
    def get_timeoff_detail(self, id, **kwargs):

        leave = request.env["hr.leave"].sudo().browse(id)

        if not leave:
            return {"status": 404, "data": None, "message": "Time off not found!! "}

        return {
            "status": 200,
            "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
            "message": "timeoff",
        }

    @route(
        "/mobile/api/profile/dashboard",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_profile_dashboard(self, **kwargs):
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )

        leaves_data = (
            request.env["hr.leave.type"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .get_allocation_data_request(datetime.now(), False)
        )

        employee_tz = employee_id.tz
        attendance_data = (
            employee_id.with_user(SUPERUSER_ID)
            .with_company(PARENT_COMPANY_ID)
            .get_attendance_report(
                datetime.now().astimezone(pytz.timezone(employee_tz))
                - timedelta(days=30),
                datetime.now().astimezone(pytz.timezone(employee_tz))
                - timedelta(days=1),
            )
        )

        leave_summary = {"remaining": 0, "total": 0, "taken": 0}
        for leave in leaves_data:
            leave_summary["remaining"] += leave[1]["remaining_leaves"]
            leave_summary["taken"] += leave[1]["leaves_taken"]
            leave_summary["total"] += leave[1]["max_leaves"]

        payslip = (
            request.env["hr.payslip"]
            .sudo()
            .search_count(
                [
                    ("employee_id", "=", employee_id.id),
                    ("state", "not in", ["cancel", "draft"]),
                ]
            )
        )

        return {
            "status": 200,
            "data": {
                "leaves": {"summary": leave_summary, "breakdown": leaves_data},
                "attendance": attendance_data,
                "payslip": {"count": payslip},
            },
            "message": "profile dashboard",
        }

    @route("/mobile/api/timeoff/my", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def get_my_timeoff(self, **kwargs):

        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee = request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id

        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1
        state = kwargs.get("state")
        # data = []
        domain = [("employee_id", "=", employee.id)]

        if state:
            domain.append(("state", "=", state))
        leaves = (
            request.env["hr.leave"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .web_search_read(
                domain,
                TIME_OFF_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
            )
        )

        return {"status": 200, "data": leaves, "message": "timeoff"}

    @route(
        "/mobile/api/timeoff/types", type="json", auth="public", csrf=False, cors="*"
    )
    @login_required()
    def get_timeoff_types(self, **kwargs):
        """Get available leave types for the employee"""
        # user = request.env.user
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee = request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "Employee not found for this user",
            }

        if kwargs.get("employee_id") and request.env.user.hr_app_role != "user":
            employee = (
                request.env["hr.employee"]
                .sudo()
                .with_company(PARENT_COMPANY_ID)
                .browse(int(kwargs["employee_id"]))
            )

        leave_types = (
            request.env["hr.leave.type"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .with_context(
                {
                    "employee_id": employee.id,
                    "default_date_from": datetime.now(),
                    "default_date_to": datetime.now(),
                }
            )
            .search(
                domain=[
                    "|",
                    ["requires_allocation", "=", "no"],
                    "&",
                    ["has_valid_allocation", "=", True],
                    "|",
                    ["allows_negative", "=", True],
                    "&",
                    ["virtual_remaining_leaves", ">", 0],
                    ["allows_negative", "=", False],
                ]
            )
        )
        types_data = []
        for leave_type in leave_types:
            types_data.append(
                {
                    "id": leave_type.id,
                    "name": leave_type.name,
                    "requires_allocation": leave_type.requires_allocation,
                    "remaining_leaves": leave_type.virtual_remaining_leaves,
                    "max_leaves": leave_type.max_leaves,
                    "request_unit": leave_type.request_unit,
                    "color": leave_type.color,
                    "employee_requests": leave_type.employee_requests,
                }
            )

        return {"status": 200, "data": types_data, "message": "timeoff types"}

    @route(
        "/mobile/api/timeoff/create", type="json", auth="public", csrf=False, cors="*"
    )
    @login_required()
    def create_timeoff(self, **kwargs):
        """Create a new time off request"""
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id
        employee = request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id

        if kwargs.get("employee_id") and request.env.user.hr_app_role != "user":
            employee = (
                request.env["hr.employee"]
                .sudo()
                .with_company(PARENT_COMPANY_ID)
                .browse(int(kwargs["employee_id"]))
            )
        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "Employee not found for this user",
            }

        # Required fields
        holiday_status_id = kwargs.get("holiday_status_id")
        request_date_from = kwargs.get("request_date_from")
        request_date_to = kwargs.get("request_date_to")

        if not holiday_status_id:
            return {
                "status": 400,
                "data": None,
                "message": "Leave type is required",
            }

        if not request_date_from:
            return {
                "status": 400,
                "data": None,
                "message": "Start date is required",
            }

        if not request_date_to:
            return {
                "status": 400,
                "data": None,
                "message": "End date is required",
            }

        # Validate dates
        try:
            date_from = datetime.strptime(request_date_from, "%Y-%m-%d").date()
            date_to = datetime.strptime(request_date_to, "%Y-%m-%d").date()
        except ValueError:
            return {
                "status": 400,
                "data": None,
                "message": "Invalid date format. Use YYYY-MM-DD",
            }

        if date_from > date_to:
            return {
                "status": 400,
                "data": None,
                "message": "Start date cannot be after end date",
            }

        # Check if leave type exists and is valid
        leave_type = (
            request.env["hr.leave.type"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .browse(holiday_status_id)
        )
        if not leave_type.exists():
            return {
                "status": 404,
                "data": None,
                "message": "Leave type not found",
            }

        # Prepare values for creating leave
        leave_values = {
            "employee_id": employee.id,
            "holiday_status_id": holiday_status_id,
            "request_date_from": request_date_from,
            "request_date_to": request_date_to,
            "private_name": kwargs.get("name", ""),
            # "notes": kwargs.get("notes", ""),
        }

        # Handle half-day requests
        if kwargs.get("request_unit_half"):
            leave_values["request_unit_half"] = True
            if kwargs.get("request_date_from_period"):
                leave_values["request_date_from_period"] = kwargs.get(
                    "request_date_from_period"
                )

        # Handle custom hour requests
        if kwargs.get("request_unit_hours"):
            leave_values["request_unit_hours"] = True
            if kwargs.get("request_hour_from"):
                leave_values["request_hour_from"] = kwargs.get("request_hour_from")
            if kwargs.get("request_hour_to"):
                leave_values["request_hour_to"] = kwargs.get("request_hour_to")

        try:
            leave = (
                request.env["hr.leave"]
                .sudo()
                .with_context(
                    mail_create_nosubscribe=True,
                    mail_create_nolog=True,
                )
                .create(leave_values)
            )

            return {
                "status": 201,
                "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
                "message": "Time off request created successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

    @route(
        "/mobile/api/timeoff/<int:id>",
        type="json",
        auth="public",
        csrf=False,
        methods=["PUT"],
        cors="*",
    )
    @login_required()
    def update_timeoff(self, id, **kwargs):
        """Update an existing time off request"""
        user = request.env.user
        leave = request.env["hr.leave"].sudo().browse(id)

        if not leave.exists():
            return {
                "status": 404,
                "data": None,
                "message": "Time off request not found",
            }

        # Check if user can modify this leave
        if user.hr_app_role != "admin" and leave.employee_id != user.employee_id:
            return {
                "status": 403,
                "data": None,
                "message": "You can only modify your own time off requests",
            }

        # Cannot modify validated/cancelled/refused leaves
        if leave.state not in ["confirm"]:
            return {
                "status": 400,
                "data": None,
                "message": f"Cannot modify time off in '{leave.state}' state",
            }

        update_values = {}

        if kwargs.get("holiday_status_id"):
            update_values["holiday_status_id"] = kwargs.get("holiday_status_id")

        if kwargs.get("request_date_from"):
            try:
                datetime.strptime(kwargs.get("request_date_from"), "%Y-%m-%d")
                update_values["request_date_from"] = kwargs.get("request_date_from")
            except ValueError:
                return {
                    "status": 400,
                    "data": None,
                    "message": "Invalid start date format. Use YYYY-MM-DD",
                }

        if kwargs.get("request_date_to"):
            try:
                datetime.strptime(kwargs.get("request_date_to"), "%Y-%m-%d")
                update_values["request_date_to"] = kwargs.get("request_date_to")
            except ValueError:
                return {
                    "status": 400,
                    "data": None,
                    "message": "Invalid end date format. Use YYYY-MM-DD",
                }

        if "name" in kwargs:
            update_values["private_name"] = kwargs.get("name")

        if "notes" in kwargs:
            update_values["notes"] = kwargs.get("notes")

        if not update_values:
            return {
                "status": 400,
                "data": None,
                "message": "No fields to update",
            }

        try:
            leave.sudo().write(update_values)
            request.env.cr.commit()

            return {
                "status": 200,
                "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
                "message": "Time off request updated successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

    @route(
        "/mobile/api/timeoff/<int:id>/cancel",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def cancel_timeoff(self, id, **kwargs):
        """Cancel a time off request"""
        user = request.env.user
        leave = request.env["hr.leave"].sudo().browse(id)

        if not leave.exists():
            return {
                "status": 404,
                "data": None,
                "message": "Time off request not found",
            }

        # Check if user can cancel this leave
        if user.hr_app_role != "admin" and leave.employee_id != user.employee_id:
            return {
                "status": 403,
                "data": None,
                "message": "You can only cancel your own time off requests",
            }

        if not leave.can_cancel:
            return {
                "status": 400,
                "data": None,
                "message": "This time off request cannot be cancelled",
            }

        try:
            leave.sudo().action_cancel()
            request.env.cr.commit()

            return {
                "status": 200,
                "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
                "message": "Time off request cancelled successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

    @route(
        "/mobile/api/timeoff/<int:id>/approve",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def approve_timeoff(self, id, **kwargs):
        """Approve a time off request (for managers/admins)"""
        user = request.env.user

        if user.hr_app_role not in ["admin", "manager"]:
            return {
                "status": 403,
                "data": None,
                "message": "Only admins/managers can approve time off requests",
            }

        leave = request.env["hr.leave"].sudo().browse(id)

        if not leave.exists():
            return {
                "status": 404,
                "data": None,
                "message": "Time off request not found",
            }

        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee = request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id

        if employee.id == leave.employee_id.id:
            return {
                "status": 403,
                "data": None,
                "message": "You cannot approve own leave !!",
            }

        if leave.state not in ["confirm", "validate1"]:
            return {
                "status": 400,
                "data": None,
                "message": f"Cannot approve time off in '{leave.state}' state",
            }

        try:
            leave.with_user(SUPERUSER_ID).action_approve()
            request.env.cr.commit()

            return {
                "status": 200,
                "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
                "message": "Time off request approved successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

    @route(
        "/mobile/api/timeoff/<int:id>/validate",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def validate_timeoff(self, id, **kwargs):
        user = request.env.user

        leave = request.env["hr.leave"].sudo().browse(id)

        if user.hr_app_role not in ["admin", "manager"]:
            return {
                "status": 403,
                "data": None,
                "message": "Only admins/managers can validate time off requests",
            }
        if leave.state not in ["confirm", "validate1"]:
            return {
                "status": 400,
                "data": None,
                "message": f"Cannot approve time off in '{leave.state}' state",
            }

        try:
            leave.with_user(SUPERUSER_ID).action_validate()
            request.env.cr.commit()

            return {
                "status": 200,
                "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
                "message": "Time off request approved successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

    @route(
        "/mobile/api/timeoff/<int:id>/refuse",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def refuse_timeoff(self, id, **kwargs):
        """Refuse a time off request (for managers/admins)"""

        leave = request.env["hr.leave"].sudo().browse(id)

        if not leave.can_approve:
            return {
                "status": 403,
                "data": None,
                "message": "Only admins/managers can refuse time off requests",
            }

        if not leave.exists():
            return {
                "status": 404,
                "data": None,
                "message": "Time off request not found",
            }

        if leave.state not in ["confirm", "validate1"]:
            return {
                "status": 400,
                "data": None,
                "message": f"Cannot refuse time off in '{leave.state}' state",
            }

        try:
            leave.sudo().action_refuse()
            request.env.cr.commit()

            return {
                "status": 200,
                "data": leave.web_read(TIME_OFF_SPECIFICATIONS)[0],
                "message": "Time off request refused successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

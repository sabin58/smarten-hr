# -*- coding: utf-8 -*-

from datetime import datetime, timezone

from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Controller, route
from odoo.tools.mail import html2plaintext

from .message import get_record_messages


MOBILE_APPROVAL_TYPES = ["attendance", "advance_salary"]

CATEGORY_SPECIFICATIONS = {
    "name": {},
    "display_name": {},
    "description": {},
    "approval_type": {},
    "has_date": {},
    "has_period": {},
    "has_amount": {},
    "has_quantity": {},
    "has_reference": {},
    "has_location": {},
    "has_partner": {},
    "requirer_document": {},
    "approval_minimum": {},
    "automated_sequence": {},
    "manager_approval": {},
}

APPROVAL_SPECIFICATIONS = {
    "name": {},
    "display_name": {},
    "category_id": {"fields": {"display_name": {}}},
    "approval_type": {},
    "request_owner_id": {"fields": {"display_name": {}, "name": {}}},
    "request_status": {},
    "user_status": {},
    "date": {},
    "date_start": {},
    "date_end": {},
    "date_confirmed": {},
    "amount": {},
    "quantity": {},
    "reference": {},
    "location": {},
    "reason": {},
    "has_date": {},
    "has_period": {},
    "has_amount": {},
    "has_quantity": {},
    "has_reference": {},
    "has_location": {},
    "requirer_document": {},
    "attachment_number": {},
    "approver_ids": {
        "fields": {
            "user_id": {"fields": {"display_name": {}, "name": {}}},
            "status": {},
            "required": {},
            "sequence": {},
        },
    },
}


def parse_datetime(value, field_label):
    """An ISO 8601 datetime from the app, as the naive utc Odoo stores.

    The app sends the local time of the employee along with its offset, e.g.
    ``2026-08-20T12:53:00+05:45``. A value without an offset is taken as utc,
    the way the ORM reads its own datetimes.

    :raise ValueError: with a message the endpoint hands back as is
    """
    try:
        parsed = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValueError(
            f"Invalid {field_label} format. Use an ISO 8601 datetime, "
            f"e.g. 2026-08-20T12:53:00+05:45"
        )

    if parsed.tzinfo:
        parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)

    return parsed


class ApprovalController(Controller):
    def _get_parent_company_id(self):
        return request.env.company.parent_id.id or request.env.company.id

    def _get_my_employee(self):
        return (
            request.env.user.sudo()
            .with_company(self._get_parent_company_id())
            .employee_id
        )

    def _get_categories(self, approval_type=None):
        parent_company_id = self._get_parent_company_id()

        domain = [
            (
                "approval_type",
                "in",
                [approval_type] if approval_type else MOBILE_APPROVAL_TYPES,
            ),
            ("company_id", "in", [parent_company_id, request.env.company.id]),
        ]

        return (
            request.env["approval.category"]
            .sudo()
            .with_company(parent_company_id)
            .search(domain, order="sequence, id")
        )

    def _get_requests(self):
        return (
            request.env["approval.request"]
            .sudo()
            .with_company(self._get_parent_company_id())
        )

    def _get_scope_domain(self, **kwargs):
        user = request.env.user
        domain = [("approval_type", "in", MOBILE_APPROVAL_TYPES)]

        if user.hr_app_role == "admin":
            if kwargs.get("department_id"):
                domain.append(
                    (
                        "request_owner_id.employee_ids.department_id",
                        "=",
                        int(kwargs["department_id"]),
                    )
                )
            return domain

        if user.hr_app_role == "manager":
            department = self._get_my_employee().department_id
            return domain + [
                "|",
                "|",
                ("request_owner_id", "=", user.id),
                ("approver_ids.user_id", "=", user.id),
                ("request_owner_id.employee_ids.department_id", "=", department.id),
            ]

        return domain + [
            "|",
            ("request_owner_id", "=", user.id),
            ("approver_ids.user_id", "=", user.id),
        ]

    def _get_extra_domain(self, **kwargs):
        """The filters every list endpoint understands."""
        domain = []

        if kwargs.get("approval_type"):
            domain.append(("approval_type", "=", kwargs["approval_type"]))

        if kwargs.get("request_status"):
            domain.append(("request_status", "=", kwargs["request_status"]))

        if kwargs.get("category_id"):
            domain.append(("category_id", "=", int(kwargs["category_id"])))

        return domain

    def _can_read(self, approval):
        """Whether the request is inside the scope of the logged in user."""
        return bool(approval.filtered_domain(self._get_scope_domain()))

    def _get_values(self, category, kwargs):
        values = {}

        for field_name, label in (
            ("date", "date"),
            ("date_start", "start date"),
            ("date_end", "end date"),
        ):
            if kwargs.get(field_name):
                values[field_name] = parse_datetime(kwargs[field_name], label)

        for field_name in ("amount", "quantity"):
            if kwargs.get(field_name) is not None:
                values[field_name] = float(kwargs[field_name])

        for field_name in ("reference", "location", "reason"):
            if kwargs.get(field_name) is not None:
                values[field_name] = kwargs[field_name]

        if kwargs.get("name") and not category.automated_sequence:
            values["name"] = kwargs["name"]

        return values

    def _check_required_values(self, category, values):
        if category.approval_type == "attendance":
            if not values.get("date_start") or not values.get("date_end"):
                return (
                    "Period (start and end date) is required for an attendance request"
                )

        if category.approval_type == "advance_salary":
            if not values.get("amount"):
                return "Amount is required for an advance salary request"
            if values["amount"] < 0:
                return "Amount of an advance salary request must be positive"

        if values.get("date_start") and values.get("date_end"):
            if values["date_start"] > values["date_end"]:
                return "Start date cannot be after end date"

        return None

    @route(
        "/mobile/api/approval/categories",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_approval_categories(self, **kwargs):
        categories = self._get_categories(kwargs.get("approval_type"))
        return {
            "status": 200,
            "data": categories.web_read(CATEGORY_SPECIFICATIONS),
            "message": "approval categories",
        }

    @route("/mobile/api/approval", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def get_all_approvals(self, **kwargs):
        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        domain = self._get_scope_domain(**kwargs) + self._get_extra_domain(**kwargs)

        approvals = self._get_requests().web_search_read(
            domain,
            APPROVAL_SPECIFICATIONS,
            offset=limit * (page - 1),
            limit=limit,
            order="create_date desc",
        )

        return {"status": 200, "data": approvals, "message": "approvals"}

    @route("/mobile/api/approval/my", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def get_my_approvals(self, **kwargs):
        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        domain = [
            ("approval_type", "in", MOBILE_APPROVAL_TYPES),
            ("request_owner_id", "=", request.env.user.id),
        ] + self._get_extra_domain(**kwargs)

        approvals = self._get_requests().web_search_read(
            domain,
            APPROVAL_SPECIFICATIONS,
            offset=limit * (page - 1),
            limit=limit,
            order="create_date desc",
        )

        return {"status": 200, "data": approvals, "message": "approvals"}

    @route(
        "/mobile/api/approval/to-review",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_approvals_to_review(self, **kwargs):
        """The requests waiting for a decision of the logged in user."""
        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        domain = [
            ("approval_type", "in", MOBILE_APPROVAL_TYPES),
            ("approver_ids.user_id", "=", request.env.user.id),
            ("request_status", "=", "pending"),
        ] + self._get_extra_domain(**kwargs)

        approvals = self._get_requests().web_search_read(
            domain,
            APPROVAL_SPECIFICATIONS,
            offset=limit * (page - 1),
            limit=limit,
            order="create_date desc",
        )

        return {"status": 200, "data": approvals, "message": "approvals to review"}

    @route(
        "/mobile/api/approval/submit",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def submit_approval(self, **kwargs):

        category = self._get_categories(kwargs.get("approval_type"))
        if not category:
            return {"status": 400, "data": None, "message": "Invalid Category Id !!"}

        owner = request.env.user

        try:
            values = self._get_values(category, kwargs)
        except ValueError as error:
            return {"status": 400, "data": None, "message": str(error)}

        error_message = self._check_required_values(category, values)
        if error_message:
            return {"status": 400, "data": None, "message": error_message}

        values.update({"category_id": category.id, "request_owner_id": owner.id})
        values.setdefault("name", category.name)

        try:
            approval = self._get_requests().create(values)
            approval.action_confirm()
        except (UserError, ValidationError) as error:
            return {"status": 400, "data": None, "message": str(error)}
        except Exception as error:
            return {"status": 500, "data": None, "message": str(error)}

        return {
            "status": 201,
            "data": approval.web_read(APPROVAL_SPECIFICATIONS)[0],
            "message": "Approval Submitted Successfully",
        }

    @route(
        "/mobile/api/approval/<int:id>",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_approval_detail(self, id, **kwargs):
        """One request with its chatter."""
        message_limit = kwargs.get("message_limit") or 80

        approval = self._get_requests().browse(id).exists()

        if not approval or approval.approval_type not in MOBILE_APPROVAL_TYPES:
            return {
                "status": 404,
                "data": None,
                "message": "Approval request not found",
            }

        if not self._can_read(approval):
            return {
                "status": 403,
                "data": None,
                "message": "You cannot access this approval request",
            }

        data = approval.web_read(APPROVAL_SPECIFICATIONS)[0]
        data["messages"] = get_record_messages(
            "approval.request", approval.id, message_limit
        )
        data["reason"] = html2plaintext(data["reason"] or "", include_references=False)

        return {"status": 200, "data": data, "message": "approval"}

    @route(
        "/mobile/api/approval/<int:id>/approve",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def approve_approval(self, id, **kwargs):
        """Approve as the logged in user."""
        approval = self._get_requests().browse(id).exists()

        if not approval or approval.approval_type not in MOBILE_APPROVAL_TYPES:
            return {
                "status": 404,
                "data": None,
                "message": "Approval request not found",
            }

        if approval.user_status != "pending":
            return {
                "status": 403,
                "data": None,
                "message": "This approval request is not waiting for your approval",
            }

        try:
            approval.action_approve()

            return {
                "status": 200,
                "data": approval.web_read(APPROVAL_SPECIFICATIONS)[0],
                "message": "Approval request approved successfully",
            }
        except (UserError, ValidationError) as error:
            return {"status": 400, "data": None, "message": str(error)}
        except Exception as error:
            return {"status": 500, "data": None, "message": str(error)}

    @route(
        "/mobile/api/approval/<int:id>/refuse",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def refuse_approval(self, id, **kwargs):
        """Refuse as the logged in user."""
        approval = self._get_requests().browse(id).exists()

        if not approval or approval.approval_type not in MOBILE_APPROVAL_TYPES:
            return {
                "status": 404,
                "data": None,
                "message": "Approval request not found",
            }

        if approval.user_status != "pending":
            return {
                "status": 403,
                "data": None,
                "message": "This approval request is not waiting for your approval",
            }

        try:
            approval.action_refuse()

            return {
                "status": 200,
                "data": approval.web_read(APPROVAL_SPECIFICATIONS)[0],
                "message": "Approval request refused successfully",
            }
        except (UserError, ValidationError) as error:
            return {"status": 400, "data": None, "message": str(error)}
        except Exception as error:
            return {"status": 500, "data": None, "message": str(error)}

    @route(
        "/mobile/api/approval/<int:id>/cancel",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def cancel_approval(self, id, **kwargs):
        """Cancel a request the logged in user created."""
        approval = self._get_requests().browse(id).exists()

        if not approval or approval.approval_type not in MOBILE_APPROVAL_TYPES:
            return {
                "status": 404,
                "data": None,
                "message": "Approval request not found",
            }

        if (
            request.env.user.hr_app_role != "admin"
            and approval.request_owner_id != request.env.user
        ):
            return {
                "status": 403,
                "data": None,
                "message": "You can only cancel your own approval requests",
            }

        if approval.request_status in ["new", "cancel"]:
            return {
                "status": 400,
                "data": None,
                "message": f"Cannot cancel an approval request in '{approval.request_status}' state",
            }

        try:
            approval.action_cancel()

            return {
                "status": 200,
                "data": approval.web_read(APPROVAL_SPECIFICATIONS)[0],
                "message": "Approval request cancelled successfully",
            }
        except (UserError, ValidationError) as error:
            return {"status": 400, "data": None, "message": str(error)}
        except Exception as error:
            return {"status": 500, "data": None, "message": str(error)}

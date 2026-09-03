import base64

from odoo.addons.mobile_auth.controllers.auth import login_required, make_response
from odoo.addons.mobile_auth.utils import get_hr_employee
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Controller, route

from .message import get_record_messages

CATEGORY_SPECIFICATIONS = {
    "name": {},
    "display_name": {},
    "standard_price": {},
    "uom_id": {"fields": {"display_name": {}}},
}

EXPENSE_SPECIFICATIONS = {
    "name": {},
    "date": {},
    "description": {},
    "state": {},
    "quantity": {},
    "total_amount_currency": {},
    "product_id": {"fields": {"display_name": {}, "name": {}}},
    "employee_id": {"fields": {"display_name": {}}},
    "currency_id": {"fields": {"display_name": {}}},
    # Kept by mobile_hr on hr.expense itself, 19.0 renamed both.
    "approved_by": {"fields": {"display_name": {}}},
    "approved_on": {},
}


class ExpenseController(Controller):
    def _serialize_attachments(self, attachments):
        """Receipt metadata plus a url the app can load straight into an image."""
        base_url = request.env["ir.config_parameter"].sudo().get_base_url()

        data = []
        for attachment in attachments:
            # The employee is a portal user and cannot read /web/content
            # directly, so the url carries the access token instead.
            access_token = attachment.generate_access_token()[0]
            data.append(
                {
                    "id": attachment.id,
                    "name": attachment.name,
                    "mimetype": attachment.mimetype,
                    "file_size": attachment.file_size,
                    "url": f"{base_url}/web/content/{attachment.id}"
                    f"?access_token={access_token}",
                }
            )

        return data

    def _create_attachments(self, expense, uploads):
        """Store the uploaded receipt files against the expense.

        :param uploads: werkzeug FileStorage objects taken from the multipart
            body of the request
        :return: the created ir.attachment recordset
        """
        values = []
        for index, upload in enumerate(uploads, start=1):
            content = upload.read()

            if not content:
                continue

            values.append(
                {
                    "name": upload.filename or f"receipt-{index}",
                    "datas": base64.b64encode(content),
                    "res_model": "hr.expense",
                    "res_id": expense.id,
                }
            )

        if not values:
            return request.env["ir.attachment"].sudo()

        created = request.env["ir.attachment"].sudo().create(values)

        # Written straight onto the field instead of going through
        # attach_document(): that calls _message_set_main_attachment_id, which
        # hr_expense_extract overrides to auto-send the receipt to the IAP OCR
        # service. The scan costs credits and is not wanted here, so the hook
        # is bypassed while the receipt still shows as the main attachment.
        expense.sudo().message_main_attachment_id = created[-1].id

        return created

    def _is_approver(self, expense):
        """Whether the logged in user decides on this expense.

        19.0 dropped hr.expense.sheet, the manager of the expense itself now
        carries what the report used to. It is only filled from the expense
        manager of the employee or from their own manager, and when neither
        is set Odoo falls back to the department manager, so the same
        fallback is applied here rather than leaving the expense with nobody
        able to approve it.
        """
        if not expense:
            return False

        responsible = expense.manager_id or expense._get_default_responsible_for_approval()

        return bool(responsible) and request.env.user in responsible

    def _get_approver_domain(self):
        """Expenses waiting on the logged in user, with the same fallback."""
        uid = request.env.user.id

        return [
            "|",
            ("manager_id", "=", uid),
            "&",
            ("manager_id", "=", False),
            "|",
            ("employee_id.parent_id.user_id", "=", uid),
            ("employee_id.department_id.manager_id.user_id", "=", uid),
        ]

    @route(
        "/mobile/api/expense/categories",
        type="jsonrpc",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_expense_categories(self, **kwargs):

        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        categories = (
            request.env["product.product"]
            .sudo()
            .web_search_read(
                [("can_be_expensed", "=", True)],
                CATEGORY_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
            )
        )

        return {
            "status": 200,
            "data": categories,
            "message": "expense categories",
        }

    @route(
        "/mobile/api/expense/create",
        type="http",
        methods=["POST"],
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    @make_response
    def create_expense(self, **kwargs):

        name = kwargs.get("name")
        product_id = kwargs.get("product_id")
        date = kwargs.get("date")
        description = kwargs.get("description")
        total_amount = kwargs.get("total_amount")
        quantity = kwargs.get("quantity")

        # Multipart sends one part per file, and kwargs only keeps the last of
        # a repeated name, so the uploads are read off the request directly.
        uploads = request.httprequest.files.getlist("images")

        if not name:
            return {"status": 400, "data": None, "message": "Description is required"}

        employee = get_hr_employee()

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "No employee profile is linked to your account !!",
            }

        values = {
            "name": name,
            "employee_id": employee.id,
        }

        # Every form field arrives as a string, so the numbers are converted
        # here rather than handed to the ORM as text.
        try:
            if product_id:
                product = (
                    request.env["product.product"]
                    .sudo()
                    .browse(int(product_id))
                    .exists()
                )
                if not product or not product.can_be_expensed:
                    return {
                        "status": 404,
                        "data": None,
                        "message": "Expense category not found",
                    }
                values["product_id"] = product.id

            if quantity:
                values["quantity"] = float(quantity)

            if total_amount:
                values["total_amount_currency"] = float(total_amount)

        except (TypeError, ValueError):
            return {
                "status": 400,
                "data": None,
                "message": "product_id, quantity and total_amount must be numbers",
            }

        if date:
            values["date"] = date

        if description:
            values["description"] = description

        try:
            expense = request.env["hr.expense"].sudo().create(values)

            created_attachments = self._create_attachments(expense, uploads)

            # Straight to the approver. 19.0 submits the expense itself,
            # there is no report to create around it anymore.
            expense.action_submit()

            expense_data = expense.web_read(EXPENSE_SPECIFICATIONS)[0]
            expense_data["attachments"] = self._serialize_attachments(
                created_attachments
            )

            return {
                "status": 201,
                "data": expense_data,
                "message": "Expense submitted successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

    @route(
        "/mobile/api/expenses",
        type="jsonrpc",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_my_expenses(self, **kwargs):

        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1
        state = kwargs.get("state")
        to_approve = kwargs.get("to_approve")

        if to_approve:
            # Expenses whose report waits on the logged in user as approver.
            domain = self._get_approver_domain()
            if not state:
                domain.append(("state", "=", "submitted"))
        else:
            employee = get_hr_employee()

            if not employee:
                return {
                    "status": 400,
                    "data": None,
                    "message": "No employee profile is linked to your account !!",
                }

            domain = [("employee_id", "=", employee.id)]

        if state:
            domain.append(("state", "=", state))

        expenses = (
            request.env["hr.expense"]
            .sudo()
            .web_search_read(
                domain,
                EXPENSE_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
                order="date desc, id desc",
            )
        )

        return {
            "status": 200,
            "data": expenses,
            "message": "my expenses",
        }

    @route(
        "/mobile/api/expense/<int:expense_id>",
        type="jsonrpc",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_expense_detail(self, expense_id, **kwargs):

        message_limit = kwargs.get("message_limit") or 80

        expense = request.env["hr.expense"].sudo().browse(expense_id).exists()

        if not expense or not (
            expense.employee_id == get_hr_employee() or self._is_approver(expense)
        ):
            return {
                "status": 404,
                "data": None,
                "message": "Expense not found",
            }

        data = expense.web_read(EXPENSE_SPECIFICATIONS)[0]
        data["attachments"] = self._serialize_attachments(expense.attachment_ids)
        data["can_approve"] = self._is_approver(expense) and expense.state in (
            "draft",
            "submitted",
        )
        data["messages"] = get_record_messages("hr.expense", expense.id, 80)
        return {
            "status": 200,
            "data": data,
            "message": "expense",
        }

    def _get_expense_for_approval(self, expense_id):
        """Return the expense if the caller may decide on it.

        :return: a tuple of (hr.expense, error dict)
        """
        expense = request.env["hr.expense"].sudo().browse(expense_id).exists()

        if not expense:
            return (
                None,
                {
                    "status": 404,
                    "data": None,
                    "message": "Expense not found",
                },
            )

        # An expense that was never submitted has no approval state yet.
        if not expense.approval_state:
            return (
                None,
                {
                    "status": 400,
                    "data": None,
                    "message": "This expense has not been submitted yet !!",
                },
            )

        # can_approve on the model is bypassed by sudo, so the approver is
        # checked here: only the manager of the expense decides.
        if not self._is_approver(expense):
            return (
                None,
                {
                    "status": 403,
                    "data": None,
                    "message": "Only the approver of this expense can do that !!",
                },
            )

        if expense.state not in ("draft", "submitted"):
            return (
                None,
                {
                    "status": 400,
                    "data": None,
                    "message": "This expense is not waiting for approval anymore !!",
                },
            )

        return expense, None

    @route(
        "/mobile/api/expense/<int:expense_id>/approve",
        type="jsonrpc",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def approve_expense(self, expense_id, **kwargs):

        expense, error = self._get_expense_for_approval(expense_id)

        if error:
            return error

        try:
            # _do_approve rather than action_approve, which returns a
            # duplicate-check wizard action the app cannot render.
            expense._do_approve()

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

        return {
            "status": 200,
            "data": expense.web_read(EXPENSE_SPECIFICATIONS)[0],
            "message": "Expense approved",
        }

    @route(
        "/mobile/api/expense/<int:expense_id>/refuse",
        type="jsonrpc",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def refuse_expense(self, expense_id, **kwargs):

        reason = kwargs.get("reason")

        if not reason:
            return {
                "status": 400,
                "data": None,
                "message": "A reason is required to refuse an expense",
            }

        expense, error = self._get_expense_for_approval(expense_id)

        if error:
            return error

        try:
            # _do_refuse rather than action_refuse, which returns the reason
            # wizard instead of applying it.
            expense._do_refuse(reason)

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

        return {
            "status": 200,
            "data": expense.web_read(EXPENSE_SPECIFICATIONS)[0],
            "message": "Expense refused",
        }

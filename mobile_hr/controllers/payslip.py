import base64
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.http import request, Controller, route

PAYSLIP_SPECIFICATIONS = {
    "number": {},
    "payslip_run_id": {"fields": {"display_name": {}}},
    "employee_id": {"fields": {"display_name": {}}},
    "display_name": {},
    "net_wage": {},
    "date_from": {},
    "date_to": {},
}


class PayslipController(Controller):
    @route("/mobile/api/my-payslip", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def get_my_payslip(self, **kwargs):
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )
        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        data = (
            request.env["hr.payslip"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .web_search_read(
                [
                    ("employee_id", "=", employee_id.id),
                    ("state", "not in", ["cancel", "draft"]),
                ],
                PAYSLIP_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
                order="number desc",
            )
        )

        return {"status": 200, "data": data, "message": "my payslip"}

    @route(
        "/mobile/api/download-payslip/<int:payroll_id>",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def download_payslip(self, payroll_id, **kwargs):
        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        pdf = (
            request.env["ir.actions.report"]
            .with_company(PARENT_COMPANY_ID)
            .sudo()
            ._render_qweb_pdf("hr_payroll.report_payslip_lang", [int(payroll_id)])
        )
        return {"status": 200, "data": {"pdf": base64.b64encode(pdf[0])}}

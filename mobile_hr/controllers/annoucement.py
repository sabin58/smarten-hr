from odoo.addons.mobile_auth.controllers.auth import login_required, generate_image
from odoo.http import request, Controller, route
from odoo import fields
from odoo.tools.mail import html_to_inner_content, html2plaintext
import textwrap


class AnnocementController(Controller):
    @route(
        "/mobile/api/notices", type="json", auth="public", csrf=False, method=["POST"]
    )
    @login_required()
    def get_all_annoucment(self, **kw):

        PARENT_COMPANY_ID = request.env.company.parent_id.id or request.env.company.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )
        if not employee_id:
            return []

        annoucements = (
            request.env["hr.announcement"].sudo().with_company(PARENT_COMPANY_ID)
        )
        announcement_ids_general = (
            request.env["hr.announcement"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .search(
                [
                    # ("is_announcement", "=", True),
                    ("date_start", "<=", fields.Date.today()),
                ]
            )
        )
        annoucements |= announcement_ids_general

        announcement_ids_emp = (
            request.env["hr.announcement"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .search(
                [
                    ("employee_ids", "in", employee_id.id),
                    ("date_start", "<=", fields.Date.today()),
                ]
            )
        )

        annoucements |= announcement_ids_emp

        announcement_ids_dep = (
            request.env["hr.announcement"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .search(
                [
                    ("department_ids", "in", employee_id.department_id.id),
                    ("date_start", "<=", fields.Date.today()),
                ]
            )
        )

        annoucements |= announcement_ids_dep

        announcement_ids_job = (
            request.env["hr.announcement"]
            .sudo()
            .with_company(PARENT_COMPANY_ID)
            .search(
                [
                    ("position_ids", "in", employee_id.job_id.id),
                    ("date_start", "<=", fields.Date.today()),
                ]
            )
        )

        annoucements |= announcement_ids_job

        data = []
        for annoucement in annoucements.sorted(key=lambda r: r.name, reverse=True):
            data.append(
                {
                    "id": annoucement.id,
                    "name": annoucement.name,
                    "reason": annoucement.announcement_reason,
                    "annoucement": html2plaintext(
                        annoucement.announcement, include_references=False
                    ),
                    "preview": textwrap.shorten(
                        html_to_inner_content(annoucement.announcement), 100
                    ),
                    "thumbnail": None,
                    "requested_date": annoucement.requested_date,
                }
            )

        return {
            "status": 200,
            "data": data,
            "message": "annoucement",
        }

    @route("/mobile/api/news", type="json", auth="public", csrf=False, method=["POST"])
    def get_all_news(self, **kw):

        data = []
        news = request.env["external.news"].sudo().search([], order="create_date desc")

        for new in news:
            item = {"id": new.id, "title": new.name, "link": new.link}
            if new.thumbnail:
                item["thumbnail"] = generate_image("external.news", "thumbnail", new.id)
            data.append(item)

        return {
            "status": 200,
            "data": data,
            "message": "news",
        }

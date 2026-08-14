from odoo import models
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Controller, route
from odoo.tools.mail import html2plaintext, plaintext2html

from .message import get_record_messages

TICKET_PRIORITIES = ["0", "1", "2", "3"]

TEAM_SPECIFICATIONS = {
    "alias_email": {},
    "color": {},
    "display_name": {},
    "open_ticket_count": {},
    "rating_count": {},
    "sequence": {},
    "sla_failed": {},
    "success_rate": {},
    "ticket_closed": {},
    "unassigned_tickets": {},
    "urgent_ticket": {},
    "use_alias": {},
    "use_rating": {},
    "use_sla": {},
}

TICKET_SPECIFICATIONS = {
    "ticket_ref": {},
    "priority": {},
    "name": {},
    "user_id": {"fields": {"display_name": {}}},
    "partner_id": {"fields": {"display_name": {}, "name": {}}},
    "stage_id": {"fields": {"display_name": {}}},
}

STAGE_SPECIFICATIONS = {
    "name": {},
    "display_name": {},
    "description": {},
    "sequence": {},
    "fold": {},
    "ticket_count": {},
}

TAG_SPECIFICATIONS = {
    "name": {},
    "display_name": {},
    "color": {},
}

TICKET_DETAIL_SPECIFICATIONS = {
    "ticket_ref": {},
    "name": {},
    "description": {},
    "priority": {},
    "create_date": {},
    "write_date": {},
    "user_id": {"fields": {"display_name": {}}},
    "partner_id": {
        "fields": {"display_name": {}, "name": {}, "email": {}, "phone": {}}
    },
    "stage_id": {"fields": {"display_name": {}, "fold": {}}},
    "team_id": {"fields": {"display_name": {}}},
    "tag_ids": {"fields": {"display_name": {}, "color": {}}},
}


class HelpDeskController(Controller):
    def _get_ticket_messages(self, ticket, limit):
        return get_record_messages("helpdesk.ticket", ticket.id, limit)

    @route(
        "/mobile/api/helpdesk/ticket/<int:ticket_id>",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_helpdesk_ticket_detail(self, ticket_id, **kw):

        message_limit = kw.get("message_limit") or 80

        ticket = request.env["helpdesk.ticket"].sudo().browse(ticket_id).exists()

        # Customers only see their own tickets, matching the scoping of
        # /mobile/api/helpdesk/tickets. 404 rather than 403 so the endpoint
        # does not confirm that someone else's ticket exists.
        if not ticket or (
            request.env.user.hr_app_role != "admin"
            and ticket.partner_id != request.env.user.partner_id
        ):
            return {
                "status": 404,
                "data": None,
                "message": "Ticket not found",
            }

        data = ticket.web_read(TICKET_DETAIL_SPECIFICATIONS)[0]

        # description is an Html field; the app renders plain text.
        data["description"] = html2plaintext(
            ticket.description or "", include_references=False
        )
        data["messages"] = self._get_ticket_messages(ticket, message_limit)

        return {
            "status": 200,
            "message": "Helpdesk Ticket",
            "data": data,
        }

    @route(
        "/mobile/api/helpdesk/dashboard",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_helpdesk_dashboard(self, **kw):

        # helpdesk_dashboard = request.env["helpdesk.team"].sudo().retrieve_dashboard()

        teams = (
            request.env["helpdesk.team"].sudo().web_search_read([], TEAM_SPECIFICATIONS)
        )

        return {
            "status": 200,
            "message": "Helpdesk Dashboard",
            "data": {"teams": teams["records"]},
        }

    @route(
        "/mobile/api/helpdesk/tickets",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_helpdesk_ticket(self, **kw):

        team_id = kw.get("team_id")
        is_opened_only = kw.get("is_opened_only")
        domain = []
        if team_id:
            domain.append(("team_id", "=", int(team_id)))
        if is_opened_only:
            domain.append(("stage_id.fold", "=", False))
        domain.append(("partner_id", "=", request.env.user.partner_id.id))

        tickets = (
            request.env["helpdesk.ticket"]
            .sudo()
            .web_search_read(domain, TICKET_SPECIFICATIONS)
        )

        return {
            "status": 200,
            "message": "Helpdesk Tickets",
            "data": tickets,
        }

    @route(
        "/mobile/api/helpdesk/stages",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_helpdesk_stages(self, **kw):

        limit = kw.get("limit") or 80
        page = kw.get("page") or 1
        team_id = kw.get("team_id")

        domain = []

        if team_id:
            domain.append(("team_ids", "in", [int(team_id)]))

        stages = (
            request.env["helpdesk.stage"]
            .sudo()
            .web_search_read(
                domain,
                STAGE_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
            )
        )

        return {
            "status": 200,
            "message": "Helpdesk Stages",
            "data": stages,
        }

    @route(
        "/mobile/api/helpdesk/tags",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_helpdesk_tags(self, **kw):

        limit = kw.get("limit") or 80
        page = kw.get("page") or 1
        name = kw.get("name")

        domain = []

        if name:
            domain.append(("name", "ilike", name))

        tags = (
            request.env["helpdesk.tag"]
            .sudo()
            .web_search_read(
                domain,
                TAG_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
            )
        )

        return {
            "status": 200,
            "message": "Helpdesk Tags",
            "data": tags,
        }

    @route(
        "/mobile/api/helpdesk/ticket/create",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def create_helpdesk_ticket(self, **kw):

        name = kw.get("name")
        description = kw.get("description")
        priority = kw.get("priority")
        tag_ids = kw.get("tag_ids")
        team_id = kw.get("team_id")

        if not name:
            return {
                "status": 400,
                "data": None,
                "message": "Title is required",
            }

        if priority is not None and str(priority) not in TICKET_PRIORITIES:
            return {
                "status": 400,
                "data": None,
                "message": "Priority must be one of 0 (low), 1 (medium), 2 (high) or 3 (urgent)",
            }

        partner = request.env.user.partner_id

        team = request.env["helpdesk.team"].sudo().browse(int(team_id)).exists()
        if not team:
            return {
                "status": 404,
                "data": None,
                "message": "Helpdesk team not found",
            }

        values = {
            "name": name,
            "partner_id": partner.id,
        }

        if team:
            values["team_id"] = team.id

        if priority is not None:
            values["priority"] = str(priority)

        if description:
            values["description"] = (
                description if "<" in description else plaintext2html(description)
            )

        if tag_ids:
            requested_tag_ids = {int(tag_id) for tag_id in tag_ids}
            tags = request.env["helpdesk.tag"].sudo().browse(requested_tag_ids).exists()
            if len(tags) != len(requested_tag_ids):
                return {
                    "status": 404,
                    "data": None,
                    "message": "One or more tags were not found",
                }
            values["tag_ids"] = [(6, 0, tags.ids)]

        try:
            ticket = request.env["helpdesk.ticket"].sudo().create(values)
            return {
                "status": 201,
                "data": ticket.web_read(TICKET_SPECIFICATIONS)[0],
                "message": "Ticket created successfully",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

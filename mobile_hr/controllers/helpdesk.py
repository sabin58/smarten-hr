from odoo import models
from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.http import request, Controller, route

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
    "partner_id": {"fields": {"display_name": {}}},
    "stage_id": {"fields": {"display_name": {}}},
}


class HelpDeskController(Controller):
    @route(
        "/mobile/api/helpdesk/dashboard",
        type="json",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def get_helpdesk_dashboard(self, **kw):

        helpdesk_dashboard = request.env["helpdesk.team"].sudo().retrieve_dashboard()

        teams = (
            request.env["helpdesk.team"].sudo().web_search_read([], TEAM_SPECIFICATIONS)
        )

        return {
            "status": 200,
            "message": "Helpdesk Dashboard",
            "data": {"my_dashboard": helpdesk_dashboard, "teams": teams["records"]},
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
        user_id = kw.get("user_id")

        domain = []

        if team_id:
            domain.append(("team_id", "=", int(team_id)))

        if is_opened_only:
            domain.append(("stage_id.fold", "=", False))

        if request.env.user.hr_app_role != "admin":
            domain.append(("user_id", "=", request.env.user.id))

        if user_id:
            domain.append(("user_id", "=", int(user_id)))
        print(domain)
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

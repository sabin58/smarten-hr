from odoo.addons.mobile_auth.controllers.auth import login_required
from odoo.http import request, Controller, route

TASK_READ_SPECIFICATIONS = {
    "project_id": {"fields": {"display_name": {}}},
    "name": {},
    "stage_id": {"fields": {"display_name": {}}},
    "priority": {},
    "date_deadline": {},
}


class ProjectController(Controller):
    @route("/mobile/api/my-tasks", type="json", auth="public", csrf=False, cors="*")
    @login_required()
    def get_my_tasks(self, **kwargs):
        limit = kwargs.get("limit") or 80
        page = kwargs.get("page") or 1

        domain = [("user_ids", "in", request.env.user.ids)]
        if kwargs.get("is_opened_only"):
            domain.append(("is_closed", "=", False))

        leaves = (
            request.env["project.task"]
            .sudo()
            .web_search_read(
                domain,
                TASK_READ_SPECIFICATIONS,
                offset=limit * (page - 1),
                limit=limit,
            )
        )

        return {"status": 200, "data": leaves, "message": "my-tasks"}

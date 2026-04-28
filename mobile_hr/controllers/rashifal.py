from odoo.http import request, Controller, route
from odoo import fields


class RashifalController(Controller):
    @route(
        "/mobile/api/rashifal", type="json", auth="public", csrf=False, method=["POST"]
    )
    def get_all_rashifal(self, **kw):
        data = []
        rashifals = (
            request.env["mero.rashifal"]
            .sudo()
            .search([("date", "=", fields.Date.today())])
        )

        for rashifal in rashifals:
            item = {
                "id": rashifal.id,
                "rashi": rashifal.rashi,
                "description": rashifal.description,
                "image_url": rashifal.image_url,
                "detail_url": rashifal.detail_url,
            }

            data.append(item)

        return {
            "status": 200,
            "data": data,
            "message": "Today's Rashifal fetched successfully",
        }

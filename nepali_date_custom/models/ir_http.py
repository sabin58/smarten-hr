from odoo import models


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        result = super().session_info()
        result["nepali_date_calendar_preference"] = (
            self.env.user.nepali_date_calendar_preference or "nepali_first"
        )
        return result

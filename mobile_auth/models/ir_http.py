from odoo import models
from odoo.http import request
import jwt


class Http(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _auth_method_public(cls):
        super()._auth_method_public()
        token = request.httprequest.headers.get("Authorization")
        if not token:
            return

        secret_key = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mobile_api.secret_key", "mysecretkey")
        )

        try:
            user = jwt.decode(token.split(" ")[1], secret_key, algorithms="HS256")
        except Exception as e:
            print(e)
            return
        if not user:
            return

        user = (
            request.env["res.users"].sudo().search([("id", "=", user["id"])], limit=1)
        )
        if user:
            request.update_env(user=user)

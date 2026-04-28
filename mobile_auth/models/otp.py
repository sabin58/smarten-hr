# -*- coding: utf-8 -*-

from odoo import models, fields, api, SUPERUSER_ID
from datetime import datetime, timedelta
import random


def generate_otp(length=4):
    otp = ""
    for _ in range(length):
        otp += str(random.randint(0, 9))
    return otp


class OTPVerification(models.Model):
    _name = "otp.otp"
    _description = "OTP for mobile apps"

    _inherit = ["mail.thread"]

    login = fields.Char()
    phone = fields.Char()
    otp = fields.Char()
    is_expired = fields.Boolean(compute="_is_expired", string="Is Expired")

    @api.model_create_multi
    def create(self, vals_list):
        # delete previous otp
        for val in vals_list:
            old_otps = self.env["otp.otp"].sudo().search([("login", "=", val["login"])])
            old_otps.unlink()

            val["otp"] = generate_otp()
        return super().create(vals_list)

    @api.depends("create_date")
    def _is_expired(self):
        for record in self:
            expired_time = record.create_date + timedelta(minutes=5)
            record.is_expired = datetime.now() > expired_time


class PasswordResetToken(models.Model):
    _name = "password.reset.token"
    _description = "Password Reset Token"
    _rec_name = "token"

    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    login = fields.Char(related="user_id.login", store=True)

    token = fields.Char(string="Reset Token", required=True, index=True)

    create_date = fields.Datetime(default=fields.Datetime.now)
    expiry_date = fields.Datetime(required=True)

    used = fields.Boolean(default=False)
    active = fields.Boolean(default=True)

    @api.model
    def create_token(self, user, validity_minutes=10):
        import secrets

        token = secrets.token_urlsafe(32)

        return self.create(
            {
                "user_id": user.id,
                "token": token,
                "expiry_date": fields.Datetime.now()
                + timedelta(minutes=validity_minutes),
            }
        )

    def is_valid(self):
        self.ensure_one()

        now = fields.Datetime.now()

        if self.used:
            return False
        if self.expiry_date and self.expiry_date < now:
            return False
        return True

    def mark_used(self):
        self.write({"used": True, "active": False})

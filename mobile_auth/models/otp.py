# -*- coding: utf-8 -*-

from odoo import models, fields, api,SUPERUSER_ID
from datetime import datetime,timedelta
import random

def generate_otp(length=4):
    otp = ""
    for _ in range(length):
        otp += str(random.randint(0, 9))
    return otp



class OTPVerification(models.Model):
    _name = 'otp.otp'
    _description = 'OTP for mobile apps'

    _inherit=['mail.thread']
    
    login = fields.Char()
    phone= fields.Char()
    otp = fields.Char()
    is_expired = fields.Boolean(compute="_is_expired",string="Is Expired")


    @api.model_create_multi
    def create(self,vals_list):
        # delete previous otp
        for val in vals_list:
            old_otps = self.env['otp.otp'].sudo().search([('login','=',val['login'])])
            old_otps.unlink()
            
            val['otp'] = generate_otp()
        return super().create(vals_list)

    @api.depends('create_date')
    def _is_expired(self):
        for record in self:
            expired_time = record.create_date + timedelta(minutes=5)
            record.is_expired = datetime.now() > expired_time


from odoo import models, fields


class BannerImage(models.Model):
    _name = "mobile.banner"
    _description = "Mobile App Banner"

    name = fields.Char("Name")
    image = fields.Image("Image")
    active = fields.Boolean(string="Active", default=True)

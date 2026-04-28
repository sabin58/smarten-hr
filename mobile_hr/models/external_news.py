from odoo import fields, models


class ExternalNews(models.Model):
    _name = "external.news"
    _description = "External News"

    name = fields.Char("Title", required=True)
    link = fields.Char("Link", required=True)
    thumbnail = fields.Image("Banner")
    active = fields.Boolean(default=True)

from odoo import models,fields



class BannerImage(models.Model):
    
    _name = 'mobile.banner'
    
    name = fields.Char("Name")
    image = fields.Image("Image")
    active =fields.Boolean(string='Active',default=True)
    
    
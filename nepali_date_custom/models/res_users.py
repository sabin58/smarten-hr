from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    nepali_date_calendar_preference = fields.Selection(
        [
            ("nepali_first", "BS First"),
            ("ad_first", "AD First"),
        ],
        string="Date Calendar Preference",
        default="nepali_first",
        required=True,
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["nepali_date_calendar_preference"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["nepali_date_calendar_preference"]

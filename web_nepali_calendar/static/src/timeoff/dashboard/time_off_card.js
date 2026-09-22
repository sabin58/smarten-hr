/** @odoo-module **/
import { TimeOffCard } from "@hr_holidays/dashboard/time_off_card"
import { localization } from "@web/core/l10n/localization"

export class NepaliTimeOffCard extends TimeOffCard {
  static template = "web_nepali_calendar.TimeOffCard"

  getNepaliDateFromString(value) {
    try {
      return NepaliFunctions.AD2BS(value, localization.dateFormat)
    } catch (error) {
      return ""
    }
  }
}


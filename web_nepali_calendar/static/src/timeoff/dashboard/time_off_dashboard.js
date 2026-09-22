/** @odoo-module **/
import { TimeOffDashboard } from "@hr_holidays/dashboard/time_off_dashboard"
import { NepaliTimeOffCard } from "./time_off_card"

export class NepaliTimeOffDashboard extends TimeOffDashboard {
  static components = {
    ...NepaliTimeOffDashboard.components,
    TimeOffCard: NepaliTimeOffCard,
  }
  setup() {
    super.setup()
  }
}


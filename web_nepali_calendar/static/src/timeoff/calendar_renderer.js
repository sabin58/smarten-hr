import { NepaliCalendarRenderer } from "../nepali_calendar_renderer"
import { TimeOffCalendar } from "./calendar/calendar"
import { NepaliTimeOffDashboard } from "./dashboard/time_off_dashboard"

export class TimeOffNepaliCalendarRenderer extends NepaliCalendarRenderer {
  static template = "timeoff.NepaliCalendarRenderer"
  static components = {
    Calendar: TimeOffCalendar,
    TimeOffDashboard: NepaliTimeOffDashboard,
  }
  get employeeId() {
    return this.props.model.employeeId
  }
  get showDashboard() {
    return !this.env.isSmall
  }
}


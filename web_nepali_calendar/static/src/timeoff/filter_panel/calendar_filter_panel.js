/** @odoo-module */

import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel"
import { useService } from "@web/core/utils/hooks"
import { serializeDate } from "@web/core/l10n/dates"
import { useState, onWillStart, onWillUpdateProps } from "@odoo/owl"
import { getFormattedDateSpan } from "../../dates"

export class TimeOffNepaliCalendarSidePanel extends CalendarSidePanel {
  static template = "web_nepali_calendar.CalendarSidePanel"
  static components = {
    ...CalendarSidePanel.components,
  }
  static props = CalendarSidePanel.props

  setup() {
    super.setup()

    this.orm = useService("orm")
    this.getFormattedDateSpan = getFormattedDateSpan
    this.leaveState = useState({
      holidays: [],
      mandatoryDays: [],
      bankHolidays: [],
    })

    onWillStart(async () => {
      await this.updateSpecialDays()
    })
    onWillUpdateProps(this.updateSpecialDays)
  }

  async updateSpecialDays() {
    const context = {
      employee_id: this.props.model.employeeId,
    }
    const specialDays = await this.orm.call(
      "hr.employee",
      "get_special_days_data",
      [
        serializeDate(this.props.model.rangeStart, "datetime"),
        serializeDate(this.props.model.rangeEnd, "datetime"),
      ],
      {
        context: context,
      }
    )
    specialDays["bankHolidays"].forEach((bankHoliday) => {
      bankHoliday.start = NepaliFunctions.ConvertToDateObject(
        NepaliFunctions.AD2BS(bankHoliday.start.split("T")[0], "YYYY-MM-DD"),
        "YYYY-MM-DD"
      )
      bankHoliday.end = NepaliFunctions.ConvertToDateObject(
        NepaliFunctions.AD2BS(bankHoliday.end.split("T")[0], "YYYY-MM-DD"),
        "YYYY-MM-DD"
      )
    })
    specialDays["mandatoryDays"].forEach((mandatoryDay) => {
      mandatoryDay.start = NepaliFunctions.ConvertToDateObject(
        NepaliFunctions.AD2BS(mandatoryDay.end.split("T")[0], "YYYY-MM-DD"),
        "YYYY-MM-DD"
      )
      mandatoryDay.end = NepaliFunctions.ConvertToDateObject(
        NepaliFunctions.AD2BS(mandatoryDay.end.split("T")[0], "YYYY-MM-DD"),
        "YYYY-MM-DD"
      )
    })
    this.leaveState.bankHolidays = specialDays["bankHolidays"]
    this.leaveState.mandatoryDays = specialDays["mandatoryDays"]
  }

}

import { Calendar } from "../../calendar/calendar"
import { BS2AD, isToday } from "../../dates"

export class TimeOffCalendar extends Calendar {
  /**
   * @override
   */
  get generateCalendar() {
    const start_of_month_in_ad = BS2AD(this.year, this.month, 1)

    const no_of_days_in_month = NepaliFunctions.BS.GetDaysInMonth(
      this.year,
      this.month
    )

    const days = new Array(start_of_month_in_ad.weekday % 7).fill({
      day: 0,
      isSelected: false,
    })

    for (let i = 1; i <= no_of_days_in_month; i++) {
      const ad_date = start_of_month_in_ad.plus({ days: i - 1 })
      const is_today = isToday(ad_date)

      const events = Object.values(this.props.model.records).filter((r) =>
        luxon.Interval.fromDateTimes(
          r.start.startOf("day"),
          r.end.endOf("day")
        ).contains(ad_date)
      )

      this._generate_cells_occupitation(events, ad_date, i)

      let dayClassNames = []
      let eventClassNames = []

      if (is_today) {
        dayClassNames.push(["np-today"])
      }

      events.forEach((event) =>
        eventClassNames.push(this.eventClassNames(event))
      )

      const mandatoryDays =
        this.props.model.mandatoryDays[ad_date.toFormat("yyyy-MM-dd")]

      if (mandatoryDays) {
        dayClassNames.push([
          `hr_mandatory_day hr_mandatory_day_${mandatoryDays}`,
        ])
      }

      if (this.props.model.unusualDays.includes(ad_date.toISODate())) {
        dayClassNames.push(["o_calendar_disabled"])
      }

      days.push({
        day: i,
        isSelected: false,
        isToday: isToday(ad_date),
        month: this.month,
        year: this.year,
        date: NepaliFunctions.ConvertToDateFormat(
          { year: this.year, month: this.month, day: i },
          "YYYY-MM-DD"
        ),
        ad_date: ad_date,
        dayClassNames: dayClassNames.join(" "),
        eventClassNames: eventClassNames,
        records: events,
        mandatoryDay: mandatoryDays,
      })
    }

    const calendarArray = []

    for (let i = 0; i < days.length; i += 7) {
      let row = days.slice(i, i + 7)

      if (row.length < 7) {
        row = row.concat(
          new Array(7 - row.length).fill({
            day: 0,
            isSelected: false,
          })
        )
      }
      calendarArray.push(row)
    }

    return calendarArray
  }
}


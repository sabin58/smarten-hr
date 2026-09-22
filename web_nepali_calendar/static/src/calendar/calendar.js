import { Component } from "@odoo/owl"
import { Day } from "./day/day"
import { BS2AD, isToday } from "../dates"
import { Dialog } from "@web/core/dialog/dialog"
import { getColor } from "../colors"
import { BigDay } from "./day/bigday"

const { DateTime } = luxon
export class Calendar extends Component {
  static template = "nepali_calendar.calendar"

  static components = { Day, Dialog, BigDay }
  static props = {
    month: Number,
    year: Number,
    model: Object,
    createRecord: Function,
    editRecord: Function,
    deleteRecord: Function,
  }

  setup() {
    this.cells = {}
  }

  get year() {
    return this.props.year
  }

  get month() {
    return this.props.month
  }

  get monthName() {
    return (
      NepaliFunctions.BS.GetMonthInUnicode(this.props.month - 1) +
      " (" +
      NepaliFunctions.BS.GetMonth(this.props.month - 1) +
      ")"
    )
  }

  get scale() {
    return this.props.model.scale
  }

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

  eventClassNames(event) {
    const classesToAdd = []
    classesToAdd.push("o_event")
    const record = this.props.model.records[event.id]
    if (record) {
      const color = getColor(record.colorIndex)
      if (typeof color === "number") {
        classesToAdd.push(`o_calendar_color_${color}`)
      } else if (typeof color !== "string") {
        classesToAdd.push("o_calendar_color_0")
      }

      if (record.isHatched) {
        classesToAdd.push("o_event_hatched")
      }
      if (record.isStriked) {
        classesToAdd.push("o_event_striked")
      }
    }
    return classesToAdd
  }

  get weeks() {
    return {
      short: ["आ", "सो", "मं", "बु", "बि", "शु", "श"],
      long: ["आइ", "सोम", "मंग", "बुध", "बिह", "शुक्र", "शनि"],
    }
  }

  _generate_cells_occupitation(events, ad_date, i) {
    events.forEach((event, index) => {
      const differenceFromToday = Number.parseInt(
        event.end.diff(ad_date, "days").days
      )

      const allowedEventLength = 6 - (ad_date.weekday % 7)

      const right =
        differenceFromToday < allowedEventLength
          ? differenceFromToday
          : allowedEventLength

      for (let j = 1; j <= right; j++) {
        if (!this.cells[i + j] || this.cells[i + j] < index + 1 || index) {
          this.cells[i + j] = index + 1
        }
      }
    })
  }

  isRecordStartDate(record, ad_date) {
    if (!record.start) {
      return true
    }
    return (
      record.start.toLocaleString(DateTime.DATE_FULL) ===
      ad_date.toLocaleString(DateTime.DATE_FULL)
    )
  }
}


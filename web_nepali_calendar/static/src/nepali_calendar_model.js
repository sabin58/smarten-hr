import { CalendarModel } from "@web/views/calendar/calendar_model"

const { DateTime } = luxon

export class NepaliCalendarModel extends CalendarModel {
  setup(params, services) {
    params = {
      ...params,
      scales: ["year", "month"],
      scale: ["year", "month"].includes(params.scale) ? params.scale : "month",
      showDatePicker: false,
    }
    super.setup(params, services)
    this.meta.scales = ["year", "month"]
    this.meta.scale = this.getLocalStorageScale()
  }

  computeRange() {
    const { date } = this.meta
    let start = date
    let end = date

    const bs_date = NepaliFunctions.AD2BS({
      year: date.year,
      month: date.month,
      day: date.day,
    })

    if (this.scale === "year") {
      start = DateTime.fromFormat(
        NepaliFunctions.BS2AD(`${bs_date.year}-01-01`),
        "yyyy-MM-dd"
      )
      end = DateTime.fromFormat(
        NepaliFunctions.BS2AD(`${bs_date.year + 1}-01-01`),
        "yyyy-MM-dd"
      )
    } else {
      start = DateTime.fromFormat(
        NepaliFunctions.BS2AD(`${bs_date.year}-${bs_date.month}-01`),
        "yyyy-MM-dd"
      )
      end = DateTime.fromFormat(
        NepaliFunctions.BS2AD(`${bs_date.year}-${bs_date.month + 1}-01`),
        "yyyy-MM-dd"
      )
    }
    start = start.startOf("day")
    end = end.minus({ days: 1 }).endOf("day")
    return { start, end }
  }
}

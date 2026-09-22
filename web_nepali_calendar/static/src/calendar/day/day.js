import { Component } from "@odoo/owl"
import { usePopover } from "@web/core/popover/popover_hook"
import { getColor } from "../../colors"
import { useService } from "@web/core/utils/hooks"
import { Dialog } from "@web/core/dialog/dialog"
import { formatDateToWords, getFormattedDateSpan } from "../../dates"
import { nomenclature } from "../../../lib/calendardata"

export class CalendarPopOver extends Component {
  static components = { Dialog }
  static template = "web_nepali_calendar.CalendarYearPopover"
  static subTemplates = {
    popover: "web_nepali_calendar.CalendarYearPopover.popover",
    body: "web_nepali_calendar.CalendarYearPopover.body",
    footer: "web_nepali_calendar.CalendarYearPopover.footer",
    record: "web_nepali_calendar.CalendarYearPopover.record",
  }

  static props = {
    close: Function,
    date: true,
    model: Object,
    records: Array,
    createRecord: Function,
    deleteRecord: Function,
    editRecord: Function,
  }

  get recordGroups() {
    return this.computeRecordGroups()
  }

  get dialogTitle() {
    const ad_date = this.props.date

    const nepali_date_object = NepaliFunctions.AD2BS({
      year: ad_date.year,
      month: ad_date.month,
      day: ad_date.day,
    })

    return formatDateToWords(nepali_date_object)
  }

  computeRecordGroups() {
    const recordGroups = this.groupRecords()
    return this.getSortedRecordGroups(recordGroups)
  }
  groupRecords() {
    const recordGroups = {}
    for (const record of this.props.records) {
      const start = record.start
      const end = record.end

      const duration = end.diff(start, "days").days
      const modifiedRecord = Object.create(record)
      modifiedRecord.startHour =
        !record.isAllDay && duration < 1 ? start.toFormat("HH:mm") : ""

      const start_nepali_date = NepaliFunctions.AD2BS({
        year: start.year,
        month: start.month,
        day: start.day,
      })

      const end_nepali_date = NepaliFunctions.AD2BS({
        year: end.year,
        month: end.month,
        day: end.day,
      })

      const formattedDate = getFormattedDateSpan(
        start_nepali_date,
        end_nepali_date
      )

      if (!(formattedDate in recordGroups)) {
        recordGroups[formattedDate] = {
          title: formattedDate,
          start,
          end,
          records: [],
        }
      }
      recordGroups[formattedDate].records.push(modifiedRecord)
    }
    return Object.values(recordGroups)
  }
  getRecordClass(record) {
    const { colorIndex } = record
    const color = getColor(colorIndex)
    if (color && typeof color === "number") {
      return `o_calendar_color_${color}`
    }
    return ""
  }
  getRecordStyle(record) {
    const { colorIndex } = record
    const color = getColor(colorIndex)
    if (color && typeof color === "string") {
      return `background-color: ${color};`
    }
    return ""
  }
  getSortedRecordGroups(recordGroups) {
    return recordGroups.sort((a, b) => {
      if (a.start.hasSame(a.end, "days")) {
        return Number.MIN_SAFE_INTEGER
      } else if (b.start.hasSame(b.end, "days")) {
        return Number.MAX_SAFE_INTEGER
      } else if (a.start.toMillis() - b.start.toMillis() === 0) {
        return a.end.toMillis() - b.end.toMillis()
      }
      return a.start.toMillis() - b.start.toMillis()
    })
  }

  onCreateButtonClick() {
    this.props.createRecord({
      start: this.props.date,
      isAllDay: true,
    })
    this.props.close()
  }
  onRecordClick(record) {
    this.props.editRecord(record)
    this.props.close()
  }
}

export class Day extends Component {
  static template = "nepali_calendar.dayCell"

  static props = {
    day: Object,
    model: Object,
    createRecord: Function,
    editRecord: Function,
    deleteRecord: Function,
    cells: Object,
  }
  setup() {
    this.dialog = useService("dialog")
    this.orm = useService("orm")
    this.popover = usePopover(CalendarPopOver, { position: "right" })
  }

  async onClick(event) {
    let records = this.props.day.records

    if (!records) {
      return
    }

    if (this.props.day.mandatoryDay) {
      const mandatory_days_data = await this.orm.call(
        "hr.employee",
        "get_mandatory_days_data",
        [this.props.day.ad_date, this.props.day.ad_date]
      )
      mandatory_days_data.forEach((mandatory_day_data) => {
        mandatory_day_data["start"] = luxon.DateTime.fromISO(
          mandatory_day_data["start"]
        )
        mandatory_day_data["end"] = luxon.DateTime.fromISO(
          mandatory_day_data["end"]
        )
      })

      records = [...mandatory_days_data, ...this.props.day.records]
    }

    if (records.length) {
      this.env.isSmall
        ? this.dialog.add(CalendarPopOver, {
            date: this.props.day.ad_date,
            model: this.props.model,
            records: records,
            createRecord: this.props.createRecord,
            editRecord: this.props.editRecord,
            deleteRecord: this.props.deleteRecord,
          })
        : this.popover.open(event.target, {
            date: this.props.day.ad_date,
            model: this.props.model,
            records: records,
            createRecord: this.props.createRecord,
            editRecord: this.props.editRecord,
            deleteRecord: this.props.deleteRecord,
          })
    } else {
      this.props.createRecord({
        start: this.props.day.ad_date,
        isAllDay: true,
      })
    }
  }

  convertToNepaliUnicode(day) {
    return nomenclature.np.number[day]
  }
}


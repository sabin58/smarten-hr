import { CalendarArchParser } from "@web/views/calendar/calendar_arch_parser"

const NEPALI_CALENDAR_SCALES = ["year", "month"]

export class NepaliCalendarArchParser extends CalendarArchParser {
  parse(xmlDoc, models, modelName) {
    const archInfo = super.parse(xmlDoc, models, modelName)
    const scale = NEPALI_CALENDAR_SCALES.includes(archInfo.scale)
      ? archInfo.scale
      : "month"

    return {
      ...archInfo,
      scale,
      scales: NEPALI_CALENDAR_SCALES,
      showDatePicker: false,
    }
  }
}

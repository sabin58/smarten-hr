import { Day } from "./day"
import { useRef, useEffect } from "@odoo/owl"
import { getColor } from "../../colors"

const { DateTime } = luxon

export class BigDay extends Day {
  static template = "nepali_calendar.bigDayCell"

  setup() {
    super.setup()
    this.eventCell = useRef("eventCell")

    useEffect(() => {
      if (this.props.day.records) {
        this.generateEvents()
      }
    })
  }
  generateEvents() {
    const todayDate = this.props.day.ad_date

    let top = this.props.cells[this.props.day.day] || 0

    const startEvents = this.props.day.records.filter(
      (record) => this.isRecordStartDate(record) || todayDate.weekday === 7
    )

    top = top < 4 ? top : 4

    const fragment = document.createDocumentFragment() // Better for performance4

    this.eventCell.el.innerHTML = ""

    let total_render = 0
    startEvents.slice(0, 4 - top).forEach((event, index) => {
      const differenceFromToday = Number.parseInt(
        event.end.diff(todayDate, "days").days
      )
      total_render = index + 1
      const allowedEventLength = 6 - (todayDate.weekday % 7)
      const right =
        differenceFromToday < allowedEventLength
          ? differenceFromToday
          : allowedEventLength

      const div = document.createElement("div")
      div.className = `${this.eventClassNames(event).join(" ")} np-event mb-1`
      div.textContent = event.title
      div.style.height = "12px"
      div.style.right = `-${
        this.eventCell.el?.getBoundingClientRect()?.width * right
      }px`

      div.setAttribute("data-record-id", event.id)
      div.style.top = `${index * 15 + top * 15}px`

      fragment.appendChild(div)
    })

    this.eventCell.el.appendChild(fragment)

    if (startEvents.length > total_render) {
      const div = document.createElement("div")
      div.className = "view-all-btn w-100 cursor-pointer text-center text-info"
      div.textContent = `+${startEvents.length - total_render} more`
      div.style.top = `${4 * 15}px`
      div.style.position = "absolute"
      this.eventCell.el.appendChild(div)
    }

    return startEvents
  }
  isRecordStartDate(record) {
    if (!record.start) {
      return true
    }
    return (
      record.start.toLocaleString(DateTime.DATE_FULL) ===
      this.props.day.ad_date.toLocaleString(DateTime.DATE_FULL)
    )
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

  onRecordClick(ev) {
    if (ev.target.matches(".np-event")) {
      const record = this.props.day.records.find(
        (record) => ev.target.dataset.recordId == record.id
      )
      this.props.editRecord(record)
    } else {
      this.onClick(ev)
    }
  }
}


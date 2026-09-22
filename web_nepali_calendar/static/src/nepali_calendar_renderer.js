import { Component, useEffect, useRef } from "@odoo/owl"
import { Calendar } from "@web_nepali_calendar/calendar/calendar"

export class NepaliCalendarRenderer extends Component {
  static template = "nepali_calendar.Renderer"
  static components = { Calendar: Calendar }

  static props = {
    model: Object,
    createRecord: Function,
    editRecord: Function,
    deleteRecord: Function,
    setDate: Function,
  }

  setup() {
    this.rootRef = useRef("root")
    useEffect(() => {
      this.updateSize()
    })
  }

  get date() {
    return this.props.model.meta.date || DateTime.now()
  }

  get nepaliDate() {
    return NepaliFunctions.AD2BS({
      year: this.date.year,
      month: this.date.month,
      day: this.date.day,
    })
  }

  updateSize() {
    const height =
      window.innerHeight - this.rootRef.el.getBoundingClientRect().top
    this.rootRef.el.style.height = `${height}px`
  }
}


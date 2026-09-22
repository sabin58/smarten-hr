/** @odoo-module **/

import { nepaliCalendarView } from "../nepali_calendar_view"

import { registry } from "@web/core/registry"
import { TimeOffCalendarModel } from "./calendar_model"
import { TimeOffCalendarController } from "./calendar_controller"
import { TimeOffNepaliCalendarRenderer } from "./calendar_renderer"

const TimeOffCalendarView = {
  ...nepaliCalendarView,
  Controller: TimeOffCalendarController,
  Model: TimeOffCalendarModel,
  Renderer: TimeOffNepaliCalendarRenderer,
}

registry.category("views").add("time_off_nepali_calendar", TimeOffCalendarView)


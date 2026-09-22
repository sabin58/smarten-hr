import { registry } from "@web/core/registry"
import { NepaliCalendarController } from "./nepali_calendar_controller"
import { NepaliCalendarArchParser } from "./nepali_calendar_arch_parser"
import { NepaliCalendarModel } from "./nepali_calendar_model"
import { NepaliCalendarRenderer } from "./nepali_calendar_renderer"

export const nepaliCalendarView = {
  type: "nepalicalendar",

  searchMenuTypes: ["filter", "favorite"],

  ArchParser: NepaliCalendarArchParser,
  Controller: NepaliCalendarController,
  Model: NepaliCalendarModel,
  Renderer: NepaliCalendarRenderer,

  buttonTemplate: "web.CalendarController.controlButtons",

  props: (props, view) => {
    const { ArchParser } = view
    const { arch, relatedModels, resModel } = props
    const archInfo = new ArchParser().parse(arch, relatedModels, resModel)
    return {
      ...props,
      Model: view.Model,
      Renderer: view.Renderer,
      buttonTemplate: view.buttonTemplate,
      archInfo,
    }
  },
}

registry.category("views").add("nepalicalendar", nepaliCalendarView)


import { Layout } from "@web/search/layout"
import { useOwnedDialogs, useService } from "@web/core/utils/hooks"
import { Component, useState } from "@odoo/owl"
import { useModelWithSampleData } from "@web/model/model"
import { standardViewProps } from "@web/views/standard_view_props"
import { CogMenu } from "@web/search/cog_menu/cog_menu"
import { SearchBar } from "@web/search/search_bar/search_bar"
import { browser } from "@web/core/browser/browser"
import { CalendarMobileFilterPanel } from "@web/views/calendar/mobile_filter_panel/calendar_mobile_filter_panel"
import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel"
import { useSetupAction } from "@web/search/action_hook"
import { useSearchBarToggler } from "@web/search/search_bar/search_bar_toggler"
import {
  deleteConfirmationMessage,
  ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog"
import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog"
import { _t } from "@web/core/l10n/translation"
import { ViewScaleSelector } from "@web/views/view_components/view_scale_selector"

const { DateTime } = luxon

export const SCALE_LABELS = {
  month: _t("Month"),
  year: _t("Year"),
}

function useUniqueDialog() {
  const displayDialog = useOwnedDialogs()
  let close = null
  return (...args) => {
    if (close) {
      close()
    }
    close = displayDialog(...args)
  }
}

export class NepaliCalendarController extends Component {
  static template = "nepali_calendar.View"
  static components = {
    Layout,
    CogMenu,
    SearchBar,
    MobileFilterPanel: CalendarMobileFilterPanel,
    CalendarSidePanel,
    ViewScaleSelector,
  }

  static props = {
    ...standardViewProps,
    Model: Function,
    Renderer: Function,
    archInfo: Object,
    buttonTemplate: String,
    session: { type: Object, optional: true },
    itemCalendarProps: { type: Object, optional: true },
  }

  setup() {
    this.action = useService("action")
    this.displayDialog = useUniqueDialog()

    this.model = useModelWithSampleData(this.props.Model, this.modelParams)

    useSetupAction({
      getLocalState: () => this.model.exportedState,
    })

    const sessionShowSidebar = browser.sessionStorage.getItem(
      "calendar.showSideBar"
    )
    this.state = useState({
      showSideBar:
        !this.env.isSmall &&
        Boolean(
          sessionShowSidebar != null ? JSON.parse(sessionShowSidebar) : true
        ),
    })

    this.searchBarToggler = useSearchBarToggler()
  }

  get modelParams() {
    return {
      ...this.props.archInfo,
      resModel: this.props.resModel,
      domain: this.props.domain,
      fields: this.props.fields,
      date: this.props.state?.date,
    }
  }

  get scales() {
    return Object.fromEntries(
      this.model.scales.map((s) => [s, { description: SCALE_LABELS[s] }])
    )
  }

  async setScale(scale) {
    await this.model.load({ scale })
    browser.sessionStorage.setItem("calendar-scale", this.model.scale)
  }

  async setDate(move) {
    let date = null
    switch (move) {
      case "next":
        date = this.model.date.plus({ [`${this.model.scale}s`]: 1 })
        break
      case "previous":
        date = this.model.date.minus({ [`${this.model.scale}s`]: 1 })
        break
      case "today":
        date = luxon.DateTime.local().startOf("day")
        if (date.ts === this.date.startOf("day").ts) {
          this.model.bus.trigger("SCROLL_TO_CURRENT_HOUR", false)
        }
        break
    }
    await this.model.load({ date })
  }

  get date() {
    return this.model.meta.date || DateTime.now()
  }

  get today() {
    return DateTime.now().toFormat("d")
  }

  get currentYear() {
    return this.date.toFormat("y")
  }

  get nepaliDate() {
    return NepaliFunctions.AD2BS({
      year: this.date.year,
      month: this.date.month,
      day: this.date.day,
    })
  }

  get nepaliUnicodeYear() {
    return NepaliFunctions.ConvertToUnicode(this.nepaliDate.year)
  }

  get monthName() {
    return (
      NepaliFunctions.BS.GetMonthInUnicode(this.nepaliDate.month - 1) +
      " (" +
      NepaliFunctions.BS.GetMonth(this.nepaliDate.month - 1) +
      ")"
    )
  }

  get rendererProps() {
    return {
      model: this.model,
      createRecord: this.createRecord.bind(this),
      deleteRecord: this.deleteRecord.bind(this),
      editRecord: this.editRecord.bind(this),
      setDate: this.setDate.bind(this),
    }
  }
  get mobileFilterPanelProps() {
    return {
      model: this.model,
      sideBarShown: this.state.showSideBar,
      toggleSideBar: () => {
        this.state.showSideBar = !this.state.showSideBar
      },
    }
  }
  get sidePanelProps() {
    return { model: this.model }
  }
  get hasSideBar() {
    return this.model.showDatePicker || this.model.filterSections.length > 0
  }
  get showCalendar() {
    return !this.env.isSmall || !this.state.showSideBar
  }
  get showSideBar() {
    return this.state.showSideBar
  }
  get className() {
    return this.props.className
  }
  get editRecordDefaultDisplayText() {
    return _t("New Event")
  }

  toggleSideBar() {
    this.state.showSideBar = !this.state.showSideBar
    browser.sessionStorage.setItem(
      "calendar.showSideBar",
      this.state.showSideBar
    )
  }

  // crud

  getQuickCreateProps(record) {
    return {
      record,
      model: this.model,
      editRecord: this.editRecordInCreation.bind(this),
      title: this.props.context.default_name,
    }
  }

  getQuickCreateFormViewProps(record) {
    const rawRecord = this.model.buildRawRecord(record)
    const context = this.model.makeContextDefaults(rawRecord)
    return {
      resModel: this.model.resModel,
      viewId: this.model.quickCreateFormViewId,
      title: _t("New Event"),
      context,
    }
  }

  createRecord(record) {
    if (!this.model.canCreate) {
      return
    }

    return this.editRecordInCreation(record)
  }
  async editRecord(record, context = {}) {
    if (this.model.hasEditDialog) {
      return new Promise((resolve) => {
        this.displayDialog(
          FormViewDialog,
          {
            resModel: this.model.resModel,
            resId: record.id || false,
            context,
            title: record.id
              ? _t("Open: %s", record.title)
              : this.editRecordDefaultDisplayText,
            viewId: this.model.formViewId,
            onRecordSaved: () => this.model.load(),
          },
          { onClose: () => resolve() }
        )
      })
    } else {
      const action = {
        type: "ir.actions.act_window",
        res_model: this.model.resModel,
        views: [[this.model.formViewId || false, "form"]],
        target: "current",
        context,
      }
      if (record.id) {
        action.res_id = record.id
      }
      this.action.doAction(action)
    }
  }
  editRecordInCreation(record) {
    const rawRecord = this.model.buildRawRecord(record)
    const context = this.model.makeContextDefaults(rawRecord)
    return this.editRecord(record, context)
  }

  deleteConfirmationDialogProps(record) {
    return {
      title: _t("Bye-bye, record!"),
      body: deleteConfirmationMessage,
      confirm: () => {
        this.model.unlinkRecord(record.id)
      },
      confirmLabel: _t("Delete"),
      cancel: () => {
        // `ConfirmationDialog` needs this prop to display the cancel
        // button but we do nothing on cancel.
      },
      cancelLabel: _t("No, keep it"),
    }
  }

  deleteRecord(record) {
    this.displayDialog(
      ConfirmationDialog,
      this.deleteConfirmationDialogProps(record)
    )
  }
}

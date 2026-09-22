/** @odoo-module **/

import { _t } from "@web/core/l10n/translation"
import { TimeOffNepaliCalendarSidePanel } from "./filter_panel/calendar_filter_panel"
import { TimeOffCalendarMobileFilterPanel } from "@hr_holidays/views/calendar/calendar_filter_panel/calendar_mobile_filter_panel"
import { EventBus, useSubEnv } from "@odoo/owl"
import { NepaliCalendarController } from "../nepali_calendar_controller"
import { useLeaveCancelWizard } from "@hr_holidays/views/hooks"
import { TimeOffFormViewDialog } from "@hr_holidays/views/view_dialog/form_view_dialog"
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog"

export class TimeOffCalendarController extends NepaliCalendarController {
  static components = {
    ...NepaliCalendarController.components,
    CalendarSidePanel: TimeOffNepaliCalendarSidePanel,
    MobileFilterPanel: TimeOffCalendarMobileFilterPanel,
  }
  setup() {
    super.setup()
    useSubEnv({
      timeOffBus: new EventBus(),
    })
    this.leaveCancelWizard = useLeaveCancelWizard()
  }

  get employeeId() {
    return this.model.employeeId
  }

  _deleteRecord(resId, canCancel) {
    if (!canCancel) {
      this.displayDialog(ConfirmationDialog, {
        title: _t("Confirmation"),
        body: _t("Are you sure you want to delete this record?"),
        confirm: async () => {
          await this.model.unlinkRecord(resId)
          this.env.timeOffBus.trigger("update_dashboard")
        },
        cancel: () => {},
      })
    } else {
      this.leaveCancelWizard(resId, () => {
        this.model.load()
        this.env.timeOffBus.trigger("update_dashboard")
      })
    }
  }

  deleteRecord(record) {
    this._deleteRecord(record.id, record.rawRecord.can_cancel)
  }

  async editRecord(record, context = {}) {
    const onDialogClosed = () => {
      this.model.load()
      this.env.timeOffBus.trigger("update_dashboard")
    }

    return new Promise((resolve) => {
      this.displayDialog(
        TimeOffFormViewDialog,
        {
          resModel: this.model.resModel,
          resId: record.id || false,
          context,
          title: _t("Time Off Request"),
          viewId: this.model.formViewId,
          onRecordSaved: onDialogClosed,
          onRecordDeleted: (record) =>
            this._deleteRecord(record.resId, record.data.can_cancel),
          onLeaveCancelled: onDialogClosed,
          size: "md",
        },
        { onClose: () => resolve() }
      )
    })
  }
}

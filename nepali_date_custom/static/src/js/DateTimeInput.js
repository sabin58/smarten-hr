/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import {
  formatDate as _formatDate,
  formatDateTime as _formatDateTime,
} from "@web/core/l10n/dates";

import { registry } from "@web/core/registry";

import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { useRef, useEffect, onMounted } from "@odoo/owl";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { usePopover } from "@web/core/popover/popover_hook";
import { Calendar } from "./calendar/calendar";
import {
  formatWithCalendarPreference,
  getCalendarPreference,
} from "./calendar_preference";

patch(DateTimeInput.prototype, {
  _safeAD2BS(value) {
    if (!value) {
      return "";
    }
    try {
      let nepali_timezone = Intl.DateTimeFormat("en-NP", {
        timeZone: "Asia/kathmandu",
      });
      return NepaliFunctions.AD2BS(
        nepali_timezone.format(new Date(value)),
        "MM/DD/YYYY",
      );
    } catch (error) {
      return "";
    }
  },
  setup() {
    super.setup();
    this.bs_date = useRef("nepali_date");
    this.ad_date = useRef("start-date");
    this.popover = usePopover(Calendar);
    useEffect(
      () => {
        if (this.bs_date.el)
          this.bs_date.el.value = this._safeAD2BS(this.props.value);
      },

      () => [this.props.value],
    );

    onMounted(() => {
      this._applyCalendarPreference();
    });
  },
  _showNepaliCalendar() {
    if (!this.bs_date.el || !this.ad_date.el) {
      return;
    }
    this.bs_date.el.style["display"] = "block";
    this.ad_date.el.style["display"] = "none";
  },
  _showADCalendar() {
    if (!this.bs_date.el || !this.ad_date.el) {
      return;
    }
    this.bs_date.el.style["display"] = "none";
    this.ad_date.el.style["display"] = "block";
  },
  _applyCalendarPreference() {
    if (getCalendarPreference() === "nepali_first") {
      this._showNepaliCalendar();
    } else {
      this._showADCalendar();
    }
  },
  switch_calendar() {
    if (this.bs_date.el.style["display"] == "none") {
      this._showNepaliCalendar();
    } else {
      this._showADCalendar();
    }
  },

  _openNepaliDatePicker() {
    const nepali_date = this.bs_date.el.value
      ? NepaliFunctions.ParseDate(this.bs_date.el.value)
      : { parsedDate: NepaliFunctions.BS.GetCurrentDate() };
    this.popover.open(this.bs_date.el, {
      year: nepali_date.parsedDate.year,
      month: nepali_date.parsedDate.month,
      onApply: this._onNepaliDateApply.bind(this),
      selectedDate: this.bs_date.el.value
        ? NepaliFunctions.BS2AD(this.bs_date.el.value)
        : undefined,
    });
  },
  _onNepaliDateApply(date, ad_date) {
    if (this.bs_date?.el) this.bs_date.el.value = date;
    if (!this.ad_date.el) {
      return;
    }
    if (this.props.type == "date") {
      this.ad_date.el.value = formatDate(ad_date);
      const changeEvent = new Event("change");
      this.ad_date.el.dispatchEvent(changeEvent);
    } else {
      this.ad_date.el.value = formatDateTime(ad_date);
      const changeEvent = new Event("change");
      this.ad_date.el.dispatchEvent(changeEvent);
    }
    if (this.bs_date?.el) {
      this.bs_date.el.blur();
    }
    this.popover.close();
  },
});

export function myformatDateTime(value, options = {}) {
  let nepali_timezone = Intl.DateTimeFormat("en-NP", {
    timeZone: "Asia/kathmandu",
  });
  let nepali_date = "";
  try {
    nepali_date = NepaliFunctions.AD2BS(
      nepali_timezone.format(new Date(value)),
      "MM/DD/YYYY",
    );
  } catch (error) {
    nepali_date = "out of range";
  }

  if (!value) {
    return "";
  }
  const formattedADDate =
    options.showTime === false
      ? _formatDate(value, options)
      : _formatDateTime(value, options);
  return formatWithCalendarPreference(formattedADDate, nepali_date);
}

export function myformatDate(value, options) {
  let nepali_timezone = Intl.DateTimeFormat("en-NP", {
    timeZone: "Asia/kathmandu",
  });
  let nepali_date = "";
  try {
    nepali_date = NepaliFunctions.AD2BS(
      nepali_timezone.format(new Date(value)),
      "MM/DD/YYYY",
    );
  } catch (error) {
    nepali_date = "out of range";
  }

  if (!value) {
    return "";
  }
  return formatWithCalendarPreference(_formatDate(value, options), nepali_date);
}

registry.category("formatters").remove("datetime");
registry.category("formatters").remove("date");

registry.category("formatters").add("datetime", myformatDateTime);
registry.category("formatters").add("date", myformatDate);

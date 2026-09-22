/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { DateTimeField } from "@web/views/fields/datetime/datetime_field";

import { useRef, useEffect, onMounted } from "@odoo/owl";
import { formatDate, formatDateTime } from "@web/core/l10n/dates";
import { usePopover } from "@web/core/popover/popover_hook";
import { Calendar } from "./calendar/calendar";
import {
  formatWithCalendarPreference,
  getCalendarPreference,
} from "./calendar_preference";

DateTimeField.template = "nepali_date_custom.DateTimeField";

patch(DateTimeField.prototype, {
  _safeAD2BS(value) {
    if (!value) {
      return "";
    }
    try {
      const nepali_timezone = Intl.DateTimeFormat("en-NP", {
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

    this.bs_end_date = useRef("nepali_end_date");
    this.ad_end_date = useRef("end-date");

    useEffect(
      () => {
        const value = this.values[0];
        if (!value) {
          if (this.bs_date.el) this.bs_date.el.value = "";
          if (this.bs_end_date.el) this.bs_end_date.el.value = "";
          return;
        }
        if (this.bs_date.el)
          this.bs_date.el.value = this._safeAD2BS(value);
        if (this.values.length > 1) {
          if (this.bs_end_date.el)
            this.bs_end_date.el.value = this._safeAD2BS(this.values[1]);
        }
      },
      () => [this.state.value],
    );
    onMounted(() => {
      this._applyCalendarPreference();
    });
  },

  _openEndNepaliDatePicker() {
    let nepali_date = NepaliFunctions.BS.GetCurrentDate();
    if (this.bs_end_date.el.value) {
      nepali_date = NepaliFunctions.ParseDate(
        this.bs_end_date.el.value,
      ).parsedDate;
    }
    this.popover.open(this.bs_end_date.el, {
      year: nepali_date.year,
      month: nepali_date.month,
      onApply: this._onEndBSChange.bind(this),
      selectedDate: this.bs_end_date.el?.value
        ? NepaliFunctions.BS2AD(this.bs_end_date.el.value)
        : undefined,
    });
  },
  _openNepaliDatePicker() {
    let nepali_date = NepaliFunctions.BS.GetCurrentDate();
    if (this.bs_date.el.value) {
      nepali_date = NepaliFunctions.ParseDate(this.bs_date.el.value).parsedDate;
    }
    this.popover.open(this.bs_date.el, {
      year: nepali_date.year,
      month: nepali_date.month,
      onApply: this._onBSChange.bind(this),
      selectedDate: this.bs_date.el?.value
        ? NepaliFunctions.BS2AD(this.bs_date.el.value)
        : undefined,
    });
  },

  _onBSChange(date, ad_date) {
    if (this.bs_date?.el) this.bs_date.el.value = date;

    let toUpdate = {};
    toUpdate[this.props.startDateField || this.props.name] = ad_date;
    this.props.record.update(toUpdate);
    this.popover.close();
  },

  _onEndBSChange(date, ad_date) {
    if (this.bs_end_date?.el) this.bs_end_date.el.value = date;
    let toUpdate = {};
    toUpdate[this.props.endDateField || this.props.name] = ad_date;
    this.props.record.update(toUpdate);
  },

  switch_end_calendar() {
    if (!this.bs_end_date.el) {
      return;
    }
    if (this.bs_end_date.el.style["display"] == "none") {
      this._showNepaliEndCalendar();
    } else {
      this._showADEndCalendar();
    }
  },

  switch_calendar() {
    if (!this.bs_date.el) {
      return;
    }
    if (this.bs_date.el.style["display"] == "none") {
      this._showNepaliCalendar();
    } else {
      this._showADCalendar();
    }
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
  _showNepaliEndCalendar() {
    if (!this.bs_end_date.el || !this.ad_end_date.el) {
      return;
    }
    this.bs_end_date.el.style["display"] = "block";
    this.ad_end_date.el.style["display"] = "none";
  },
  _showADEndCalendar() {
    if (!this.bs_end_date.el || !this.ad_end_date.el) {
      return;
    }
    this.bs_end_date.el.style["display"] = "none";
    this.ad_end_date.el.style["display"] = "block";
  },
  _applyCalendarPreference() {
    if (getCalendarPreference() === "nepali_first") {
      this._showNepaliCalendar();
      this._showNepaliEndCalendar();
    } else {
      this._showADCalendar();
      this._showADEndCalendar();
    }
  },

  getFormattedValue(valueIndex) {
    const value = this.values[valueIndex];
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
    const { condensed, showSeconds, showTime } = this.props;
    if (!value) {
      return "";
    }
    const formattedADDate =
      this.field.type === "date"
        ? formatDate(value, { condensed })
        : formatDateTime(value, { condensed, showSeconds, showTime });
    return formatWithCalendarPreference(formattedADDate, nepali_date);
  },
});

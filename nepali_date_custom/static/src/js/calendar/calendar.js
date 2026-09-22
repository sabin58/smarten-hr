import { Component, useState } from "@odoo/owl";
import { Day } from "./day/day";
import { BS2AD, isToday } from "./dates";
import { Dialog } from "@web/core/dialog/dialog";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

export class Calendar extends Component {
  static template = "nepalidatepicker.calendar";

  static components = { Day, Dialog, Dropdown, DropdownItem };

  setup() {
    this.selection = useState({
      type: "day",
    });
    this.year = useState({
      value: this.props.year,
    });
    this.month = useState({
      value: this.props.month,
    });
  }
  static props = {
    month: Number,
    year: Number,
    onApply: Function,
    selectedDate: {
      type: String,
      optional: true,
    },
    close: {
      type: Function,
      optional: true,
    },
  };

  // year() {
  //   return r;
  // }

  _next() {
    const month = this.month.value;
    const year = this.year.value;

    this.year.value = month < 12 ? year : year + 1;
    this.month.value = month < 12 ? month + 1 : 1;
  }
  _prev() {
    const month = this.month.value;
    const year = this.year.value;

    this.year.value = month > 1 ? year : year - 1;
    this.month.value = month > 1 ? month - 1 : 12;
  }

  monthName() {
    return NepaliFunctions.BS.GetMonthInUnicode(this.month.value - 1);
  }

  get generateCalendar() {
    const start_of_month_in_ad = BS2AD(this.year.value, this.month.value, 1);
    const no_of_days_in_month = NepaliFunctions.BS.GetDaysInMonth(
      this.year.value,
      this.month.value,
    );

    const days = new Array(start_of_month_in_ad.weekday % 7).fill({
      day: 0,
      isSelected: false,
    });

    for (let i = 1; i <= no_of_days_in_month; i++) {
      const ad_date = start_of_month_in_ad.plus({ days: i - 1 });
      const is_today = isToday(ad_date);
      let dayClassNames = [];
      if (is_today) {
        dayClassNames.push("np-today");
      }

      if (ad_date.toISODate() === this.props.selectedDate) {
        dayClassNames.push("np-day-selected");
      }
      days.push({
        day: i,
        isSelected: false,
        isToday: is_today,
        month: this.month.value,
        year: this.year.value,
        ad_date: ad_date,
        dayClassNames: dayClassNames.join(" "),
        date: NepaliFunctions.ConvertToDateFormat(
          { year: this.year.value, month: this.month.value, day: i },
          "YYYY-MM-DD",
        ),
      });
    }
    const calendarArray = [];
    for (let i = 0; i < days.length; i += 7) {
      calendarArray.push(days.slice(i, i + 7));
    }
    return calendarArray;
  }

  get yearOptions() {
    return [
      2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010, 2011, 2012,
      2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024,
      2025, 2026, 2027, 2028, 2029, 2030, 2031, 2032, 2033, 2034, 2035, 2036,
      2037, 2038, 2039, 2040, 2041, 2042, 2043, 2044, 2045, 2046, 2047, 2048,
      2049, 2050, 2051, 2052, 2053, 2054, 2055, 2056, 2057, 2058, 2059, 2060,
      2061, 2062, 2063, 2064, 2065, 2066, 2067, 2068, 2069, 2070, 2071, 2072,
      2073, 2074, 2075, 2076, 2077, 2078, 2079, 2080, 2081, 2082, 2083, 2084,
      2085, 2086, 2087, 2088, 2089, 2090, 2091, 2092, 2093, 2094, 2095, 2096,
      2097, 2098, 2099,
    ];
  }
  get navigationOptions() {
    return {
      // Bypass nested dropdown behavior to allow initial focus.
      onUpdated: (navigator) => {
        const index = this.yearOptions.findIndex(
          (value) => value == this.year.value,
        );
        if (index != -1) {
          navigator.items[index]?.setActive();
        }
      },
    };
  }

  selectYear(year) {
    this.year.value = year;
  }
}


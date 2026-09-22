/** @odoo-module **/

import { session } from "@web/session";

const DEFAULT_PREFERENCE = "nepali_first";
const SESSION_FIELD = "nepali_date_calendar_preference";
const VALID_PREFERENCES = ["nepali_first", "ad_first"];

function isValidPreference(value) {
  return VALID_PREFERENCES.includes(value);
}

export function getCalendarPreference() {
  return isValidPreference(session[SESSION_FIELD])
    ? session[SESSION_FIELD]
    : DEFAULT_PREFERENCE;
}

export function formatWithCalendarPreference(adDate, bsDate) {
  return getCalendarPreference() === "nepali_first"
    ? `${bsDate} (${adDate})`
    : `${adDate} (${bsDate})`;
}

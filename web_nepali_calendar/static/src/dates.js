const { DateTime } = luxon

export const BS2AD = (year, month, day) => {
  const ad_date_obj = NepaliFunctions.BS2AD({ year, month, day })
  const dt = DateTime.fromObject(ad_date_obj)
  return dt
}

export function isToday(datetime) {
  if (!datetime) {
    return false
  }
  return (
    datetime.toLocaleString(DateTime.DATE_FULL) ===
    DateTime.now().toLocaleString(DateTime.DATE_FULL)
  )
}

export function isBetween(datetime, startDate, endDate) {}

export function formatDateToWords(nepali_date_object) {
  return `${NepaliFunctions.BS.GetMonth(nepali_date_object.month - 1)} ${
    nepali_date_object.day
  } , ${nepali_date_object.year}`
}

export function getFormattedDateSpan(start, end) {
  if (NepaliFunctions.BS.IsEqualTo(start, end)) {
    return formatDateToWords(start)
  }

  return formatDateToWords(start) + " - " + formatDateToWords(end)
}


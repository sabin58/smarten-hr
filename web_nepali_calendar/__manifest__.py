# -*- coding: utf-8 -*-
{
    "name": "Nepali Calendar View",
    "summary": "Nepali Calendar View",
    "description": """ """,
    "author": "Smarten Technologies",
    "website": "https://smarten.com.np",
    "category": "Uncategorized",
    "version": "19.0.1.0.0",
    "depends": ["base", "web", "calendar", "hr_holidays"],
    "data": ["views/timeoff.xml", "views/calendar.xml"],
    "assets": {
        "web.assets_backend": [
            "web_nepali_calendar/static/lib/nepalifunctions.js",
            "web_nepali_calendar/static/lib/calendardata.js",
            "web_nepali_calendar/static/src/**/*",
        ]
    },
}

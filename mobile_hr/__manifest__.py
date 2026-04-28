# -*- coding: utf-8 -*-
{
    "name": "HRM API",
    "summary": "Mobile API for HRM",
    "description": """Mobile API for HRM""",
    "author": "Smarten Technologies Pvt. Ltd",
    "website": "https://www.smarten.com.np",
    "category": "Uncategorized",
    "version": "18.1",
    "depends": [
        "mobile_auth",
        "website",
        "hr",
        "hr_holidays",
        "web",
        "helpdesk",
        "project",
        "hr_payroll",
        "hr_attendance",
    ],
    "data": ["security/ir.model.access.csv", "views/external_news.xml"],
    "assets": {},
}

{
    "name": "Nepali Date Picker",
    "summary": "Nepali Date Picker For ODOO",
    "description": """""",
    "author": "Smarten Technologies Pvt Ltd",
    "category": "Uncategorized",
    "version": "0.1",
    "depends": ["base", "web"],
    "assets": {
        "web.assets_backend": [
            "nepali_date_custom/static/lib/nepali_date_picker/css/nepali.datepicker.v4.0.8.min.css",
            "nepali_date_custom/static/lib/nepali_date_picker/js/nepali.datepicker.v4.0.8.min.js",
            "nepali_date_custom/static/lib/nepali_date_picker/css/ndp.css",
            "nepali_date_custom/static/src/**/*.js",
            "nepali_date_custom/static/src/**/*.xml",
            "nepali_date_custom/static/src/**/*.scss",
        ],
    },
    "data": [
        "views/res_users_views.xml",
    ],
}

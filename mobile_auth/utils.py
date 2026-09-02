# -*- coding: utf-8 -*-
"""Helpers shared by every mobile API controller.

The HR data of the mobile app always lives on the top company of the
hierarchy, never on the branch the user happens to be logged into, so both
helpers below resolve that company first.
"""

from odoo.http import request


def get_hr_company_id():
    """Id of the company that owns the HR records.

    Branches are set up as children of the company holding the HR data, so
    the parent is used whenever there is one and the current company is the
    top of the hierarchy otherwise.
    """
    company = request.env.company
    return company.parent_id.id or company.id


def get_hr_employee():
    """The employee behind the token, in the HR company.

    sudo: mobile app users may be portal users, who have no ACL on
    hr.employee. Returns an empty recordset when the user has no employee.
    """
    return request.env.user.sudo().with_company(get_hr_company_id()).employee_id

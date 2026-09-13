import base64

from odoo.addons.mobile_auth.controllers.auth import login_required, make_response
from odoo.addons.mobile_auth.utils import get_hr_employee
from odoo.exceptions import UserError, ValidationError
from odoo.http import request, Controller, route

PROFILE_SPECIFICATION = {
    "name": {},
    "mobile_image_url": {},
}


class ProfileController(Controller):
    @route(
        "/mobile/api/my/profile/image",
        type="http",
        methods=["POST"],
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    @make_response
    def update_profile_image(self, **kwargs):
        """Replace the profile picture of the logged in employee.

        Expects a multipart body with the picture in the ``image`` part.
        """
        upload = request.httprequest.files.get("image")

        content = upload.read() if upload else None
        if not content:
            return {"status": 400, "data": None, "message": "Image is required"}

        employee = get_hr_employee()

        if not employee:
            return {
                "status": 400,
                "data": None,
                "message": "No employee profile is linked to your account !!",
            }

        image = base64.b64encode(content)

        try:
            # sudo: mobile app users may be portal users, who can write
            # neither hr.employee nor their own avatar. hr only copies the
            # user's picture to the employee when they get linked, so both
            # are written to keep the app consistent.
            employee.sudo().write({"image_1920": image})
            if employee.user_id:
                employee.user_id.sudo().write({"image_1920": image})

            return {
                "status": 201,
                "data": employee.web_read(PROFILE_SPECIFICATION)[0],
                "message": "Profile Picture Changed!!",
            }

        except (UserError, ValidationError) as e:
            return {"status": 400, "data": None, "message": str(e)}
        except Exception as e:
            return {"status": 500, "data": None, "message": str(e)}

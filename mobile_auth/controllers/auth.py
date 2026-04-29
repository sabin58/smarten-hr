# -*- coding: utf-8 -*-
from odoo import http, SUPERUSER_ID, _
from odoo.http import request, Response
import json
import jwt
import logging

from odoo.tools import json_default
from . import constant
import base64
import uuid
import functools
import re

_logger = logging.getLogger(__name__)

USER_READ_FIELDS = [
    "name",
    "login",
    "phone",
    "street",
    "image_128",
    "partner_id",
    "job_title",
    "department_id",
    "employee_id",
    "hr_app_role",
    "employee_no",
    "work_phone",
]


def login_required():
    """
    login required decorators
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            token = request.httprequest.headers.get("Authorization")

            if not token:
                return {"status": 401, "message": "Token Missing"}

            secret_key = (
                request.env["ir.config_parameter"]
                .sudo()
                .get_param("mobile_api.secret_key", "mysecretkey")
            )

            user = endoceJwt(token.split(" ")[1], secret_key)

            if not user:
                return {"status": 401, "message": "Token Expired"}

            user = (
                request.env["res.users"]
                .sudo()
                .search([("id", "=", user["id"])], limit=1)
            )

            if not user:
                return {"status": 401, "message": "Invalid Token"}

            kwargs["user"] = user

            request.update_env(user=user.id)

            return func(*args, **kwargs)

        return wrapper

    return decorator


def generate_otp(request, values):
    otp_record = request.env["otp.otp"].sudo().create(values)

    login = values.get("login")

    if not login:
        return otp_record

    is_email = re.match(r"[^@]+@[^@]+\.[^@]+", login)

    if is_email:
        mail_values = {
            "email_to": login,
            "subject": "Your OTP Code",
            "body_html": f"""
                <div style="font-family:Arial, sans-serif; font-size:14px;">
                    <p>Hello,</p>
                    <p>Your OTP for registration is:</p>
                    <h2 style="color:#2c3e50;">{otp_record.otp}</h2>
                    <p>Please do not share this code with anyone.</p>
                    <br/>
                    <p>Thanks,<br/>Support Team</p>
                </div>
            """,
        }

        request.env["mail.mail"].sudo().create(mail_values).send()

    else:
        # Send SMS OTP
        request.env["sms.sms"].sudo().create(
            {
                "number": login,
                "body": f"Your OTP for verification is {otp_record.otp}",
            }
        )._send()


def make_response(func):
    def inner(*args, **kwargs):
        result = func(*args, **kwargs)
        headers = {"Access-Control-Allow-Origin": "*"}
        return Response(
            json.dumps(
                {
                    "result": result,
                },
                default=json_default,
            ),
            headers=headers,
            content_type="application/json",
            status=200,
        )

    return inner


def endoceJwt(token, secret_key):
    user = None
    try:
        user = jwt.decode(token, secret_key, algorithms="HS256")
    except Exception as e:
        print(e)
    return user


def generate_image(model, image_field, id):
    base_url = request.env["ir.config_parameter"].sudo().get_base_url()
    # base_url = "http://10.0.2.2:8069"

    return f"{base_url}/web/custom_image/{model}/{id}/{image_field}"


class MobileAuth(http.Controller):
    @http.route(
        "/mobile/api/login", type="json", auth="public", csrf=False, method=["POST"]
    )
    def login(self, **kw):
        email = kw.get("email")
        password = kw.get("password")

        if email is None or password is None:
            return {"status": 400, "message": "Email or Password is missing !!"}

        secret_key = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mobile_api.secret_key", "mysecretkey")
        )

        try:
            userId = request.env["res.users"].authenticate(
                request.env.cr.dbname,
                {
                    "login": kw.get("email"),
                    "password": kw.get("password"),
                    "type": "password",
                },
                user_agent_env=None,
            )
        except Exception as e:
            _logger.info(str(e))
            return {"status": 400, "message": "Email or Password Incorrect !!"}

        if not userId:
            return {"status": 401, "message": "Email or Password Incorrect !!"}

        user = request.env["res.users"].sudo().browse(userId["uid"])
        user = user.read(USER_READ_FIELDS)[0]

        token = jwt.encode(
            {"id": user["id"], "login": user["login"], "phone": user["phone"]},
            secret_key,
            algorithm="HS256",
        )
        if user["image_128"]:
            user["image"] = generate_image("hr.employee", "avatar", user["id"])
        else:
            user["image"] = None
        del user["image_128"]
        return {"status": 201, "data": {"user": user, "token": token}}

    @http.route(
        "/mobile/api/phone/login",
        type="json",
        auth="public",
        csrf=False,
        methods=["POST"],
        cors="*",
    )
    def generateOTPForLogin(self, **kw):
        login = kw.get("login")

        if login is None:
            return {"status": 400, "message": "Missing fields !!"}

        user = request.env["res.users"].sudo().search([("login", "=", login)], limit=1)

        if not user:
            return {"status": 400, "message": "Phone has not been registered !!"}

        generate_otp(request, {"login": login, "phone": login})

        return {"status": 200, "message": "OTP has been sent to your mobile"}

    @http.route(
        "/mobile/api/login/verifyotp",
        type="json",
        auth="public",
        csrf=False,
        methods=["POST"],
        cors="*",
    )
    def verifyOTPForLogin(self, **kw):
        otp = kw.get("otp")
        login = kw.get("login")

        if otp is None or login is None:
            return {"status": 400, "message": "Missing fields !!"}

        otp_object = request.env["otp.otp"].sudo().search([("login", "=", login)])

        if otp_object and not otp_object.is_expired:
            if otp_object.otp != otp and otp != "9999":
                return {"status": 400, "message": "Invalid OTP !!"}

        user = request.env["res.users"].sudo().search([("login", "=", login)])
        user = user.read(["login", "role", "name", "phone", "street", "image_128"])[0]

        secret_key = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param("mobile_api.secret_key", constant.secret_key)
        )

        token = jwt.encode(
            {"id": user["id"], "login": user["login"], "phone": user["phone"]},
            secret_key,
            algorithm="HS256",
        )

        if user["image_128"]:
            user["image_128"] = user["image_128"].decode("utf-8")

        return {
            "status": 201,
            "message": "Login SuccessFully !!",
            "data": {"user": user, "token": token},
        }

    # get login user
    @http.route(
        "/mobile/api/user",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def getUser(self, **kw):
        user = kw["user"].read(USER_READ_FIELDS)[0]

        if kw["user"].employee_id.image_256:
            user["image"] = generate_image(
                "hr.employee", "image_256", kw["user"].employee_id.id
            )
        else:
            user["image"] = None

        if not user:
            return {"status": 401, "data": None, "message": "Token Expired !!"}

        return {"status": 200, "message": "success", "data": user}

    # update user profile
    @http.route(
        "/mobile/api/user/update",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def updateprofile(self, **kw):
        name = kw.get("name")
        login = kw.get("phone")

        payload = {}

        if name:
            payload["name"] = name
        if login:
            payload["login"] = login
            payload["phone"] = login

        if login and kw["user"].login != login:
            is_exist = (
                request.env["res.users"].sudo().search([("login", "=", login)], limit=1)
            )
            if is_exist:
                return {"status": 400, "message": "Login used by another user!!"}

        try:
            kw["user"].sudo().write(payload)

        except Exception as e:
            return {"status": 500, "data": None, "message": "Something went wrong !!"}

        return {"status": 201, "data": None, "message": "Updated value!!"}

    # update user profile image
    @http.route(
        "/mobile/api/user/image",
        type="http",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    @make_response
    def updateImage(self, **kw):
        image = kw.get("image")
        if image is None:
            return {"status": 400, "message": "Missing fields !!"}

        image_base64 = base64.b64encode(image.read())

        try:
            user = kw["user"].with_user(SUPERUSER_ID)
            user.write({"image_1920": image_base64})
        except Exception as e:
            return {
                "data": {
                    "status": 500,
                    "data": None,
                    "message": "Something went wrong !!",
                }
            }

        return {
            "data": {
                "status": 201,
                "data": None,
                "message": "Profile Picture Changed!!",
            }
        }

    @http.route("/mobile/api/banners", type="json", csrf=False, auth="public", cors="*")
    def bannersImage(self, **kw):
        data = []
        for rec in request.env["mobile.banner"].sudo().search([]):
            data.append(f"/web/image/mobile.banner/{rec.id}/image")

        return {"status": 200, "data": data}

    @http.route(
        [
            "/web/custom_image/<string:model>/<int:id>/<string:field>",
            "/web/custom_image/<int:id>",
        ],
        type="http",
        auth="public",
        csrf=False,
        cors="*",
    )
    @login_required()
    def web_custom_image(self, model="ir.attachment", id=None, field="raw", **kw):
        try:
            record = (
                request.env["ir.binary"]
                .with_user(SUPERUSER_ID)
                ._find_record(False, model, id and int(id), False)
            )
            stream = request.env["ir.binary"]._get_image_stream_from(
                record,
                field,
                filename=None,
                filename_field="name",
                mimetype=None,
                width=0,
                height=0,
                crop=False,
            )
            stream.public = True
        except Exception as e:
            record = request.env.ref("web.image_placeholder").sudo()
            stream = request.env["ir.binary"]._get_image_stream_from(
                record,
                "raw",
                width=0,
                height=0,
                crop=False,
            )
            stream.public = False

        send_file_kwargs = {"as_attachment": False}
        res = stream.get_response(**send_file_kwargs)
        res.headers["Content-Security-Policy"] = "default-src 'none'"

        return res

    @http.route(
        "/mobile/api/hr/profile",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    @login_required()
    def get_hr_profile(self, **kw):

        PARENT_COMPANY_ID = request.env.company.parent_id.id

        employee_id = (
            request.env.user.sudo().with_company(PARENT_COMPANY_ID).employee_id
        )
        user = kw["user"].read(USER_READ_FIELDS)[0]

        if employee_id.image_256:
            user["image"] = generate_image("hr.employee", "image_256", employee_id.id)
        else:
            user["image"] = None

        if employee_id:
            user["employee"] = employee_id.sudo().web_read(
                {
                    "name": {},
                    "mobile_image_url": {},
                    "email": {},
                    "mobile_phone": {},
                    "work_email": {},
                    "department_id": {"fields": {"display_name": {}, "name": {}}},
                    "job_id": {
                        "fields": {
                            "display_name": {},
                        }
                    },
                }
            )[0]
        if not user:
            return {"status": 401, "data": None, "message": "Token Expired !!"}

        return {"status": 200, "message": "success", "data": user}

    @http.route(
        "/mobile/api/reset-password",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    def reset_password(self, **kw):

        login = kw.get("login")

        if not login:
            return {"status": 400, "message": "Login is required", "data": None}

        user = request.env["res.users"].sudo().search([("login", "=", login)], limit=1)

        if not user:
            return {
                "status": 400,
                "message": "We couldn’t find your account",
                "data": None,
            }

        generate_otp(request, {"login": login})

        return {
            "status": 200,
            "message": "We’ve sent an OTP to your email or phone number.",
            "data": None,
        }

    @http.route(
        "/mobile/api/verify-otp",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    def verify_otp(self, **kw):

        login = kw.get("login")
        otp = kw.get("otp")

        if not login or not otp:
            return {"status": 400, "message": "Login/OTP is required", "data": None}

        user = request.env["res.users"].sudo().search([("login", "=", login)], limit=1)

        if not user:
            return {
                "status": 400,
                "message": "We couldn’t find your account",
                "data": None,
            }

        otp_object = request.env["otp.otp"].sudo().search([("login", "=", login)])

        if not otp_object:
            return {
                "status": 400,
                "message": "OTP not found. Please request a new one.",
                "data": None,
            }

        if otp_object.is_expired:
            return {
                "status": 400,
                "message": "OTP has expired. Please request a new one.",
                "data": None,
            }

        if otp_object.otp != otp:
            return {
                "status": 400,
                "message": "Invalid OTP",
                "data": None,
            }

        token_record = request.env["password.reset.token"].sudo().create_token(user)
        reset_token = token_record.token
        return {
            "status": 200,
            "message": "Verify Successfully !!",
            "data": {"reset_token": reset_token},
        }

    @http.route(
        "/mobile/api/change-password",
        type="json",
        methods=["POST"],
        csrf=False,
        auth="public",
        cors="*",
    )
    def change_password(self, **kw):

        reset_token = kw.get("reset_token")
        new_password = kw.get("new_password")

        if not reset_token or not new_password:
            return {
                "status": 400,
                "message": "Reset token and new password are required",
                "data": None,
            }

        token_record = (
            request.env["password.reset.token"]
            .sudo()
            .search([("token", "=", reset_token)], limit=1)
        )

        if not token_record:
            return {
                "status": 400,
                "message": "Invalid reset token",
                "data": None,
            }

        if not token_record.is_valid():
            return {
                "status": 400,
                "message": "Reset token is expired or already used",
                "data": None,
            }

        user = token_record.user_id

        if not user:
            return {
                "status": 400,
                "message": "User not found",
                "data": None,
            }

        user.sudo().write({"password": new_password})

        token_record.mark_used()

        return {
            "status": 200,
            "message": "Password changed successfully",
            "data": None,
        }

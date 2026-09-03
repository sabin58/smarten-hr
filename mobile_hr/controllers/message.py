from odoo.addons.mobile_auth.controllers.auth import generate_image
from odoo.http import request
from odoo.tools.mail import html2plaintext


def get_record_messages(model, res_id, limit):
    """Chatter of a record: comments, notifications and their tracking values.

    Shared by the detail endpoints so every screen of the mobile app renders
    the same message payload. Bodies are Html on mail.message, so they are
    handed over as plain text.
    """
    messages = (
        request.env["mail.message"]
        .sudo()
        .search(
            [
                ("model", "=", model),
                ("res_id", "=", res_id),
                ("message_type", "in", ["comment", "notification"]),
            ],
            order="id desc",
            limit=limit,
        )
    )

    data = []
    for message in messages:
        # 19.0 moved the field metadata under a 'fieldInfo' key, dropped
        # 'fieldName' from it and made 'oldValue'/'newValue' the values
        # themselves. The name of the field is read back off the tracking
        # record, so the payload of the app stays the one it knows.
        trackings_by_id = {
            tracking.id: tracking for tracking in message.tracking_value_ids
        }
        tracking_values = []
        for formatted in message.tracking_value_ids._tracking_value_format():
            tracking = trackings_by_id[formatted["id"]]
            field_info = formatted["fieldInfo"]
            tracking_values.append(
                {
                    "id": formatted["id"],
                    "field": tracking.field_id.name
                    or (tracking.field_info or {}).get("name")
                    or "unknown",
                    "label": field_info["changedField"],
                    "field_type": field_info["fieldType"],
                    "old_value": formatted["oldValue"],
                    "new_value": formatted["newValue"],
                }
            )

        data.append(
            {
                "id": message.id,
                "message_type": message.message_type,
                "body": html2plaintext(message.body or "", include_references=False),
                "tracking_values": tracking_values,
                "author_id": {
                    "id": message.author_id.id,
                    "display_name": message.author_id.display_name,
                    "name": message.author_id.name,
                    "image": generate_image(
                        "res.partner",
                        "avatar_256",
                        message.author_id.id,
                        message.author_id.write_date
                        and message.author_id.write_date.timestamp(),
                    ),
                }
                if message.author_id
                else None,
                "date": message.date,
            }
        )

    return data

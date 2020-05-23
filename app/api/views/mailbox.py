from flask import g
from flask import jsonify
from flask import request
from flask_cors import cross_origin

from app.api.base import api_bp, require_api_auth
from app.dashboard.views.mailbox import send_verification_email
from app.email_utils import (
    mailbox_already_used,
    email_domain_can_be_used_as_mailbox,
)
from app.extensions import db
from app.models import Mailbox


@api_bp.route("/mailboxes", methods=["POST"])
@cross_origin()
@require_api_auth
def create_mailbox():
    """
    Create a new mailbox. User needs to verify the mailbox via an activation email.
    Input:
        email: in body
    Output:
        the new mailbox
        - id
        - email
        - verified

    """
    user = g.user
    mailbox_email = request.get_json().get("email").lower().strip()

    if mailbox_already_used(mailbox_email, user):
        return jsonify(error=f"{mailbox_email} already used"), 400
    elif not email_domain_can_be_used_as_mailbox(mailbox_email):
        return (
            jsonify(
                error=f"{mailbox_email} cannot be used. Please note a mailbox cannot "
                f"be a disposable email address"
            ),
            400,
        )
    else:
        new_mailbox = Mailbox.create(email=mailbox_email, user_id=user.id)
        db.session.commit()

        send_verification_email(user, new_mailbox)

        return (
            jsonify(
                id=new_mailbox.id,
                email=new_mailbox.email,
                verified=new_mailbox.verified,
                default=user.default_mailbox_id == new_mailbox.id,
            ),
            201,
        )


@api_bp.route("/mailboxes/<mailbox_id>", methods=["DELETE"])
@cross_origin()
@require_api_auth
def delete_mailbox(mailbox_id):
    """
    Delete mailbox
    Input:
        mailbox_id: in url
    Output:
        200 if deleted successfully

    """
    user = g.user
    mailbox = Mailbox.get(mailbox_id)

    if not mailbox or mailbox.user_id != user.id:
        return jsonify(error="Forbidden"), 403

    if mailbox.id == user.default_mailbox_id:
        return jsonify(error="You cannot delete the default mailbox"), 400

    Mailbox.delete(mailbox_id)
    db.session.commit()

    return jsonify(deleted=True), 200


@api_bp.route("/mailboxes/<mailbox_id>", methods=["PUT"])
@cross_origin()
@require_api_auth
def update_mailbox(mailbox_id):
    """
    Update mailbox
    Input:
        mailbox_id: in url
        default (optional): in body
    Output:
        200 if updated successfully

    """
    user = g.user
    mailbox = Mailbox.get(mailbox_id)

    if not mailbox or mailbox.user_id != user.id:
        return jsonify(error="Forbidden"), 403

    data = request.get_json() or {}
    changed = False
    if "default" in data:
        is_default = data.get("default")
        if is_default:
            user.default_mailbox_id = mailbox.id
            changed = True

    if changed:
        db.session.commit()

    return jsonify(deleted=True), 200

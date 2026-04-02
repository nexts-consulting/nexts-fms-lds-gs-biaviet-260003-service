from flask import Blueprint, current_app, jsonify, request

from app.extensions import get_supabase
from app.services.biaviet_redeem import RedeemError, submit_biaviet_redeem

bp = Blueprint("redeem_biaviet", __name__, url_prefix="/api/redeem/biaviet")


@bp.post("/submit")
def submit():
    """
    Customer submit: duplicate check by phone → resolve location → weighted random gift
    from inventory → insert fms_rp_entry_gsolution_biaviet_260003.
    """
    client = get_supabase()
    if client is None:
        return (
            jsonify(
                {
                    "success": False,
                    "code": "SUPABASE_NOT_CONFIGURED",
                    "error": "Supabase client is not configured.",
                }
            ),
            503,
        )

    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        return (
            jsonify(
                {
                    "success": False,
                    "code": "VALIDATION",
                    "error": "JSON body required.",
                }
            ),
            400,
        )

    project_code = body.get("project_code") or current_app.config.get(
        "FMS_BIAVIET_PROJECT_CODE"
    )

    try:
        result = submit_biaviet_redeem(
            client,
            phone_number=body.get("phone_number", ""),
            customer_name=body.get("customer_name", ""),
            location_code=body.get("location_code", ""),
            project_code=project_code,
            bill_number=body.get("bill_number"),
            created_by=body.get("created_by"),
            sale_data=body.get("sale_data"),
            other_data=body.get("other_data"),
            gift_receive_image_url=body.get("gift_receive_image_url") or "",
        )
        return jsonify(result), 201
    except RedeemError as err:
        return (
            jsonify(
                {
                    "success": False,
                    "code": err.code,
                    "error": err.message,
                }
            ),
            err.status_code,
        )

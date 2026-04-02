from flask import Blueprint, jsonify

from app.extensions import get_supabase

bp = Blueprint("health", __name__, url_prefix="")


@bp.get("/health")
def health():
    return jsonify({"status": "ok", "service": "fms-gift-redeemtion-service"})


@bp.get("/health/supabase")
def health_supabase():
    """Quick check that Supabase client is configured (no DB query)."""
    client = get_supabase()
    if client is None:
        return (
            jsonify(
                {
                    "status": "not_configured",
                    "detail": "Missing FMS Supabase URL (NEXT_PUBLIC_API_URL or "
                    "NEXT_PUBLIC_SUPABASE_URL_FMS) or NEXT_PUBLIC_SUPABASE_ANON_KEY_FMS",
                }
            ),
            503,
        )
    return jsonify({"status": "ok", "supabase": "client_ready"})

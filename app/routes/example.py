"""
Example JSON route using Supabase. Replace `your_table` with a real table
or remove this blueprint when you add domain routes.
"""

from flask import Blueprint, jsonify

from app.extensions import get_supabase

bp = Blueprint("example", __name__, url_prefix="/api")


@bp.get("/example/ping-db")
def ping_db():
    client = get_supabase()
    if client is None:
        return jsonify({"error": "supabase_not_configured"}), 503
    # Minimal round-trip: list 0 rows from a table you create in Supabase.
    # Uncomment and set table name after you have a schema:
    # res = client.table("your_table").select("id").limit(1).execute()
    # return jsonify({"ok": True, "count": len(res.data or [])})
    return jsonify(
        {
            "ok": True,
            "hint": "Uncomment ping-db query in app/routes/example.py after creating a table.",
        }
    )

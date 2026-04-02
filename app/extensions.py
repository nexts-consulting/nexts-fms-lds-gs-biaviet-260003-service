from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from flask import Flask

if TYPE_CHECKING:
    from supabase import Client


_supabase: Optional["Client"] = None


def init_supabase(app: Flask) -> None:
    global _supabase
    url = (app.config.get("SUPABASE_FMS_URL") or "").strip()
    key = (app.config.get("SUPABASE_FMS_ANON_KEY") or "").strip()
    if not url or not key:
        app.logger.warning(
            "FMS Supabase URL or anon key missing; set NEXT_PUBLIC_API_URL (→ …/fms) "
            "or NEXT_PUBLIC_SUPABASE_URL_FMS, and NEXT_PUBLIC_SUPABASE_ANON_KEY_FMS"
        )
        _supabase = None
        return
    from supabase import create_client

    _supabase = create_client(url, key)


def get_supabase() -> Optional["Client"]:
    return _supabase

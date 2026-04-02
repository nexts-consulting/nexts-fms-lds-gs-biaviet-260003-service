import os

from dotenv import load_dotenv

load_dotenv()


def _build_fms_supabase_url() -> str:
    """
    Optional override: NEXT_PUBLIC_SUPABASE_URL_FMS or legacy SUPABASE_URL.
    """
    explicit = os.environ.get("NEXT_PUBLIC_SUPABASE_URL_FMS", "").strip()
    if explicit:
        return explicit.rstrip("/")
    base = os.environ.get("NEXT_PUBLIC_API_URL", "").strip().rstrip("/")
    if base:
        return f"{base}/fms"
    return os.environ.get("SUPABASE_URL", "").strip().rstrip("/")


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-change-me")
    PORT = int(os.environ.get("PORT", "5000"))

    # Same env names as Next client (FMS route)
    NEXT_PUBLIC_API_URL = os.environ.get("NEXT_PUBLIC_API_URL", "").strip().rstrip("/")
    NEXT_PUBLIC_SUPABASE_URL_FMS = os.environ.get("NEXT_PUBLIC_SUPABASE_URL_FMS", "").strip().rstrip("/")
    NEXT_PUBLIC_SUPABASE_ANON_KEY_FMS = os.environ.get(
        "NEXT_PUBLIC_SUPABASE_ANON_KEY_FMS", ""
    ).strip()

    SUPABASE_FMS_URL = _build_fms_supabase_url()
    SUPABASE_FMS_ANON_KEY = NEXT_PUBLIC_SUPABASE_ANON_KEY_FMS

    # Gift redeem / LDS master data (must match rows in lds_* tables)
    FMS_BIAVIET_PROJECT_CODE = os.environ.get(
        "FMS_BIAVIET_PROJECT_CODE", "nexts-gs-biaviet-2600003"
    ).strip()

"""
Bia Việt 260003 redeem flow: location + inventory-weighted gift draw + entry insert.
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from postgrest.exceptions import APIError
from supabase import Client

from app.constants import (
    DEFAULT_BIAVIET_PROJECT_CODE,
    TABLE_FMS_RP_ENTRY_BIAVIET_260003,
    TABLE_LDS_GIFT_DEFINITIONS,
    TABLE_LDS_GIFT_INVENTORY,
    TABLE_LDS_LOCATIONS,
)

logger = logging.getLogger(__name__)


def _mask_phone(phone: str, tail: int = 4) -> str:
    """Log-friendly phone (PII): keep last `tail` digits only."""
    if not phone:
        return ""
    if len(phone) <= tail:
        return "****"
    return f"***{phone[-tail:]}"


class RedeemError(Exception):
    """Business / validation error with HTTP status hint."""

    def __init__(self, message: str, status_code: int = 400, code: str = "REDEEM_ERROR"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_phone(phone: str) -> str:
    return (phone or "").strip()


@dataclass
class GiftLine:
    inventory_id: str
    gift_id: str
    remaining: int
    definition: Dict[str, Any]


def _fetch_location(
    client: Client, project_code: str, location_code: str
) -> Optional[Dict[str, Any]]:
    res = (
        client.table(TABLE_LDS_LOCATIONS)
        .select("id, code, name, project_code")
        .eq("project_code", project_code)
        .eq("code", location_code)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None


def _phone_exists(client: Client, phone: str) -> bool:
    res = (
        client.table(TABLE_FMS_RP_ENTRY_BIAVIET_260003)
        .select("id")
        .eq("phone_number", phone)
        .limit(1)
        .execute()
    )
    return bool(res.data)


def _fetch_inventory_with_definitions(
    client: Client, project_code: str, location_id: str
) -> List[GiftLine]:
    inv_res = (
        client.table(TABLE_LDS_GIFT_INVENTORY)
        .select("id, gift_id, remaining")
        .eq("project_code", project_code)
        .eq("location_id", location_id)
        .gt("remaining", 0)
        .execute()
    )
    inv_rows: List[Dict[str, Any]] = inv_res.data or []
    if not inv_rows:
        return []

    gift_ids = list({str(r["gift_id"]) for r in inv_rows})
    def_res = (
        client.table(TABLE_LDS_GIFT_DEFINITIONS)
        .select(
            "id, project_code, code, name, image_url, background_color, order_index, is_special"
        )
        .eq("project_code", project_code)
        .in_("id", gift_ids)
        .execute()
    )
    defs = {str(d["id"]): d for d in (def_res.data or [])}

    lines: List[GiftLine] = []
    for row in inv_rows:
        gid = str(row["gift_id"])
        definition = defs.get(gid)
        if not definition:
            logger.debug(
                "biaviet_redeem inventory row skipped: no gift definition gift_id=%s "
                "project_code=%s location_id=%s",
                gid,
                project_code,
                location_id,
            )
            continue
        rem = int(row["remaining"])
        if rem <= 0:
            continue
        lines.append(
            GiftLine(
                inventory_id=str(row["id"]),
                gift_id=gid,
                remaining=rem,
                definition=definition,
            )
        )
    return lines


def _weighted_pick(lines: List[GiftLine]) -> GiftLine:
    weights = [ln.remaining for ln in lines]
    return random.choices(lines, weights=weights, k=1)[0]


def _restore_inventory_remaining(
    client: Client, inventory_id: str, remaining: int
) -> None:
    now = _utc_now_iso()
    (
        client.table(TABLE_LDS_GIFT_INVENTORY)
        .update({"remaining": remaining, "updated_at": now})
        .eq("id", inventory_id)
        .execute()
    )


def _decrement_inventory(
    client: Client, inventory_id: str, expected_remaining: int
) -> bool:
    new_rem = expected_remaining - 1
    now = _utc_now_iso()
    res = (
        client.table(TABLE_LDS_GIFT_INVENTORY)
        .update({"remaining": new_rem, "updated_at": now})
        .eq("id", inventory_id)
        .eq("remaining", expected_remaining)
        .execute()
    )
    updated = res.data or []
    return len(updated) > 0


def submit_biaviet_redeem(
    client: Client,
    *,
    phone_number: str,
    customer_name: str,
    location_code: str,
    project_code: Optional[str] = None,
    bill_number: Optional[str] = None,
    created_by: Optional[str] = None,
    sale_data: Optional[Dict[str, Any]] = None,
    other_data: Optional[Dict[str, Any]] = None,
    gift_receive_image_url: str = "",
    max_decrement_retries: int = 8,
) -> Dict[str, Any]:
    """
    Returns a dict suitable for JSON response: success, customer, location, gift_won, entry.
    """
    phone = normalize_phone(phone_number)
    if not phone:
        logger.info("biaviet_redeem validation_fail code=VALIDATION reason=missing_phone")
        raise RedeemError("phone_number is required", 400, "VALIDATION")
    name = (customer_name or "").strip()
    if not name:
        logger.info(
            "biaviet_redeem validation_fail code=VALIDATION reason=missing_customer_name phone=%s",
            _mask_phone(phone),
        )
        raise RedeemError("customer_name is required", 400, "VALIDATION")
    loc_code = (location_code or "").strip()
    if not loc_code:
        logger.info(
            "biaviet_redeem validation_fail code=VALIDATION reason=missing_location_code phone=%s",
            _mask_phone(phone),
        )
        raise RedeemError("location_code is required", 400, "VALIDATION")

    pc = (project_code or DEFAULT_BIAVIET_PROJECT_CODE).strip()

    logger.info(
        "biaviet_redeem start phone=%s location_code=%s project_code=%s bill_number=%s",
        _mask_phone(phone),
        loc_code,
        pc,
        bill_number if bill_number else None,
    )

    if _phone_exists(client, phone):
        logger.warning(
            "biaviet_redeem duplicate_phone phone=%s project_code=%s",
            _mask_phone(phone),
            pc,
        )
        raise RedeemError(
            "This phone number has already been registered for a gift.",
            409,
            "DUPLICATE_PHONE",
        )

    location = _fetch_location(client, pc, loc_code)
    if not location:
        logger.warning(
            "biaviet_redeem location_not_found location_code=%s project_code=%s phone=%s",
            loc_code,
            pc,
            _mask_phone(phone),
        )
        raise RedeemError(
            f"Location not found for code '{loc_code}' and project '{pc}'.",
            404,
            "LOCATION_NOT_FOUND",
        )

    location_id = str(location["id"])
    location_name = str(location.get("name") or "")
    logger.info(
        "biaviet_redeem location_resolved location_id=%s name=%s code=%s",
        location_id,
        location_name,
        loc_code,
    )

    for attempt in range(max_decrement_retries):
        lines = _fetch_inventory_with_definitions(client, pc, location_id)
        if not lines:
            logger.warning(
                "biaviet_redeem no_stock location_id=%s project_code=%s phone=%s",
                location_id,
                pc,
                _mask_phone(phone),
            )
            raise RedeemError(
                "No gift stock available at this location.",
                422,
                "NO_STOCK",
            )
        weights = [ln.remaining for ln in lines]
        logger.debug(
            "biaviet_redeem inventory_snapshot attempt=%s lines=%s weights=%s gift_codes=%s",
            attempt + 1,
            len(lines),
            weights,
            [ln.definition.get("code") for ln in lines],
        )
        chosen = _weighted_pick(lines)
        logger.info(
            "biaviet_redeem random_pick attempt=%s inventory_id=%s gift_id=%s gift_code=%s "
            "remaining_before=%s",
            attempt + 1,
            chosen.inventory_id,
            chosen.gift_id,
            chosen.definition.get("code"),
            chosen.remaining,
        )
        if _decrement_inventory(client, chosen.inventory_id, chosen.remaining):
            logger.info(
                "biaviet_redeem decrement_ok inventory_id=%s new_remaining=%s",
                chosen.inventory_id,
                chosen.remaining - 1,
            )
            break
        logger.warning(
            "biaviet_redeem decrement_race attempt=%s/%s inventory_id=%s expected_remaining=%s",
            attempt + 1,
            max_decrement_retries,
            chosen.inventory_id,
            chosen.remaining,
        )
    else:
        logger.error(
            "biaviet_redeem inventory_race_exhausted attempts=%s location_id=%s phone=%s",
            max_decrement_retries,
            location_id,
            _mask_phone(phone),
        )
        raise RedeemError(
            "Could not reserve a gift due to high contention; please try again.",
            503,
            "INVENTORY_RACE",
        )

    now = _utc_now_iso()
    gift_payload = {
        "gift_id": chosen.gift_id,
        "gift_code": chosen.definition.get("code"),
        "gift_name": chosen.definition.get("name"),
    }
    gift_data = {
        "gifts": {chosen.gift_id: 1},
        "gift": gift_payload,
    }

    insert_row: Dict[str, Any] = {
        "created_at": now,
        "updated_at": now,
        "created_by": created_by,
        "phone_number": phone,
        "customer_name": name,
        "bill_number": bill_number,
        "sale_data": sale_data,
        "gift_data": gift_data,
        "other_data": other_data,
        "location_code": loc_code,
        "location_name": location_name or None,
    }

    try:
        # postgrest-py v2: insert() returns SyncQueryRequestBuilder (no .select().single())
        ins = (
            client.table(TABLE_FMS_RP_ENTRY_BIAVIET_260003)
            .insert(insert_row)
            .execute()
        )
        rows = ins.data or []
        entry = rows[0] if rows else None
    except APIError as exc:
        detail = exc.args[0] if exc.args else {}
        msg = (
            detail.get("message", str(exc))
            if isinstance(detail, dict)
            else str(exc)
        )
        logger.exception(
            "biaviet_redeem insert_failed phone=%s inventory_id=%s api_error=%s",
            _mask_phone(phone),
            chosen.inventory_id,
            msg,
        )
        _restore_inventory_remaining(client, chosen.inventory_id, chosen.remaining)
        logger.warning(
            "biaviet_redeem inventory_restored_after_insert_fail inventory_id=%s "
            "restored_remaining=%s",
            chosen.inventory_id,
            chosen.remaining,
        )
        raise RedeemError(msg, 500, "INSERT_FAILED") from exc

    if not entry:
        logger.error(
            "biaviet_redeem insert_empty_response phone=%s inventory_id=%s",
            _mask_phone(phone),
            chosen.inventory_id,
        )
        _restore_inventory_remaining(client, chosen.inventory_id, chosen.remaining)
        logger.warning(
            "biaviet_redeem inventory_restored_after_empty_entry inventory_id=%s",
            chosen.inventory_id,
        )
        raise RedeemError("Failed to create entry.", 500, "INSERT_FAILED")

    entry_id = entry.get("id")
    logger.info(
        "biaviet_redeem success entry_id=%s phone=%s gift_code=%s location_code=%s",
        entry_id,
        _mask_phone(phone),
        gift_payload.get("gift_code"),
        loc_code,
    )

    return {
        "success": True,
        "customer": {
            "phone_number": phone,
            "customer_name": name,
        },
        "location": {
            "code": loc_code,
            "name": location_name,
            "project_code": pc,
        },
        "gift": gift_payload,
        "entry": entry,
    }

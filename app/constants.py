"""Table and domain constants aligned with service/database/3.3. lds_system-demo.sql."""

TABLE_FMS_RP_ENTRY_BIAVIET_260003 = "fms_rp_entry_gsolution_biaviet_260003"
TABLE_LDS_LOCATIONS = "lds_mst_locations"
TABLE_LDS_GIFT_INVENTORY = "lds_mst_gift_inventory"
TABLE_LDS_GIFT_DEFINITIONS = "lds_mst_gift_definitions"
TABLE_LDS_APP_CFG_SPECIAL_CONFIG = "lds_app_cfg_special_config"

# Fallback if route does not pass config; prefer FMS_BIAVIET_PROJECT_CODE from Flask config / env.
DEFAULT_BIAVIET_PROJECT_CODE = "nexts-gs-biaviet-260003"

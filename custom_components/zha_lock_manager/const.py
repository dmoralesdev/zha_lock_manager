DOMAIN = "zha_lock_manager"
PLATFORMS: list[str] = []  # no entities; UI-only + storage + WS API

STORAGE_KEY = DOMAIN
STORAGE_VERSION = 1

KEY_STORAGE_KEY = f"{DOMAIN}_key"
KEY_STORAGE_VERSION = 1

CONF_LOCKS = "locks"  # list of lock dicts
CONF_ALARMO_ENABLED = "alarmo_enabled"
CONF_ALARMO_ENTITY_ID = "alarmo_entity_id"

CONF_SLOT_OFFSET = "slot_offset"  # optional per-lock offset fix
DEFAULT_SLOT_OFFSET = 0

EVENT_ZHA = "zha_event"

# Frontend / panel
PANEL_URL_BASE = "/zha-lock-manager-frontend"
PANEL_MODULE_URL = f"{PANEL_URL_BASE}/zha_lock_manager_panel.js"
PANEL_PATH = "frontend"
PANEL_TITLE = "Zigbee Locks"
PANEL_ICON = "mdi:lock-smart"
PANEL_URL_PATH = "zha-lock-manager"

# WebSocket command types
WS_NS = "zlm"
WS_LIST_LOCKS = f"{WS_NS}/list_locks"
WS_GET_LOCK = f"{WS_NS}/get_lock"
WS_SET_CODE = f"{WS_NS}/set_code"
WS_ENABLE_CODE = f"{WS_NS}/enable_code"
WS_DISABLE_CODE = f"{WS_NS}/disable_code"
WS_CLEAR_CODE = f"{WS_NS}/clear_code"
WS_RENAME_CODE = f"{WS_NS}/rename_code"
WS_SAVE_LOCK_META = f"{WS_NS}/save_lock_meta"  # name/slot_offset/max_slots
from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import async_register_built_in_panel, async_remove_panel
from homeassistant.components.http import StaticPathConfig

from .const import (
    DOMAIN,
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_BASE,
    PANEL_URL_PATH,
    PANEL_PATH,
    PANEL_MODULE_URL,
)


async def async_register_panel(hass: HomeAssistant) -> None:
    """Register (or update) the sidebar panel and static assets.

    We guard against duplicates so reloading the integration or options won't crash
    with ValueError("Overwriting panel ...").
    """
    root = Path(__file__).parent
    panel_dir = root / PANEL_PATH

    domain_data = hass.data.setdefault(DOMAIN, {})

    # Serve static assets once
    if not domain_data.get("static_paths_registered"):
        await hass.http.async_register_static_paths(
            [StaticPathConfig(PANEL_URL_BASE, str(panel_dir), True)]
        )
        domain_data["static_paths_registered"] = True

    # (Re)register sidebar panel; if exists, remove and re-add to update
    try:
        async_register_built_in_panel(
            hass,
            component_name="custom",
            frontend_url_path=PANEL_URL_PATH,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            require_admin=True,
            config={
                "_panel_custom": {
                    "name": "zha-lock-manager-panel",
                    "module_url": PANEL_MODULE_URL,
                }
            },
        )
    except ValueError:
        # Panel already exists; remove and re-add
        async_remove_panel(hass, PANEL_URL_PATH)
        async_register_built_in_panel(
            hass,
            component_name="custom",
            frontend_url_path=PANEL_URL_PATH,
            sidebar_title=PANEL_TITLE,
            sidebar_icon=PANEL_ICON,
            require_admin=True,
            config={
                "_panel_custom": {
                    "name": "zha-lock-manager-panel",
                    "module_url": PANEL_MODULE_URL,
                }
            },
        )

    domain_data["panel_registered"] = True

# ===============================
from __future__ import annotations

from pathlib import Path

from homeassistant.core import HomeAssistant
from homeassistant.components.frontend import async_register_built_in_panel
from homeassistant.components.http import StaticPathConfig

from .const import (
    PANEL_ICON,
    PANEL_TITLE,
    PANEL_URL_BASE,
    PANEL_URL_PATH,
    PANEL_PATH,
    PANEL_MODULE_URL,
)


async def async_register_panel(hass: HomeAssistant) -> None:
    root = Path(__file__).parent
    panel_dir = root / PANEL_PATH

    # Register / serve static assets (module JS)
    await hass.http.async_register_static_paths(
        [StaticPathConfig(PANEL_URL_BASE, str(panel_dir), True)]
    )

    # Register sidebar panel
    async_register_built_in_panel(
        hass,
        component_name="custom",
        frontend_url_path=PANEL_URL_PATH,
        sidebar_title=PANEL_TITLE,
        sidebar_icon=PANEL_ICON,
        require_admin=True,
        config={
            "_panel_custom": {
                "name": "zha-lock-manager-panel",
                "module_url": PANEL_MODULE_URL,
            }
        },
    )

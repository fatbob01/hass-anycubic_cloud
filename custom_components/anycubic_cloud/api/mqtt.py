"""MQTT API helpers for Anycubic Cloud integration."""

from __future__ import annotations

from ..anycubic_cloud_api.anycubic_api import AnycubicMQTTAPI as AnycubicBaseAPI


class AnycubicMQTTAPI(AnycubicBaseAPI):
    """MQTT helper."""

    # ------------------------------------------------------------------
    # Orders such as CAMERA_OPEN (1001) are still executed over the
    # Cloud HTTP API.  Provide a passthrough so callers don’t care
    # which API variant they’re holding.
    # ------------------------------------------------------------------
    async def async_send_order(self, order_id: int, device_id: str | None = None):
        """Delegate to underlying Cloud API for order calls."""
        return await super().async_send_order(order_id, device_id=device_id)


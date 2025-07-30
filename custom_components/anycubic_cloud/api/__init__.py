"""Helper API wrappers for Anycubic Cloud integration."""

from __future__ import annotations

from typing import Any

from ..anycubic_cloud_api.anycubic_api import AnycubicMQTTAPI as _AnycubicAPI
from ..anycubic_cloud_api.data_models.orders import AnycubicBaseOrderRequest

class AnycubicCloudAPI(_AnycubicAPI):
    """Wrapper exposing simplified async_send_order."""

    async def async_send_order(self, order_id: int, device_id: int) -> Any:
        request = AnycubicBaseOrderRequest(order_id=order_id, printer_id=device_id)
        return await self._send_anycubic_order(order_request=request, raw_data=True)

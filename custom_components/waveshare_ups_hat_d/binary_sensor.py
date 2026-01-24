from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WaveshareUpsHatDCoordinator

BINARY_SENSORS: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key="vbus_present",
        name="VBUS Present",
        device_class=BinarySensorDeviceClass.POWER,
    ),
    BinarySensorEntityDescription(
        key="charging",
        name="Charging",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING,
    ),
    BinarySensorEntityDescription(
        key="on_battery",
        name="On Battery",
        device_class=BinarySensorDeviceClass.PROBLEM,
    ),
)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    coordinator: WaveshareUpsHatDCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WaveshareBinary(coordinator, description) for description in BINARY_SENSORS])

class WaveshareBinary(CoordinatorEntity[WaveshareUpsHatDCoordinator], BinarySensorEntity):
    def __init__(self, coordinator, description: BinarySensorEntityDescription):
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_name = description.name
        self._attr_has_entity_name = True
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{description.key}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.entry.entry_id)},
            manufacturer="Waveshare",
            model="UPS HAT (D)",
            name=coordinator.device_name,
        )

    @property
    def is_on(self) -> bool | None:
        val = self.coordinator.data.get(self.entity_description.key)
        return bool(val) if val is not None else None

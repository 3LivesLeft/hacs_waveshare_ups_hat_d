from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.config_entries import ConfigEntry

from smbus2 import SMBus

from .const import DOMAIN
from .i2c import read_u8, read_u16_le, read_s16_le
from .ina219 import INA219

_LOGGER = logging.getLogger(__name__)


class WaveshareUpsHatDCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        self.configured_name = entry.data["name"]
        self.device_name = entry.title or self.configured_name
        self.i2c_bus_num = entry.data["i2c_bus"]
        self.mcu_addr = entry.data["mcu_addr"]
        self.ina_addr = entry.data["ina219_addr"]

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=entry.data["scan_interval"]),
        )

    def _read_mcu(self, bus: SMBus) -> Dict[str, Any]:
        # Registers from Waveshare UPS HAT register tables (0x2D slave). :contentReference[oaicite:10]{index=10}
        charging_reg = read_u8(bus, self.mcu_addr, 0x02)

        # Best-guess bit mapping from Waveshare description: charging / fast / VBUS powered :contentReference[oaicite:11]{index=11}
        charging = bool(charging_reg & 0x01)
        fast_charging = bool(charging_reg & 0x02)
        vbus_present = bool(charging_reg & 0x04)

        batt_mv = read_u16_le(bus, self.mcu_addr, 0x20)
        batt_ma = read_s16_le(bus, self.mcu_addr, 0x22)
        batt_pct = read_u16_le(bus, self.mcu_addr, 0x24)  # some firmwares use 16-bit, low byte often enough
        rem_mah = read_u16_le(bus, self.mcu_addr, 0x26)
        rem_dis_min = read_u16_le(bus, self.mcu_addr, 0x28)

        vbus_mv = read_u16_le(bus, self.mcu_addr, 0x10)
        vbus_ma = read_u16_le(bus, self.mcu_addr, 0x12)
        vbus_mw = read_u16_le(bus, self.mcu_addr, 0x14)

        # clamp percent if firmware returns 16-bit weirdness
        pct = batt_pct
        if pct > 1000:
            pct = pct & 0xFF
        if pct > 100:
            pct = 100

        return {
            "mcu_charging_reg": charging_reg,
            "charging": charging,
            "fast_charging": fast_charging,
            "vbus_present": vbus_present,
            "battery_voltage_v": batt_mv / 1000.0,
            "battery_current_ma": batt_ma,
            "battery_percent": pct,
            "remaining_capacity_mah": rem_mah,
            "remaining_discharge_time_min": rem_dis_min,
            "vbus_voltage_v": vbus_mv / 1000.0,
            "vbus_current_ma": vbus_ma,
            "vbus_power_w": vbus_mw / 1000.0,
        }

    def _read_ina(self, bus: SMBus) -> Dict[str, Any]:
        ina = INA219(bus, self.ina_addr)

        return {
            "ina_bus_voltage_v": ina.bus_voltage_v(),
            "ina_shunt_voltage_mv": ina.shunt_voltage_mv(),
            "ina_current_ma": ina.current_ma(),
            "ina_power_w": ina.power_w(),
        }

    def _sync_update(self) -> Dict[str, Any]:
        try:
            with SMBus(self.i2c_bus_num) as bus:
                data: Dict[str, Any] = {}
                data.update(self._read_mcu(bus))
                # INA219 exists on UPS HAT (D) at 0x43 per Waveshare docs :contentReference[oaicite:12]{index=12}
                data.update(self._read_ina(bus))
                data["on_battery"] = not data["vbus_present"]
                _LOGGER.debug("Waveshare UPS HAT data on bus %s: %s", self.i2c_bus_num, data)
                return data
        except Exception as exc:
            _LOGGER.exception(
                "Failed to update Waveshare UPS HAT on bus %s (MCU 0x%X INA219 0x%X)",
            self.i2c_bus_num,
            self.mcu_addr,
            self.ina_addr,
            )
            raise UpdateFailed(str(exc)) from exc

    async def _async_update_data(self) -> Dict[str, Any]:
        return await self.hass.async_add_executor_job(self._sync_update)

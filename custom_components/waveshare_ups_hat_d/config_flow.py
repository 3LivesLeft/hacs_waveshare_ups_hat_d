from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries

from .const import (
    DOMAIN,
    DEFAULT_I2C_BUS,
    DEFAULT_MCU_ADDR,
    DEFAULT_INA219_ADDR,
    DEFAULT_SCAN_INTERVAL,
)

DEFAULT_NAME = "UPS HAT D"


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        user_input = user_input or {}
        errors: dict[str, str] = {}
        cleaned: dict[str, int | str] = {}

        if user_input:
            try:
                cleaned["i2c_bus"] = self._parse_positive_int(
                    user_input.get("i2c_bus", DEFAULT_I2C_BUS), minimum=0
                )
            except ValueError:
                errors["i2c_bus"] = "invalid_bus"

            try:
                cleaned["scan_interval"] = self._parse_positive_int(
                    user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL), minimum=5
                )
            except ValueError:
                errors["scan_interval"] = "invalid_interval"

            try:
                cleaned["mcu_addr"] = self._parse_address(
                    user_input.get("mcu_addr", hex(DEFAULT_MCU_ADDR))
                )
            except ValueError:
                errors["mcu_addr"] = "invalid_address"

            try:
                cleaned["ina219_addr"] = self._parse_address(
                    user_input.get("ina219_addr", hex(DEFAULT_INA219_ADDR))
                )
            except ValueError:
                errors["ina219_addr"] = "invalid_address"

            name = (user_input.get("name") or DEFAULT_NAME).strip()
            cleaned["name"] = name or DEFAULT_NAME

            if not errors:
                await self.async_set_unique_id(
                    f"{cleaned['i2c_bus']:02d}-{cleaned['mcu_addr']:02X}-{cleaned['ina219_addr']:02X}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=cleaned["name"],
                    data={
                        "name": cleaned["name"],
                        "i2c_bus": cleaned["i2c_bus"],
                        "mcu_addr": cleaned["mcu_addr"],
                        "ina219_addr": cleaned["ina219_addr"],
                        "scan_interval": cleaned["scan_interval"],
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._schema(user_input),
            errors=errors,
        )

    def _schema(self, user_input: dict) -> vol.Schema:
        return vol.Schema(
            {
                vol.Required(
                    "name", default=user_input.get("name", DEFAULT_NAME)
                ): str,
                vol.Required(
                    "i2c_bus", default=user_input.get("i2c_bus", DEFAULT_I2C_BUS)
                ): int,
                vol.Required(
                    "mcu_addr",
                    default=self._addr_default(user_input.get("mcu_addr"), DEFAULT_MCU_ADDR),
                ): str,
                vol.Required(
                    "ina219_addr",
                    default=self._addr_default(user_input.get("ina219_addr"), DEFAULT_INA219_ADDR),
                ): str,
                vol.Required(
                    "scan_interval",
                    default=user_input.get("scan_interval", DEFAULT_SCAN_INTERVAL),
                ): int,
            }
        )

    @staticmethod
    def _addr_default(value, fallback: int) -> str:
        if isinstance(value, int):
            return hex(value)
        if value is None:
            return hex(fallback)
        return str(value)

    @staticmethod
    def _parse_address(value) -> int:
        text = str(value).strip().lower()
        if text.startswith("0x"):
            text = text[2:]
        addr = int(text, 16)
        if not 0 <= addr <= 0x7F:
            raise ValueError
        return addr

    @staticmethod
    def _parse_positive_int(value, *, minimum: int = 1) -> int:
        num = int(value)
        if num < minimum:
            raise ValueError
        return num

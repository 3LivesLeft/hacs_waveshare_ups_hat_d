from __future__ import annotations

import asyncio
import sys
import types
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

import pytest


class _FakeHomeAssistant:
    """Tiny stand-in for Home Assistant's core object used in coordinator tests."""

    def __init__(self) -> None:
        self.loop = asyncio.get_event_loop()

    async def async_add_executor_job(self, func: Callable[..., Any], *args: Any) -> Any:
        return func(*args)


class _FakeDataUpdateCoordinator:
    """Minimal subset of Home Assistant's DataUpdateCoordinator."""

    def __init__(
        self,
        hass: _FakeHomeAssistant,
        *,
        logger: Any,
        name: str,
        update_interval: Any,
    ) -> None:
        self.hass = hass
        self.logger = logger
        self.name = name
        self.update_interval = update_interval

    async def _async_update_data(self) -> Any:  # pragma: no cover - to be overridden by tests
        raise NotImplementedError

    async def async_config_entry_first_refresh(self) -> None:
        await self._async_update_data()


class _FakeUpdateFailed(Exception):
    """Matches the UpdateFailed exception in HA."""


@dataclass
class _FakeConfigEntry:
    """Simplified replacement for ConfigEntry."""

    data: Dict[str, Any]
    title: Optional[str] = None
    version: int = 1
    minor_version: int = 1
    entry_id: str = "test-entry"
    unique_id: Optional[str] = None
    options: Dict[str, Any] = field(default_factory=dict)

    async def async_set_unique_id(self, unique_id: str) -> None:
        self.unique_id = unique_id

    async def async_reload(self) -> None:  # pragma: no cover - helper stub
        return None


class FakeSMBus:
    """Context-manager friendly SMBus stub for unit tests."""

    def __init__(self, bus_num: int = 1) -> None:
        self.bus_num = bus_num
        self.registers: Dict[tuple[int, int], int] = {}
        self.closed = False

    def __enter__(self) -> "FakeSMBus":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True

    # --- API surface used by the integration ---
    def read_byte_data(self, addr: int, reg: int) -> int:
        return self.registers.get((addr, reg), 0)

    def write_i2c_block_data(self, addr: int, reg: int, data: list[int]) -> None:
        hi = data[0] if data else 0
        lo = data[1] if len(data) > 1 else 0
        self.registers[(addr, reg)] = hi
        self.registers[(addr, reg + 1)] = lo

    def read_i2c_block_data(self, addr: int, reg: int, size: int) -> list[int]:
        return [self.registers.get((addr, reg + offset), 0) for offset in range(size)]


@pytest.fixture(autouse=True)
def stub_homeassistant_modules(monkeypatch: pytest.MonkeyPatch) -> None:
    """Inject lightweight HA modules so imports in the integration succeed."""
    ha_module = types.ModuleType("homeassistant")
    core_module = types.ModuleType("homeassistant.core")
    helpers_module = types.ModuleType("homeassistant.helpers")
    update_module = types.ModuleType("homeassistant.helpers.update_coordinator")
    config_entries_module = types.ModuleType("homeassistant.config_entries")

    core_module.HomeAssistant = _FakeHomeAssistant
    update_module.DataUpdateCoordinator = _FakeDataUpdateCoordinator
    update_module.UpdateFailed = _FakeUpdateFailed
    config_entries_module.ConfigEntry = _FakeConfigEntry

    ha_module.core = core_module  # type: ignore[attr-defined]
    ha_module.helpers = helpers_module  # type: ignore[attr-defined]
    helpers_module.update_coordinator = update_module  # type: ignore[attr-defined]
    ha_module.config_entries = config_entries_module  # type: ignore[attr-defined]

    monkeypatch.setitem(sys.modules, "homeassistant", ha_module)
    monkeypatch.setitem(sys.modules, "homeassistant.core", core_module)
    monkeypatch.setitem(sys.modules, "homeassistant.helpers", helpers_module)
    monkeypatch.setitem(
        sys.modules, "homeassistant.helpers.update_coordinator", update_module
    )
    monkeypatch.setitem(sys.modules, "homeassistant.config_entries", config_entries_module)


@pytest.fixture(autouse=True)
def stub_smbus2(monkeypatch: pytest.MonkeyPatch) -> FakeSMBus:
    """Patch smbus2.SMBus with the FakeSMBus helper."""
    smbus2_module = types.ModuleType("smbus2")
    fake_bus = FakeSMBus()
    smbus2_module.SMBus = lambda bus_num=1: FakeSMBus(bus_num)  # pylint: disable=unnecessary-lambda
    monkeypatch.setitem(sys.modules, "smbus2", smbus2_module)
    return fake_bus
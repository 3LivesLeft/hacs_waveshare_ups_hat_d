from __future__ import annotations

import pytest


def _build_register_template() -> dict[tuple[int, int], int]:
    """Populate the MCU register map with deterministic sample data."""
    addr = 0x2D
    template: dict[tuple[int, int], int] = {
        (addr, 0x02): 0x05,  # charging + vbus_present bits
    }

    def set_le(register: int, value: int) -> None:
        template[(addr, register)] = value & 0xFF
        template[(addr, register + 1)] = (value >> 8) & 0xFF

    set_le(0x20, 12_345)  # battery millivolts -> 12.345 V
    set_le(0x22, (1 << 16) - 500)  # signed battery current -> -500 mA
    set_le(0x24, 85)  # battery percent (already within 0-100)
    set_le(0x26, 2_000)  # remaining capacity mAh
    set_le(0x28, 90)  # remaining discharge minutes
    set_le(0x10, 5_100)  # VBUS mV -> 5.1 V
    set_le(0x12, 1_500)  # VBUS current mA
    set_le(0x14, 8_000)  # VBUS power mW -> 8 W
    return template


class StubBus:
    """Context-manager SMBus stand-in that mimics the subset we use."""

    def __init__(self, bus_num: int, register_template: dict[tuple[int, int], int]) -> None:
        self.bus_num = bus_num
        self._template = register_template
        self.registers = dict(register_template)
        self.closed = False

    def __enter__(self) -> "StubBus":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.closed = True

    def read_byte_data(self, addr: int, reg: int) -> int:
        return self.registers.get((addr, reg), 0)

    def read_i2c_block_data(self, addr: int, reg: int, size: int) -> list[int]:
        return [self.registers.get((addr, reg + offset), 0) for offset in range(size)]

    def write_i2c_block_data(self, addr: int, reg: int, data: list[int]) -> None:
        for idx, byte in enumerate(data):
            self.registers[(addr, reg + idx)] = byte & 0xFF


class SpyINA219:
    """Lightweight INA219 stub that records bus state at construction."""

    init_bus_closed_states: list[bool] = []

    def __init__(self, bus: StubBus, addr: int) -> None:
        self.addr = addr
        self.bus = bus
        SpyINA219.init_bus_closed_states.append(bus.closed)

    def bus_voltage_v(self) -> float:
        return 4.98

    def shunt_voltage_mv(self) -> float:
        return 12.3

    def current_ma(self) -> float:
        return 456.7

    def power_w(self) -> float:
        return 2.34


def test_sync_update_uses_fresh_bus_and_exposes_expected_payload(monkeypatch: pytest.MonkeyPatch) -> None:
    # Import inside the test so patched modules from conftest are in place.
    from homeassistant.core import HomeAssistant
    from homeassistant.config_entries import ConfigEntry
    from custom_components.waveshare_ups_hat_d import const
    from custom_components.waveshare_ups_hat_d import coordinator as coordinator_mod

    register_template = _build_register_template()
    created_buses: list[StubBus] = []

    def bus_factory(bus_num: int) -> StubBus:
        bus = StubBus(bus_num, register_template)
        created_buses.append(bus)
        return bus

    monkeypatch.setattr(coordinator_mod, "SMBus", bus_factory)
    monkeypatch.setattr(coordinator_mod, "INA219", SpyINA219)
    SpyINA219.init_bus_closed_states = []

    hass = HomeAssistant()
    entry = ConfigEntry(
        data={
            "name": "Test UPS",
            "i2c_bus": 1,
            "mcu_addr": const.DEFAULT_MCU_ADDR,
            "ina219_addr": const.DEFAULT_INA219_ADDR,
            "scan_interval": const.DEFAULT_SCAN_INTERVAL,
        },
        title="Test UPS",
    )

    coordinator = coordinator_mod.WaveshareUpsHatDCoordinator(hass, entry)

    first = coordinator._sync_update()
    second = coordinator._sync_update()

    # Each refresh should create a brand-new SMBus context that closes afterward.
    assert len(created_buses) == 2
    assert all(bus.closed for bus in created_buses)
    assert SpyINA219.init_bus_closed_states == [False, False]

    # Validate a few representative datapoints to ensure MCU parsing still works.
    assert first["battery_voltage_v"] == pytest.approx(12.345)
    assert first["battery_current_ma"] == -500
    assert first["battery_percent"] == 85
    assert first["vbus_voltage_v"] == pytest.approx(5.1)
    assert first["vbus_power_w"] == pytest.approx(8.0)
    assert first["on_battery"] is False

    # Ensures INA stub contributions are incorporated.
    assert second["ina_bus_voltage_v"] == pytest.approx(4.98)
    assert second["ina_current_ma"] == pytest.approx(456.7)
from __future__ import annotations

# INA219 registers
REG_CONFIG = 0x00
REG_SHUNT_VOLTAGE = 0x01
REG_BUS_VOLTAGE = 0x02
REG_POWER = 0x03
REG_CURRENT = 0x04
REG_CALIBRATION = 0x05

class INA219:
    def __init__(self, bus, addr: int, shunt_ohms: float = 0.1):
        self.bus = bus
        self.addr = addr
        self.shunt_ohms = shunt_ohms
        self._calibrate_32v_2a()

    def _write_u16(self, reg: int, value: int) -> None:
        hi = (value >> 8) & 0xFF
        lo = value & 0xFF
        self.bus.write_i2c_block_data(self.addr, reg, [hi, lo])

    def _read_u16(self, reg: int) -> int:
        data = self.bus.read_i2c_block_data(self.addr, reg, 2)
        return (data[0] << 8) | data[1]

    def _read_s16(self, reg: int) -> int:
        val = self._read_u16(reg)
        if val & 0x8000:
            val -= 0x10000
        return val

    def _calibrate_32v_2a(self) -> None:
        # Conservative config: 32V range, 320mV shunt, 12-bit ADCs
        # Config value is a commonly used baseline; if readings are off we can tune.
        config = 0x399F
        self._write_u16(REG_CONFIG, config)

        # Current_LSB ~ 100uA -> Cal = 0.04096 / (Current_LSB * Rshunt)
        current_lsb = 0.0001
        cal = int(0.04096 / (current_lsb * self.shunt_ohms))
        self._write_u16(REG_CALIBRATION, cal)

        self.current_lsb = current_lsb
        self.power_lsb = current_lsb * 20.0

    def bus_voltage_v(self) -> float:
        raw = self._read_u16(REG_BUS_VOLTAGE)
        # Bits: [15:3] data, LSB = 4mV
        return ((raw >> 3) * 0.004)

    def shunt_voltage_mv(self) -> float:
        raw = self._read_s16(REG_SHUNT_VOLTAGE)
        # LSB = 10uV
        return raw * 0.01

    def current_ma(self) -> float:
        raw = self._read_s16(REG_CURRENT)
        return (raw * self.current_lsb) * 1000.0

    def power_w(self) -> float:
        raw = self._read_u16(REG_POWER)
        return raw * self.power_lsb

from __future__ import annotations

from smbus2 import SMBus

def read_u8(bus: SMBus, addr: int, reg: int) -> int:
    return bus.read_byte_data(addr, reg)

def read_u16_le(bus: SMBus, addr: int, reg_low: int) -> int:
    lo = bus.read_byte_data(addr, reg_low)
    hi = bus.read_byte_data(addr, reg_low + 1)
    return (hi << 8) | lo

def read_s16_le(bus: SMBus, addr: int, reg_low: int) -> int:
    val = read_u16_le(bus, addr, reg_low)
    if val & 0x8000:
        val -= 0x10000
    return val

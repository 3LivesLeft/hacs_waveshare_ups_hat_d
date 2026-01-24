# Waveshare UPS HAT (D) – Home Assistant Integration

Custom [Home Assistant](https://www.home-assistant.io/) integration that surfaces live telemetry from the Waveshare UPS HAT (D) board via I²C. The integration is designed to be HACS-compatible and exposes both battery and power path details captured from the on-board MCU and INA219 current sensor.

---

## Features

- **Config Flow (UI):** Discover and configure the UPS HAT entirely from the Home Assistant UI with validation for I²C bus, addresses, and polling interval.
- **Coordinated Updates:** A single `DataUpdateCoordinator` polls the MCU and INA219 in one pass to keep all entities synchronized.
- **Entity Coverage:**
  - *Binary Sensors:* `VBUS Present`, `Charging`, `On Battery`
  - *Sensors:* Battery %, voltage, current, capacity, discharge time, VBUS voltage/current/power, and raw INA219 bus/shunt metrics.
- **Device Metadata:** All entities are grouped under a Waveshare UPS HAT device with manufacturer/model info for a tidy device registry.
- **I²C Helpers:** Lightweight helpers for unsigned/signed register reads plus a minimal INA219 client tailored for the HAT’s 0x43 address.
- **Debug Logging:** Coordinated debug output and structured exception logging for easier troubleshooting.

---

## Installation (HACS)

1. In Home Assistant, open **HACS → Integrations → ⋮ → Custom repositories**.
2. Add this repository URL and select category **Integration**.
3. After it appears in HACS, click **Download**.
4. Restart Home Assistant to load the new component.

> **Manual install:** copy the `custom_components/waveshare_ups_hat_d/` folder into your Home Assistant `config/custom_components/` directory and restart.

---

## Configuration

1. Navigate to **Settings → Devices & Services → Add Integration**.
2. Search for **“Waveshare UPS HAT (D)”**.
3. Provide:
   - **Name:** Friendly label for the device.
   - **I²C Bus:** Typically `1` on Raspberry Pi variants.
   - **MCU Address:** Default `0x2D`.
   - **INA219 Address:** Default `0x43`.
   - **Update Interval:** Seconds between polls (min 5 s).
4. Submit to create the entry. The integration enforces a unique ID based on bus + addresses, preventing duplicates.

---

## Entities

| Domain          | Entity name suffix              | Notes                                      |
|-----------------|---------------------------------|--------------------------------------------|
| Binary Sensor   | `VBUS Present`                  | True when external power is detected       |
| Binary Sensor   | `Charging`                      | True when the pack is charging             |
| Binary Sensor   | `On Battery`                    | True when running from battery alone       |
| Sensor          | `Battery` (%)                   | Battery state-of-charge                    |
| Sensor          | `Battery Voltage` (V)           | MCU-reported battery voltage               |
| Sensor          | `Battery Current` (mA)          | Positive when charging, negative discharge |
| Sensor          | `Remaining Capacity` (mAh)      | Estimated pack capacity remaining          |
| Sensor          | `Remaining Discharge Time` (min)| Estimated runtime left                     |
| Sensor          | `VBUS Voltage` / `Current` / `Power` | Input rail metrics                     |
| Sensor          | `INA Bus Voltage` / `Shunt Voltage` / `Current` / `Power` | Raw INA219 data |

All sensors use native Home Assistant units, device classes, and measurement state classes, enabling Energy dashboard aggregation where applicable.

---

## Development Notes

- `smbus2==0.5.0` is required (declared in `manifest.json`); Home Assistant installs it automatically.
- Module layout:
  - `coordinator.py`: Handles synchronized reads and exposes shared data.
  - `sensor.py` / `binary_sensor.py`: Entity registrations using entity descriptions.
  - `ina219.py` & `i2c.py`: Hardware helpers.
  - `config_flow.py`: UI-driven setup with validation and user feedback translations.
- Run `python3 -m compileall custom_components` to lint for syntax errors before publishing.

---

## Troubleshooting

- **Permission denied / Device not found:** Ensure the Home Assistant host has I²C enabled and the user can access `/dev/i2c-*`.
- **Incorrect readings:** Confirm addresses match the board’s jumpers; adjust via the integration options if necessary.
- **Multiple HATs:** Each unique bus/address combination can be added separately thanks to unique ID enforcement.

---

## License

This project is provided under the MIT License. Refer to the repository’s `LICENSE` file for details.

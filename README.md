# Waveshare UPS HAT (D) – Home Assistant Integration

Custom [Home Assistant](https://www.home-assistant.io/) integration that surfaces live telemetry from the Waveshare UPS HAT (D) board via I²C. The integration is designed to be HACS-compatible and exposes both battery and power path details captured from the on-board MCU and INA219 current sensor.

![Photo of the Waveshare UPS HAT (D) board](https://thepihut.com/cdn/shop/files/21700-ups-hat-d-for-raspberry-pi-4-3-waveshare-wav-25567-1212921167_1000x.jpg?v=1766502552)
*Waveshare UPS HAT (D) board with standoffs and power connectors.*

Use the badge below to open the “Add repository to HACS” dialog in Home Assistant automatically:

[![Add to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=3LivesLeft&repository=hacs_waveshare_ups_hat_d)

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

### Derived on-battery template sensor

Users who want to trigger graceful shutdown automations after the HAT has been discharging for a set amount of time can create a template binary sensor that watches the INA219 current value and adds configurable on/off delays. Add this block to your Home Assistant `configuration.yaml` (or the include where you manage template definitions):

```yaml
template:
  - binary_sensor:
      - name: "UPS On Battery (Derived)"
        unique_id: ups_on_battery_derived
        state: >
          {% set i = states('sensor.ups_hat_d_ina_current') %}
          {% if i in ['unknown','unavailable','none'] %}
            false
          {% else %}
            {{ (i | float) > 20 }}
          {% endif %}
        device_class: power
        delay_on:
          seconds: 15
        delay_off:
          seconds: 30
```

The `delay_on`/`delay_off` settings ensure the sensor only flips after consistent current draw, giving you a stable trigger for time-based shutdown workflows. Because the template integration reads from `configuration.yaml`, reloading Templates (or restarting) will apply any tweaks you make to this block.

### Automation examples

A ready-to-import set of automations lives in `examples/automation_power_events.yaml`. It includes:
- **UPS - Power cut detected (30s):** persistent notification if the derived on-battery sensor stays on for 30 seconds.
- **UPS - Power restored (60s stable):** confirmation notification once the sensor has been off for 60 seconds.
- **UPS - Warning after 60 minutes on battery:** hour-long outage warning to prep for a shutdown.
- **UPS - Shutdown after 150 minutes on battery:** guarded host shutdown after 2.5 hours on battery, ensuring Home Assistant has been fully booted for at least 10 minutes.

Copy the content into `automations.yaml` (or your preferred split package) and adjust entity IDs, delays, and services to match your environment.

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

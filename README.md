[![SWUbanner](https://raw.githubusercontent.com/vshymanskyy/StandWithUkraine/main/banner-direct-single.svg)](https://stand-with-ukraine.pp.ua/)

# Home Assistant Teknix ESPRO Integration


> 🏠 Custom integration for **Teknix ESPRO 15** (and potentially other ESPRO models) that enables **local MQTT-based control** and **Home Assistant automation** for your water and home heating system.

---

## 💡 Description

This integration allows you to locally control and monitor your **Heater ESPRO** unit via **MQTT**, using the same communication protocol as the Tasmota firmware installed inside the heater.  
It was **reverse engineered** by analyzing the MQTT commands exchanged between the heater and its native mobile app, as there is **no official API** provided by the manufacturer.

The goal of this project is to enable **local automation** and **energy-aware control** of your heater, which is especially useful in regions with power outages — like **Ukraine**, where I live.  
Thanks to MQTT, all commands and telemetry stay within your **local network** — no cloud dependency.

---

## ⚙️ Pre-requisites

Before installing and using this integration, a few configuration steps are required.

1. Open the Boiler config page in your browser:  
```
http://{HEATER_HOST}/mq?
```
Replace `{HEATER_HOST}` with your heater’s local IP address. 

2. Update the MQTT configuration fields:
- **Host** – your Home Assistant MQTT broker address (usually `core-mosquitto`)
- **User** – your MQTT username  
- **Password** – your MQTT password

3. Save the configuration. Changes will apply in few seconds

> ⚠️ **Warning:**  
> Changing MQTT settings will make the **native mobile app stop working**, as the heater will now communicate only with your local MQTT broker.  
> Please **create a backup** of the original configuration page before applying changes.  

📸 *[Placeholder for screenshot of MQTT configuration page]*

---

## ⚠️ Compatibility Notice

This custom integration was developed and tested using the **Teknix ESPRO 15** model.  
Although the internal logic is likely similar for other ESPRO models, compatibility is **not guaranteed**.  
If you have another model — feel free to test and report results via GitHub Issues.

---

## 🧰 Installation

The easiest way to install this integration is via [HACS][hacs-url].  
Click the button below:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yaro-tkachenko&repository=ha-teknix&category=Integration)

### Manual Installation (not recommended)

* Copy the entire `custom_components/teknix/` directory to your server's `<config>/custom_components` directory
* Restart Home Assistant

---

## 🖥️ Configuration

You can configure the integration via the **Home Assistant UI**:

1. Go to **Settings → Devices & Services**
2. Click **Add Integration**
3. Search for **Teknix**
4. Enter the following details:
- **Serial Number** – printed on your heater (e.g. `22110223150100004`)
- **Model** – select your model (default: `ESPRO 15`)



The integration will automatically discover and create the following entities:
- Temperature sensors (house loop, tank water)
- Heating levels (house / tank)
- Power and mode switches
- Diagnostic and system entities
---

## 🧠 Background

This project was created after reverse engineering the Tasmota MQTT payloads sent by the heater.
Since no official local API or cloud endpoint is available, the communication protocol was derived manually from the tele/ MQTT topics.
The integration decodes binary-like payloads (e.g. I1&80&26&...Z) into structured sensor values.

> “Because we live in Ukraine and experience blackouts, I wanted to ensure full local control and automation of heating to improve comfort and efficiency.”

## Licence
MIT © [Yaroslav Tkachenko](https://github.com/yaro-tkachenko)

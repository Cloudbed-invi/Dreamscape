# Dreamscape Bot

## 🚀 Quick Start Guide

### 1. Installation
Ensure you have Python 3.10+ installed.
```bash
pip install -r requirements.txt
```

### 2. Connect Your Device / Emulator
The bot uses ADB (Android Debug Bridge) to interact with your game. You need to configure the connection based on the device you are using. Update the `"adb_ip"` in **`bot_settings.json`** accordingly (or let the bot use the default).

#### 📱 Native Android Device (USB / Wi-Fi)
1. **Enable Developer Options**: Go to Settings > About Phone, and tap "Build Number" 7 times.
2. **Enable USB Debugging**: Go to Settings > Developer Options, and turn on "USB Debugging".
3. **Connect to PC**: Plug in your device via USB.
4. **Configure IP**:
   - If using USB, you can often leave `"adb_ip": "127.0.0.1:5555"` or use the device's specific serial number if multiple devices are connected.
   - For Wi-Fi debugging (Android 11+), find your device's IP address (e.g., `192.168.1.100:5555`) in Wi-Fi settings and set `"adb_ip": "192.168.1.100:5555"`.

#### 🎮 BlueStacks
1. Open BlueStacks.
2. Go to **Settings** > **Advanced** (or **Preferences** depending on version).
3. Enable **Android Debug Bridge (ADB)**.
4. Look at the port provided (often `5555`, `5554`, or something like `5565`).
5. Update `bot_settings.json` with the correct port, e.g., `"adb_ip": "127.0.0.1:5555"`.

#### 🎮 MuMu Player
1. Open MuMu Player (Version 12 recommended).
2. Go to **Settings** > **Others** (or System).
3. Enable **ADB Debugging** / **USB Debugging**.
4. MuMu typically uses port `7555` or `16384`. 
5. Update `bot_settings.json` with `"adb_ip": "127.0.0.1:7555"` (or the IP shown in MuMu's network settings, e.g., `192.168.2.11:5555`).

---

### 3. Start the Controller
The easiest way to use the bot is the **Floating Controller**:
```powershell
python .\controller.py
```
This will open a small control bar that stays on top of your game. Use it to trigger setup and start the bot with one click.

### 4. Calibration (Do this once)
Run the selector to show the bot where your game window is:
```powershell
python .\region_selector.py
```
- **Step 1**: Draw a box over the **Entire Game Area**.
- **Step 2**: Draw a box over the **OCR List Area** (the bottom names).

---

## 🗺️ How to Map a New Level (Auto-Setup)

1. **Start the Auto-Setup**: Run the setup script before you begin the level:
   ```powershell
   python .\auto_setup_level.py
   ```
2. **Start the Level**: Click "Start" in the game.
3. **Automatic Capture**: The script will wait for the countdown to end, capture the map image, and start recording item names automatically.
4. **Map the Coordinates**: Once the level is done, run the mapper:
   ```powershell
   python .\coordinate_mapper.py
   ```
   - **Left Click**: Mark the object.
   - **Right Click**: Skip.
5. Copy the output and paste it into **`master_dict.txt`**.

---

## 🤖 Running the Bot
Once your map is saved in `master_dict.txt`, just run the bot:
```powershell
python .\bot.py
```

## 📅 Daily Session Management (UTC 00:00)

The bot automatically tracks time based on **UTC 00:00** (the server reset time). 

When you start `bot.py` on a new day:
1. It will detect the date change and prompt you to **Archive**.
2. If you accept, it moves yesterday's `targets.txt`, `master_dict.txt`, and screenshots into the `archives/` folder.
3. It clears your workspace so you can begin Teacher Mode and Mapping for the new day's map immediately.

---
## ⚙️ Configuration
You can adjust speed and "human-ness" in the controller UI or `bot_settings.json`:
- `reaction`: Delay before clicking after seeing an item.
- `randomness`: Randomness in click position (keep low for small objects).
- `cooldown`: Wait time between items.

---
*Disclaimer: Use at your own risk. This tool is for educational purposes.*

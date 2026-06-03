## 🚀 Quick Start Guide

### 1. Installation
Ensure you have Python 3.10+ installed.
```bash
pip install -r requirements.txt
```

### 2. Start the Controller
The easiest way to use the bot is the **Floating Controller**:
```powershell
python .\controller.py
```
This will open a small control bar that stays on top of your game. Use it to trigger setup and start the bot with one click.

### 3. Setup MuMu Player
1. Open MuMu Player (Version 12 recommended).
2. Enable **USB Debugging** in settings.
3. Update the `ADB_ADDRESS` in `bot.py` and `capture_map.py` to match your MuMu IP (e.g., `192.168.2.11`).

### 3. Calibration (Do this once)
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
You can adjust speed and "human-ness" in `bot.py`:
- `HUMAN_REACTION_RANGE`: Delay before clicking after seeing an item.
- `HUMAN_CLICK_OFFSET`: Randomness in click position (keep low for small objects).
- `SUCCESS_COOLDOWN`: Wait time between items.

---
*Disclaimer: Use at your own risk. This tool is for educational purposes.*

import os
import json
import shutil
from datetime import datetime, timezone

def check_and_reset():
    session_file = "last_session.json"
    # Get current UTC date string
    current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    
    last_date = None
    if os.path.exists(session_file):
        with open(session_file, "r") as f:
            try:
                data = json.load(f)
                last_date = data.get("last_run_date")
            except:
                pass

    # If the day has changed
    if last_date and last_date != current_date:
        print("\n" + "="*40)
        print("🚨  NEW DAY DETECTED (UTC 00:00 Reset)  🚨")
        print("="*40)
        print(f"Last Session: {last_date}")
        print(f"Current Date: {current_date}")
        print("-" * 40)
        
        choice = input("Would you like to ARCHIVE yesterday's map and data? (y/n): ").lower()
        
        if choice == 'y':
            archive_dir = os.path.join("archives", last_date)
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
            
            # Files to move
            to_move = ["targets.txt", "master_dict.txt"]
            for filename in to_move:
                if os.path.exists(filename):
                    shutil.move(filename, os.path.join(archive_dir, filename))
                    print(f"Moved {filename} to archive.")
            
            # Move map images
            if os.path.exists("maps"):
                map_files = [f for f in os.listdir("maps") if f.endswith(".png")]
                if map_files:
                    img_archive = os.path.join(archive_dir, "maps")
                    os.makedirs(img_archive, exist_ok=True)
                    for f in map_files:
                        shutil.move(os.path.join("maps", f), os.path.join(img_archive, f))
                    print(f"Moved {len(map_files)} images to archive.")

            # Reset fresh files
            with open("targets.txt", "w") as f: f.write("")
            with open("master_dict.txt", "w") as f: f.write("{}")
            print("\n✅ Archive complete. Your workspace is ready for the new day!")
        else:
            print("\nSkipping archive. Continuing with existing data.")

    # Update session file
    with open(session_file, "w") as f:
        json.dump({"last_run_date": current_date}, f)

if __name__ == "__main__":
    check_and_reset()

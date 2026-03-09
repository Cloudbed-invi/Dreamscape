# REMINDER: Run "adb connect 127.0.0.1:5555" in your terminal before running this script!

import sys
import cv2
import numpy as np
from ppadb.client import Client as AdbClient

def main():
    # 1. Initialize the AdbClient on host 127.0.0.1 and port 5037
    client = AdbClient(host="127.0.0.1", port=5037)

    # 2. Get the device at 127.0.0.1:5555
    device = client.device("127.0.0.1:5555")

    if device is None:
        print("Error: Device at 127.0.0.1:5555 not found.")
        print("Please ensure your emulator is running and you have run 'adb connect 127.0.0.1:5555'.")
        sys.exit(1)
        
    print("Device connected successfully. Capturing screen...")

    # 3. Capture screen directly into a bytearray variable
    raw_screen = device.screencap()

    if not raw_screen:
        print("Error: Failed to capture screen.")
        sys.exit(1)

    # 4. Convert raw bytes into a NumPy array and decode it into a standard BGR OpenCV image
    image_array = np.frombuffer(raw_screen, dtype=np.uint8)
    img = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if img is None:
        print("Error: Failed to decode the image.")
        sys.exit(1)

    # 5. Crop the image array to isolate the bottom UI area (bottom 400 pixels of 900x1600 image)
    cropped_img = img[1200:1600, 0:900]

    # 6. Display the cropped image
    cv2.imshow("Pure ADB Vision", cropped_img)
    print("Press any key in the image window to exit...")
    cv2.waitKey(0)
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
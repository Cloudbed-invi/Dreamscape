import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32

def get_window_rect(window_name):
    # We use EnumWindows to find the LARGEST window with this name
    # (to avoid tiny background windows with the same name)
    best_hwnd = None
    max_area = 0
    
    EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
    
    def callback(hwnd, lParam):
        nonlocal best_hwnd, max_area
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            if buf.value == window_name:
                rect = wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                area = (rect.right - rect.left) * (rect.bottom - rect.top)
                if area > max_area:
                    max_area = area
                    best_hwnd = hwnd
        return True

    user32.EnumWindows(EnumWindowsProc(callback), 0)
    
    if best_hwnd:
        rect = wintypes.RECT()
        user32.GetWindowRect(best_hwnd, ctypes.byref(rect))
        width = rect.right - rect.left
        height = rect.bottom - rect.top
        
        print(f"[{window_name}] Found Best Window: {width}x{height} at ({rect.left}, {rect.top})")
        
        # We want the bottom part for OCR
        bottom_h = int(height * 0.30)
        bottom_top = rect.bottom - bottom_h
        
        # 1. Full Window Screenshot
        full_region = {
            'top': rect.top,
            'left': rect.left,
            'width': width,
            'height': height
        }
        
        # 2. OCR List Screenshot (Bottom 30%)
        ocr_region = {
            'top': bottom_top,
            'left': rect.left,
            'width': width,
            'height': bottom_h
        }
        
        import mss
        import mss.tools
        with mss.mss() as sct:
            # Save Full View
            full_img = sct.grab(full_region)
            mss.tools.to_png(full_img.rgb, full_img.size, output="mumu_full_view.png")
            
            # Save OCR View
            ocr_img = sct.grab(ocr_region)
            mss.tools.to_png(ocr_img.rgb, ocr_img.size, output="ocr_list_view.png")
            
            print(f"DEBUG: Saved 'mumu_full_view.png' and 'ocr_list_view.png'")
            
    else:
        print(f"Window '{window_name}' not found!")

# Found! The title is "MuMuPlayer" (no space)
get_window_rect("MuMuPlayer")

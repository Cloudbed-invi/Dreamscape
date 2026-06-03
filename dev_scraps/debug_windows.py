import ctypes
import ctypes.wintypes as wintypes

user32 = ctypes.windll.user32
user32.SetProcessDPIAware()

EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)

def foreach_window(hwnd, lParam):
    if user32.IsWindowVisible(hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buf, length + 1)
        title = buf.value
        
        class_buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, class_buf, 256)
        class_name = class_buf.value
        
        # MuMu 12 and other emulators often use these class names
        target_classes = ["Qt5QWindowIcon", "Win32Window", "RenderWindow", "Nemu", "Nox"]
        
        # Check if the title or class name matches common emulator patterns
        if any(cls in class_name for cls in target_classes) or "MuMu" in title or "Player" in title:
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            w = rect.right - rect.left
            h = rect.bottom - rect.top
            
            # Filter out tiny overlay windows or background processes
            if w > 200 and h > 200:
                print(f"MATCH FOUND!")
                print(f"  Title: {title}")
                print(f"  Class: {class_name}")
                print(f"  Size:  {w}x{h}")
                print(f"  Pos:   ({rect.left}, {rect.top})")
                print("-" * 30)
                
    return True

print("Scanning for Emulator Windows (Title or Class)...\n")
user32.EnumWindows(EnumWindowsProc(foreach_window), 0)
print("\nDone. If you see a match above that looks like your MuMu window, tell me the 'Title'!")

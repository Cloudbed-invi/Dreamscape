import os
import subprocess
import re

def main():
    print("Searching for MuMu processes...")
    # Common MuMu process names
    process_names = ["MuMuPlayer.exe", "NemuPlayer.exe", "MuMuVMMHeadless.exe"]
    pids = []
    
    result = subprocess.run(["tasklist", "/FO", "LIST"], capture_output=True, text=True)
    current_name = ""
    for line in result.stdout.splitlines():
        if "Image Name:" in line:
            current_name = line.split(":")[-1].strip()
        if "PID:" in line:
            pid = line.split(":")[-1].strip()
            if "MuMu" in current_name or "Nemu" in current_name:
                pids.append(pid)

    if not pids:
        print("Error: Could not find any MuMu processes running. Is MuMu open?")
        return

    print(f"Found MuMu PIDs: {pids}. Scanning for listening ports...")
    
    potential_ports = set()
    netstat = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
    for line in netstat.stdout.splitlines():
        if any(pid in line for pid in pids) and "LISTENING" in line:
            # Extract port from "127.0.0.1:XXXXX"
            match = re.search(r"127\.0\.0\.1:(\d+)", line)
            if match:
                potential_ports.add(int(match.group(1)))

    # Also add default ones just in case
    potential_ports.update([7555, 16384, 16416, 5555])

    adb_exe = os.path.join("platform-tools", "adb.exe")
    found = False
    
    for port in sorted(list(potential_ports)):
        addr = f"127.0.0.1:{port}"
        print(f"Checking {addr}...")
        subprocess.run([adb_exe, "connect", addr], capture_output=True, text=True)
        
        verify = subprocess.run([adb_exe, "-s", addr, "shell", "getprop", "ro.product.model"], capture_output=True, text=True)
        if verify.returncode == 0:
            print(f"\nSUCCESS! MuMu is at: {addr}")
            found = True
            break
            
    if not found:
        print("\nStill could not find it. Please manually check MuMu Settings > Other > ADB.")

if __name__ == "__main__":
    main()

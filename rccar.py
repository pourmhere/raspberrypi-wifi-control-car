#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║              RCCAR — Raspberry Pi WiFi Car                  ║
║                                                              ║
║  PIN WIRING  (physical BOARD pin numbers):                  ║
║    L298N IN1 → Pin 29  (BCM 5)                              ║
║    L298N IN2 → Pin 31  (BCM 6)                              ║
║    L298N IN3 → Pin 33  (BCM 13)                             ║
║    L298N IN4 → Pin 35  (BCM 19)                             ║
║    L298N ENA → Pi Pin 2  (5V)   always on                   ║
║    L298N ENB → Pi Pin 4  (5V)   always on                   ║
║    L298N GND → Pi Pin 6  (GND)                              ║
║    Battery + → L298N 12V terminal                           ║
║                                                              ║
║  WiFi Hotspot: SSID=RCCAR  Pass=12345678                    ║
║  Open browser: http://192.168.4.1                           ║
║  Run: sudo python3 rccar.py                                 ║
╚══════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import subprocess
import http.server
import socketserver

# ─────────────────────────────────────────────────────────────
#  MUST RUN AS ROOT
# ─────────────────────────────────────────────────────────────
if os.geteuid() != 0:
    print("[ERROR] This script must be run with sudo:")
    print("        sudo python3 rccar.py")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
#  GPIO
# ─────────────────────────────────────────────────────────────
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BOARD)
    GPIO.setwarnings(False)
    HAS_GPIO = True
except ImportError:
    HAS_GPIO = False
    print("[WARN] RPi.GPIO not found — motor control disabled")

# ─────────────────────────────────────────────────────────────
#  PIN DEFINITIONS  (physical BOARD numbers)
# ─────────────────────────────────────────────────────────────
IN1 = 29
IN2 = 31
IN3 = 33
IN4 = 35

# ─────────────────────────────────────────────────────────────
#  CONFIG
# ─────────────────────────────────────────────────────────────
SSID       = "RCCAR"
PASSPHRASE = "12345678"
AP_IP      = "192.168.4.1"
HTTP_PORT  = 80
IFACE      = "wlan0"

# ─────────────────────────────────────────────────────────────
#  GPIO SETUP
# ─────────────────────────────────────────────────────────────
def gpio_setup():
    if not HAS_GPIO:
        return
    for pin in [IN1, IN2, IN3, IN4]:
        GPIO.setup(pin, GPIO.OUT)
        GPIO.output(pin, GPIO.LOW)
    print("[GPIO] Pins 29 31 33 35 ready")

# ─────────────────────────────────────────────────────────────
#  MOTOR COMMANDS
# ─────────────────────────────────────────────────────────────
H = GPIO.HIGH if HAS_GPIO else 1
L = GPIO.LOW  if HAS_GPIO else 0

def _set(a, b, c, d):
    if not HAS_GPIO:
        return
    GPIO.output(IN1, a)
    GPIO.output(IN2, b)
    GPIO.output(IN3, c)
    GPIO.output(IN4, d)

def stop():
    _set(L, L, L, L)
    print("[CAR] STOP")

def forward():
    _set(H, L, H, L)
    print("[CAR] FORWARD")

def backward():
    _set(L, H, L, H)
    print("[CAR] BACKWARD")

def turn_left():
    _set(L, H, H, L)
    print("[CAR] LEFT")

def turn_right():
    _set(H, L, L, H)
    print("[CAR] RIGHT")

# ─────────────────────────────────────────────────────────────
#  WEB PAGE
# ─────────────────────────────────────────────────────────────
WEB_PAGE = b"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width,initial-scale=1,user-scalable=no">
<meta name="apple-mobile-web-app-capable" content="yes">
<title>RCCAR</title>
<style>
*{box-sizing:border-box;-webkit-tap-highlight-color:transparent;
  user-select:none;margin:0;padding:0;}
body{font-family:Arial,sans-serif;background:#0d0d1a;color:#eee;
  padding:12px 8px 30px;text-align:center;}
h2{color:#00d4ff;font-size:22px;letter-spacing:3px;margin:10px 0 4px;}
#badge{display:inline-block;padding:5px 28px;border-radius:20px;
  background:#0f3460;color:#00d4ff;font-size:14px;font-weight:bold;
  border:1px solid #00d4ff;margin:6px 0 20px;min-width:150px;}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;
  max-width:320px;margin:0 auto;}
.btn{height:90px;border-radius:16px;border:none;font-weight:bold;
  font-size:32px;color:#fff;cursor:pointer;touch-action:none;
  display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:4px;
  transition:filter .07s,transform .05s;}
.lbl{font-size:11px;opacity:.65;font-weight:normal;}
.btn.act{filter:brightness(2.2);transform:scale(.88);}
.mov{background:#163a5f;border:1px solid #1e5080;}
.stp{background:#700000;border:1px solid #cc2200;}
.blank{visibility:hidden;pointer-events:none;}
</style>
</head>
<body>
<h2>&#128663; RCCAR</h2>
<div id="badge">STOP</div>
<div class="grid">
  <div class="blank btn"></div>
  <button class="btn mov" id="F"
    ontouchstart="ev(event,'F')" ontouchend="ev(event,'S')"
    onmousedown="ev(event,'F')" onmouseup="ev(event,'S')" onmouseleave="ev(event,'S')">
    &#9650;<span class="lbl">FORWARD</span></button>
  <div class="blank btn"></div>

  <button class="btn mov" id="L"
    ontouchstart="ev(event,'L')" ontouchend="ev(event,'S')"
    onmousedown="ev(event,'L')" onmouseup="ev(event,'S')" onmouseleave="ev(event,'S')">
    &#9668;<span class="lbl">LEFT</span></button>
  <button class="btn stp" id="S"
    ontouchstart="ev(event,'S')" onmousedown="ev(event,'S')">
    &#9632;<span class="lbl">STOP</span></button>
  <button class="btn mov" id="R"
    ontouchstart="ev(event,'R')" ontouchend="ev(event,'S')"
    onmousedown="ev(event,'R')" onmouseup="ev(event,'S')" onmouseleave="ev(event,'S')">
    &#9658;<span class="lbl">RIGHT</span></button>

  <div class="blank btn"></div>
  <button class="btn mov" id="B"
    ontouchstart="ev(event,'B')" ontouchend="ev(event,'S')"
    onmousedown="ev(event,'B')" onmouseup="ev(event,'S')" onmouseleave="ev(event,'S')">
    &#9660;<span class="lbl">BACKWARD</span></button>
  <div class="blank btn"></div>
</div>
<script>
var last='',active=null;
var N={F:'FORWARD',B:'BACKWARD',L:'LEFT',R:'RIGHT',S:'STOP'};
function ev(e,c){
  e.preventDefault();
  if(c===last) return;
  last=c;
  if(active) active.classList.remove('act');
  var el=document.getElementById(c);
  if(el){el.classList.add('act');active=el;}
  document.getElementById('badge').innerText=N[c]||c;
  fetch('/'+c).catch(function(){});
}
document.addEventListener('visibilitychange',function(){
  if(document.hidden){last='';fetch('/S').catch(function(){});}
});
</script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────
#  HELPERS
# ─────────────────────────────────────────────────────────────
def run(cmd, show=False):
    """Run shell command. Returns (returncode, combined output)."""
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    out = (r.stdout + r.stderr).strip()
    if show and out:
        print(f"    {out}")
    return r.returncode, out

def installed(prog):
    code, _ = run(f"which {prog}")
    return code == 0

def ip_on_iface():
    _, out = run(f"ip addr show {IFACE}")
    return AP_IP in out

# ─────────────────────────────────────────────────────────────
#  METHOD 1 — nmcli  (Raspberry Pi OS Bullseye / Bookworm)
# ─────────────────────────────────────────────────────────────
def hotspot_nmcli():
    print("[WiFi] Method 1: nmcli …")

    # Delete any leftover profile
    run(f'nmcli connection delete "{SSID}" 2>/dev/null')
    time.sleep(1)

    code, out = run(
        f'nmcli device wifi hotspot '
        f'ifname {IFACE} '
        f'ssid "{SSID}" '
        f'password "{PASSPHRASE}" '
        f'con-name "{SSID}"',
        show=True
    )
    if code != 0:
        print(f"[WiFi] nmcli failed (rc={code})")
        return False

    # Force static IP (nmcli may assign a different subnet)
    time.sleep(2)
    run(f'nmcli connection modify "{SSID}" '
        f'ipv4.method shared '
        f'ipv4.addresses {AP_IP}/24')
    run(f'nmcli connection up "{SSID}"')

    # Wait up to 10 s for IP to appear
    for i in range(10):
        time.sleep(1)
        if ip_on_iface():
            print(f"[WiFi] ✓ nmcli hotspot '{SSID}' → {AP_IP}")
            return True
    print("[WiFi] nmcli: IP never confirmed")
    return False

# ─────────────────────────────────────────────────────────────
#  METHOD 2 — hostapd + dnsmasq  (Buster / manual install)
# ─────────────────────────────────────────────────────────────
HOSTAPD_CONF = f"""\
interface={IFACE}
driver=nl80211
ssid={SSID}
hw_mode=g
channel=6
ieee80211n=1
wmm_enabled=1
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
wpa=2
wpa_passphrase={PASSPHRASE}
wpa_key_mgmt=WPA-PSK
wpa_pairwise=TKIP CCMP
rsn_pairwise=CCMP
"""

DNSMASQ_CONF = f"""\
interface={IFACE}
bind-interfaces
server=8.8.8.8
dhcp-range=192.168.4.2,192.168.4.20,255.255.255.0,24h
"""

def hotspot_hostapd():
    print("[WiFi] Method 2: hostapd + dnsmasq …")

    if not installed("hostapd"):
        print("[WiFi] hostapd not installed — skipping")
        return False

    with open("/tmp/hostapd_rccar.conf", "w") as f:
        f.write(HOSTAPD_CONF)
    with open("/tmp/dnsmasq_rccar.conf", "w") as f:
        f.write(DNSMASQ_CONF)

    # Kill anything holding wlan0
    run("systemctl stop hostapd 2>/dev/null")
    run("systemctl stop dnsmasq 2>/dev/null")
    run("systemctl stop wpa_supplicant 2>/dev/null")
    run("nmcli radio wifi off 2>/dev/null")
    run("rfkill unblock wifi 2>/dev/null")
    time.sleep(1)

    # Assign static IP
    run(f"ip link set {IFACE} down")
    run(f"ip addr flush dev {IFACE}")
    run(f"ip addr add {AP_IP}/24 dev {IFACE}")
    run(f"ip link set {IFACE} up")
    time.sleep(1)

    # Start hostapd
    code, out = run("hostapd -B /tmp/hostapd_rccar.conf", show=True)
    if code != 0:
        print(f"[WiFi] hostapd failed (rc={code}): {out}")
        return False

    # Start dnsmasq
    run("killall dnsmasq 2>/dev/null")
    time.sleep(0.5)
    code2, out2 = run("dnsmasq -C /tmp/dnsmasq_rccar.conf", show=True)
    if code2 != 0:
        print(f"[WiFi] dnsmasq failed (rc={code2}): {out2}")
        # dnsmasq fail is non-fatal — hotspot still broadcasts, just no DHCP
        # clients will need manual IP 192.168.4.x

    if ip_on_iface():
        print(f"[WiFi] ✓ hostapd hotspot '{SSID}' → {AP_IP}")
        return True

    print("[WiFi] hostapd: could not confirm IP")
    return False

# ─────────────────────────────────────────────────────────────
#  MASTER HOTSPOT SETUP
# ─────────────────────────────────────────────────────────────
def setup_hotspot():
    print("=" * 52)
    print(f"  Hotspot SSID : {SSID}")
    print(f"  Password     : {PASSPHRASE}")
    print(f"  IP address   : {AP_IP}")
    print("=" * 52)

    has_nmcli   = installed("nmcli")
    has_hostapd = installed("hostapd")
    print(f"[WiFi] nmcli present   : {has_nmcli}")
    print(f"[WiFi] hostapd present : {has_hostapd}")
    print()

    if has_nmcli and hotspot_nmcli():
        return True

    if has_hostapd and hotspot_hostapd():
        return True

    # ── Nothing worked ──────────────────────────────────────
    print()
    print("[WiFi] ✗ Hotspot could not start.")
    print()
    print("  Fix: run these commands once, then retry:")
    print()
    print("    sudo apt update")
    print("    sudo apt install -y hostapd dnsmasq")
    print("    sudo systemctl unmask hostapd")
    print("    sudo rfkill unblock wifi")
    print("    sudo python3 rccar.py")
    print()
    print("[WiFi] Falling back to LAN mode (no hotspot) …")
    return False

# ─────────────────────────────────────────────────────────────
#  HTTP SERVER
# ─────────────────────────────────────────────────────────────
ROUTES = {"/F": forward, "/B": backward,
          "/L": turn_left, "/R": turn_right, "/S": stop}

class CarHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # suppress per-request log noise

    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ROUTES:
            ROUTES[path]()
            self.send_response(204)
            self.send_header("Connection", "close")
            self.end_headers()
        else:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(WEB_PAGE)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(WEB_PAGE)

# ─────────────────────────────────────────────────────────────
#  MAIN
# ─────────────────────────────────────────────────────────────
def main():
    print()
    print("  ██████╗  ██████╗ ██████╗  █████╗ ██████╗ ")
    print("  ██╔══██╗██╔════╝██╔════╝ ██╔══██╗██╔══██╗")
    print("  ██████╔╝██║     ██║      ███████║██████╔╝")
    print("  ██╔══██╗██║     ██║      ██╔══██║██╔══██╗")
    print("  ██║  ██║╚██████╗╚██████╗ ██║  ██║██║  ██║")
    print("  ╚═╝  ╚═╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝")
    print()

    gpio_setup()
    stop()

    hotspot_ok = setup_hotspot()
    bind_ip    = AP_IP if hotspot_ok else "0.0.0.0"

    print()
    print(f"[HTTP] Binding to {bind_ip}:{HTTP_PORT}")

    # Free port 80 if something already holds it
    run("fuser -k 80/tcp 2>/dev/null")
    time.sleep(0.5)

    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer((bind_ip, HTTP_PORT), CarHandler) as httpd:
            print()
            if hotspot_ok:
                print(f"  ✓ Connect phone to WiFi  :  {SSID}")
                print(f"  ✓ Open browser           :  http://{AP_IP}")
            else:
                _, lan_ip = run("hostname -I")
                print(f"  WiFi hotspot failed — LAN IP(s): {lan_ip}")
                print(f"  Try opening: http://<pi-ip>:{HTTP_PORT}")
            print()
            print("  Press Ctrl+C to stop")
            print()
            httpd.serve_forever()
    except OSError as e:
        print(f"[HTTP] Cannot bind port {HTTP_PORT}: {e}")
        print("       Run:  sudo fuser -k 80/tcp   then retry")
    except KeyboardInterrupt:
        print("\n[Main] Shutting down …")
    finally:
        stop()
        if HAS_GPIO:
            GPIO.cleanup()
        run("killall hostapd dnsmasq 2>/dev/null")
        print("[Main] Done.")

if __name__ == "__main__":
    main()

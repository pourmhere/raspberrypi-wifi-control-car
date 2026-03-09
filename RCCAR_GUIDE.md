# RCCAR — Complete Setup & Run Guide
## WiFi Controlled Car on Raspberry Pi 3

---

## WIRING

```
Raspberry Pi (Board Pin)     L298N
─────────────────────────────────────
Pin 29  (BCM 5)    ───────►  IN1
Pin 31  (BCM 6)    ───────►  IN2
Pin 33  (BCM 13)   ───────►  IN3
Pin 35  (BCM 19)   ───────►  IN4
Pin 2   (5V)       ───────►  ENA   (left motor speed, always on)
Pin 4   (5V)       ───────►  ENB   (right motor speed, always on)
Pin 6   (GND)      ───────►  GND   (shared ground)

Battery 7–12V (+)  ───────►  L298N VS / 12V terminal
Battery GND        ───────►  L298N GND (same GND as Pi)

L298N OUT1 / OUT2  ───────►  Left  motor wires
L298N OUT3 / OUT4  ───────►  Right motor wires
```

---

## STEP 1 — Install Raspberry Pi OS

1. Download Raspberry Pi Imager: https://www.raspberrypi.com/software/
2. Flash **Raspberry Pi OS Lite (64-bit)** to microSD
3. Click ⚙️ before writing:
   - Enable SSH ✓
   - Set hostname: `rccar`
   - Username: `pi`  Password: `raspberry`
4. Insert card and boot the Pi
5. SSH in from your PC:
   ```bash
   ssh pi@rccar.local
   ```

---

## STEP 2 — Run This Once: Install Everything

Copy and paste this entire block into the terminal:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip hostapd dnsmasq
sudo systemctl unmask hostapd
sudo systemctl disable hostapd
sudo systemctl disable dnsmasq
sudo rfkill unblock wifi
pip3 install RPi.GPIO --break-system-packages
```

> `unmask hostapd` is critical — on Raspberry Pi OS it is masked by default and will silently fail without this step.

---

## STEP 3 — Copy the Script

From your PC:
```bash
scp rccar.py pi@rccar.local:/home/pi/
```

Or paste it directly on the Pi:
```bash
nano /home/pi/rccar.py
# Paste the full script content
# Save: Ctrl+O → Enter → Ctrl+X
```

---

## STEP 4 — Run

```bash
sudo python3 /home/pi/rccar.py
```

You should see output like this:
```
  ██████╗  ██████╗ ██████╗  █████╗ ██████╗
  ...

[GPIO] Pins 29 31 33 35 ready
[CAR] STOP
====================================================
  Hotspot SSID : RCCAR
  Password     : 12345678
  IP address   : 192.168.4.1
====================================================
[WiFi] nmcli present   : True
[WiFi] hostapd present : True

[WiFi] Method 1: nmcli …
[WiFi] ✓ nmcli hotspot 'RCCAR' → 192.168.4.1

[HTTP] Binding to 192.168.4.1:80

  ✓ Connect phone to WiFi  :  RCCAR
  ✓ Open browser           :  http://192.168.4.1

  Press Ctrl+C to stop
```

---

## STEP 5 — Drive the Car

1. On your phone → **Settings → WiFi**
2. Connect to: **RCCAR**
3. Password: **12345678**
4. Open any browser → go to: **http://192.168.4.1**
5. **Hold** a button to move — **release** to stop automatically

---

## STEP 6 — Auto-Start on Boot (Optional)

```bash
sudo nano /etc/systemd/system/rccar.service
```

Paste this:
```ini
[Unit]
Description=RCCAR WiFi Car
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/rccar.py
WorkingDirectory=/home/pi
Restart=on-failure
User=root

[Install]
WantedBy=multi-user.target
```

Enable it:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rccar
sudo systemctl start rccar

# Check it's running:
sudo systemctl status rccar
```

---

## TROUBLESHOOTING

### Hotspot not appearing on phone

Run these commands one by one and check output:

```bash
# 1. Check WiFi adapter is visible
ip link show wlan0

# 2. Unblock WiFi if rfkill is blocking it
sudo rfkill unblock wifi
sudo rfkill list

# 3. Unmask hostapd (critical step many people miss)
sudo systemctl unmask hostapd

# 4. Make sure hostapd is installed
sudo apt install -y hostapd dnsmasq

# 5. Try running again
sudo python3 /home/pi/rccar.py
```

---

### "nmcli failed" in output

```bash
# Check NetworkManager is running
sudo systemctl status NetworkManager

# If not installed, install it
sudo apt install -y network-manager
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager
sudo reboot

# Then run the script again
sudo python3 /home/pi/rccar.py
```

---

### "Cannot bind port 80"

Something else is using port 80:
```bash
sudo fuser -k 80/tcp
sudo python3 /home/pi/rccar.py
```

---

### Motors not moving / wrong direction

- Verify wiring: IN1→Pin29, IN2→Pin31, IN3→Pin33, IN4→Pin35
- If one side goes backward when it should go forward, swap that motor's two wires on the L298N OUT terminals
- Make sure `RPi.GPIO` is installed: `pip3 install RPi.GPIO --break-system-packages`
- Make sure you run with `sudo`

---

### Phone connects to RCCAR but browser shows nothing

- Wait 5–10 seconds after connecting — DHCP takes a moment
- Make sure you type exactly: `http://192.168.4.1` (not https)
- Try on Chrome, not Safari (iOS sometimes redirects)
- Disable mobile data on phone while connected to RCCAR

---

## QUICK REFERENCE

| Command | What it does |
|---------|-------------|
| `sudo python3 rccar.py` | Start the car server |
| `Ctrl + C` | Stop the server cleanly |
| `sudo systemctl status rccar` | Check auto-start status |
| `sudo rfkill unblock wifi` | Fix blocked WiFi adapter |
| `sudo systemctl unmask hostapd` | Fix masked hostapd |
| `sudo fuser -k 80/tcp` | Free port 80 if blocked |
| `hostname -I` | Show Pi's IP address on LAN |

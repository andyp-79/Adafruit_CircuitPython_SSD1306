# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2017 James DeVito for Adafruit Industries
# SPDX-License-Identifier: MIT

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import subprocess
import time
import glob

import busio
from board import SCL, SDA
from PIL import Image, ImageDraw, ImageFont

import adafruit_ssd1306

# Create the I2C interface.
i2c = busio.I2C(SCL, SDA)

# Create the SSD1306 OLED class.
# The first two parameters are the pixel width and pixel height.  Change these
# to the right size for your display!
disp = adafruit_ssd1306.SSD1306_I2C(128, 32, i2c)

# Clear display.
disp.fill(0)
disp.show()

# Create blank image for drawing.
# Make sure to create image with mode '1' for 1-bit color.
width = disp.width
height = disp.height
image = Image.new("1", (width, height))

# Get drawing object to draw on image.
draw = ImageDraw.Draw(image)

# Draw a black filled box to clear the image.
draw.rectangle((0, 0, width, height), outline=0, fill=0)

# Draw some shapes.
# First define some constants to allow easy resizing of shapes.
padding = -2
top = padding
bottom = height - padding
# Move left to right keeping track of the current x position for drawing shapes.
x = 0


# Load default font.
font = ImageFont.load_default()

# Alternatively load a TTF font.  Make sure the .ttf font file is in the
# same directory as the python script!
# Some other nice fonts to try: http://www.dafont.com/bitmap.php
# font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 9)

# --- Page configuration ---
# Duration each page is displayed, in seconds.
PAGE_DURATION = 5

# --- Network tracking state ---
_prev_net_bytes = None
_prev_net_time = None


def _get_default_iface():
    """Return the name of the default network interface."""
    try:
        route = subprocess.check_output(
            "ip route | awk '/default/ {print $5; exit}'", shell=True
        ).decode("utf-8").strip()
        if route:
            return route
    except Exception:
        pass
    # Fallback: pick first non-lo interface.
    for path in sorted(glob.glob("/sys/class/net/*/statistics")):
        iface = path.split("/")[4]
        if iface != "lo":
            return iface
    return "eth0"


def _read_net_bytes(iface):
    """Read total rx + tx bytes for the given interface."""
    try:
        with open(f"/sys/class/net/{iface}/statistics/rx_bytes") as f:
            rx = int(f.read().strip())
        with open(f"/sys/class/net/{iface}/statistics/tx_bytes") as f:
            tx = int(f.read().strip())
        return rx + tx
    except Exception:
        return 0


def _format_bps(bps, show_unit=True):
    """Format a bits-per-second value with binary (IEC) prefixes."""
    if bps >= 1024 ** 3:
        val = f"{bps / 1024 ** 3:.1f}"
        unit = " Gibps"
    elif bps >= 1024 ** 2:
        val = f"{bps / 1024 ** 2:.1f}"
        unit = " Mibps"
    elif bps >= 1024:
        val = f"{bps / 1024:.1f}"
        unit = " Kibps"
    else:
        val = f"{int(bps)}"
        unit = " bps"
    return val + unit if show_unit else val


def _get_link_speed_bps(iface):
    """Read the negotiated link speed for the interface in bits per second."""
    try:
        with open(f"/sys/class/net/{iface}/speed") as f:
            speed_mbps = int(f.read().strip())
        if speed_mbps > 0:
            return speed_mbps * 1_000_000
    except Exception:
        pass
    # Fallback: assume 1 Gbps.
    return 1_000_000_000


_net_iface = _get_default_iface()
NET_MAX_BPS = _get_link_speed_bps(_net_iface)


def draw_bar(draw, x, y, width, height, label, value, actual, total, max_value=100):
    """Draw a horizontal bar chart with the label centered inside.

    The label text is inverted where it overlaps the filled portion of the bar
    so it remains readable regardless of the fill level.

    :param draw: PIL ImageDraw object.
    :param int x: Left edge x-coordinate.
    :param int y: Top edge y-coordinate.
    :param int width: Total width available for the bar.
    :param int height: Total height of the bar.
    :param str label: Short label displayed inside the bar (e.g. "CPU").
    :param float value: Current value of the metric (percentage).
    :param str actual: Actual value string (e.g. "3049").
    :param str total: Total/max value string (e.g. "40966").
    :param float max_value: Maximum value (default 100, i.e. percentage).
    """
    bar_width = width

    # Draw the outline of the bar (empty).
    draw.rectangle((x, y, x + bar_width - 1, y + height - 1), outline=255, fill=0)

    # Draw the filled portion proportional to value / max_value.
    fill_width = int(bar_width * min(value, max_value) / max_value)
    if fill_width > 0:
        draw.rectangle(
            (x, y, x + fill_width - 1, y + height - 1), outline=255, fill=255
        )

    # Compute centered label position.
    label_text = f"{label}: {int(value)}%, {actual}/{total}"
    text_w = draw.textlength(label_text, font=font)
    text_x = int(x + (bar_width - text_w) // 2)
    text_y = int(y + (height - 10) // 2)

    # Render label into a temporary image to get per-pixel control.
    tmp = Image.new("1", (bar_width, height), 0)
    tmp_draw = ImageDraw.Draw(tmp)
    tmp_draw.text((text_x - x, text_y - y), label_text, font=font, fill=255)

    # For each pixel in the temporary label image, XOR it onto the main image
    # so text appears white on the dark region and black on the filled region.
    from PIL import ImageChops
    bar_region = image.crop((x, y, x + bar_width, y + height))
    composited = ImageChops.logical_xor(bar_region, tmp)
    image.paste(composited, (x, y))


def get_stats():
    """Fetch current system stats and return a list of (label, value, actual, total) tuples."""
    global _prev_net_bytes, _prev_net_time

    cmd = "hostname"
    hostname = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    cmd = "hostname -I | cut -d' ' -f1"
    ip4_address = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    # Attempt to get the first global IPv6 address; fall back to empty string.
    try:
        cmd = "ip -6 addr show scope global | awk '/inet6/{print $2; exit}' | cut -d'/' -f1"
        ip6_address = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    except Exception:
        ip6_address = ""

    cmd = 'cut -f 1 -d " " /proc/loadavg'
    cpu_load = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    cpu_percent = min(float(cpu_load) * 100, 100)

    cmd = "nproc"
    cpu_cores = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    cmd = "free -m | awk 'NR==2{printf \"%s %s\", $3, $2}'"
    mem_parts = subprocess.check_output(cmd, shell=True).decode("utf-8").strip().split()
    mem_used = mem_parts[0]
    mem_total = mem_parts[1] + "MiB"
    mem_percent = float(mem_parts[0]) * 100 / float(mem_parts[1])

    cmd = "df -h | awk '$NF==\"/\"{printf \"%s %s %s\", $3, $2, $5}'"
    disk_parts = subprocess.check_output(cmd, shell=True).decode("utf-8").strip().split()
    disk_used = disk_parts[0]
    disk_total = disk_parts[1]
    disk_percent = float(disk_parts[2].rstrip("%"))

    # Network throughput.
    cur_bytes = _read_net_bytes(_net_iface)
    cur_time = time.monotonic()
    net_bps = 0.0
    if _prev_net_bytes is not None and _prev_net_time is not None:
        elapsed = cur_time - _prev_net_time
        if elapsed > 0:
            net_bps = (cur_bytes - _prev_net_bytes) * 8 / elapsed
    _prev_net_bytes = cur_bytes
    _prev_net_time = cur_time

    net_percent = min(net_bps / NET_MAX_BPS * 100, 100)
    net_actual = _format_bps(net_bps, show_unit=False)
    net_total = _format_bps(NET_MAX_BPS, show_unit=True)

    return hostname, ip4_address, ip6_address, [
        ("CPU", cpu_percent, cpu_load, cpu_cores),
        ("Mem", mem_percent, mem_used, mem_total),
        ("Disk", disk_percent, disk_used, disk_total),
        ("Net", net_percent, net_actual, net_total),
    ]


page_index = 0
last_page_time = time.monotonic()
header_index = 0

while True:
    now = time.monotonic()

    # Flip to the next page after PAGE_DURATION seconds.
    if now - last_page_time >= PAGE_DURATION:
        hostname, ip4_address, ip6_address, stats = get_stats()
        page_index = (page_index + 1) % len(stats)
        header_index = (header_index + 1) % 3
        last_page_time = now
    else:
        # On first iteration we still need data.
        if "stats" not in dir():
            hostname, ip4_address, ip6_address, stats = get_stats()

    label, value, actual, total = stats[page_index]

    # Clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Line 1: cycle through hostname, IPv4 address, and IPv6 address.
    headers = [hostname, ip4_address, ip6_address if ip6_address else "No IPv6"]
    header = headers[header_index]
    draw.text((x, top), header, font=font, fill=255)

    # Draw a large bar chart using the remaining vertical space for the single stat.
    bar_y = top + 14
    bar_height = height - bar_y - 1
    bar_max_width = min(width, disp.width) - x
    draw_bar(draw, x, bar_y, bar_max_width, bar_height, label, value, actual, total)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(0.1)

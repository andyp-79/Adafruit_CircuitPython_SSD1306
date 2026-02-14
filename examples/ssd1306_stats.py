# SPDX-FileCopyrightText: 2017 Tony DiCola for Adafruit Industries
# SPDX-FileCopyrightText: 2017 James DeVito for Adafruit Industries
# SPDX-License-Identifier: MIT

# This example is for use on (Linux) computers that are using CPython with
# Adafruit Blinka to support CircuitPython libraries. CircuitPython does
# not support PIL/pillow (python imaging library)!

import subprocess
import time

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
PAGE_DURATION = 2


def draw_bar(draw, x, y, width, height, label, value, max_value=100):
    """Draw a horizontal bar chart with the label centered inside.

    :param draw: PIL ImageDraw object.
    :param int x: Left edge x-coordinate.
    :param int y: Top edge y-coordinate.
    :param int width: Total width available for the bar.
    :param int height: Total height of the bar.
    :param str label: Short label displayed inside the bar (e.g. "CPU").
    :param float value: Current value of the metric.
    :param float max_value: Maximum value (default 100, i.e. percentage).
    """
    bar_width = width

    # Draw the outline of the bar.
    draw.rectangle((x, y, x + bar_width - 1, y + height - 1), outline=255, fill=0)

    # Draw the filled portion proportional to value / max_value.
    fill_width = int(bar_width * min(value, max_value) / max_value)
    if fill_width > 0:
        draw.rectangle(
            (x, y, x + fill_width - 1, y + height - 1), outline=255, fill=255
        )

    # Draw the label text centered inside the bar.
    label_text = f"{label}: {int(value)}%"
    text_w = draw.textlength(label_text, font=font)
    text_x = x + (bar_width - text_w) // 2
    text_y = y + (height - 10) // 2  # roughly center vertically (default font ~10px)
    # Invert fill so text is visible over both filled and empty regions.
    draw.text((text_x, text_y), label_text, font=font, fill=0 if fill_width > bar_width // 2 else 255)


def get_stats():
    """Fetch current system stats and return a list of (label, value) tuples."""
    cmd = "hostname"
    hostname = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    cmd = "hostname -I | cut -d' ' -f1"
    ip_address = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()

    cmd = 'cut -f 1 -d " " /proc/loadavg'
    cpu_load = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    cpu_percent = min(float(cpu_load) * 100, 100)

    cmd = "free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2 }'"
    mem_percent = float(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())

    cmd = "df -h | awk '$NF==\"/\"{printf \"%s\", $5}'"
    disk_percent = float(
        subprocess.check_output(cmd, shell=True).decode("utf-8").strip().rstrip("%")
    )

    return hostname, ip_address, [
        ("CPU", cpu_percent),
        ("Mem", mem_percent),
        ("Disk", disk_percent),
    ]


page_index = 0
last_page_time = time.monotonic()
show_hostname = True

while True:
    now = time.monotonic()

    # Flip to the next page after PAGE_DURATION seconds.
    if now - last_page_time >= PAGE_DURATION:
        hostname, ip_address, stats = get_stats()
        page_index = (page_index + 1) % len(stats)
        show_hostname = not show_hostname
        last_page_time = now
    else:
        # On first iteration we still need data.
        if "stats" not in dir():
            hostname, ip_address, stats = get_stats()

    label, value = stats[page_index]

    # Clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Line 1: alternate between hostname and IP address.
    header = hostname if show_hostname else ip_address
    draw.text((x, top), header, font=font, fill=255)

    # Draw a large bar chart using the remaining vertical space for the single stat.
    bar_y = top + 14
    bar_height = height - bar_y - 1
    bar_max_width = min(width, disp.width) - x
    draw_bar(draw, x, bar_y, bar_max_width, bar_height, label, value)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(0.1)

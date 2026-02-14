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


def draw_bar(draw, x, y, width, height, label, value, max_value=100):
    """Draw a horizontal bar chart showing usage of a metric.

    :param draw: PIL ImageDraw object.
    :param int x: Left edge x-coordinate.
    :param int y: Top edge y-coordinate.
    :param int width: Total width available for the label + bar.
    :param int height: Height of the bar (text is drawn within this height).
    :param str label: Short label displayed to the left of the bar (e.g. "CPU").
    :param float value: Current value of the metric.
    :param float max_value: Maximum value (default 100, i.e. percentage).
    """
    # Reserve space for the label text and a small gap.
    label_text = f"{label}:"
    label_width = draw.textlength(label_text, font=font)
    gap = 2
    bar_x = int(x + label_width + gap)
    bar_width = width - int(label_width + gap)

    # Draw the label.
    draw.text((x, y), label_text, font=font, fill=255)

    # Draw the outline of the bar.
    draw.rectangle((bar_x, y, bar_x + bar_width, y + height - 1), outline=255, fill=0)

    # Draw the filled portion proportional to value / max_value.
    fill_width = int(bar_width * min(value, max_value) / max_value)
    if fill_width > 0:
        draw.rectangle(
            (bar_x, y, bar_x + fill_width, y + height - 1), outline=255, fill=255
        )

    # Draw the percentage text centered inside the bar.
    pct_text = f"{int(value)}%"
    pct_w = draw.textlength(pct_text, font=font)
    text_x = bar_x + (bar_width - pct_w) // 2
    # Use inverted fill so the text is visible over both filled and empty regions.
    draw.text((text_x, y), pct_text, font=font, fill=0 if fill_width > bar_width // 2 else 255)


while True:
    # Draw a black filled box to clear the image.
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Shell scripts for system monitoring from here:
    # https://unix.stackexchange.com/questions/119126/command-to-display-memory-usage-disk-usage-and-cpu-load
    cmd = "hostname"
    IP = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    cmd = 'cut -f 1 -d " " /proc/loadavg'
    CPU = subprocess.check_output(cmd, shell=True).decode("utf-8").strip()
    cmd = "free -m | awk 'NR==2{printf \"%.2f\", $3*100/$2 }'"
    MemPercent = float(subprocess.check_output(cmd, shell=True).decode("utf-8").strip())
    cmd = "df -h | awk '$NF==\"/\"{printf \"%s\", $5}'"
    DiskPercent = float(
        subprocess.check_output(cmd, shell=True).decode("utf-8").strip().rstrip("%")
    )

    # Convert CPU load average to a rough percentage (assumes single-core max of 1.0).
    CPUPercent = min(float(CPU) * 100, 100)

    # Line 1: hostname as plain text.
    draw.text((x, top + 0), "Host: " + IP, font=font, fill=255)

    # Lines 2-4: horizontal bar charts for CPU, Memory, and Disk usage.
    bar_height = 8
    draw_bar(draw, x, top + 9, width, bar_height, "CPU", CPUPercent)
    draw_bar(draw, x, top + 18, width, bar_height, "Mem", MemPercent)
    draw_bar(draw, x, top + 27, width, bar_height, "Disk", DiskPercent)

    # Display image.
    disp.image(image)
    disp.show()
    time.sleep(0.1)

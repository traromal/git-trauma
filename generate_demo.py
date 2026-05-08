"""Generate a demo terminal screenshot showing git-trauma output."""

import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

REPO = r"C:\Users\ADMIN\Desktop\open"


def run(cmd):
    out = subprocess.check_output(cmd, cwd=REPO, shell=True, stderr=subprocess.STDOUT)
    return out.decode("utf-8", errors="replace")


# Get actual output
help_txt = run("git-trauma analyze --help")
output_txt = run("git-trauma analyze --no-llm")
stats_txt = run("git-trauma stats")

FONT_PATH = "C:/Windows/Fonts/Consola.ttf"
BG = (30, 30, 30)
TITLE_BG = (45, 45, 45)
TEXT_COL = (200, 200, 200)
GREEN = (80, 200, 120)
RED = (255, 100, 100)
CYAN = (80, 200, 255)
YELLOW = (255, 220, 100)
MAGENTA = (255, 100, 200)
DIM = (140, 140, 140)

font = ImageFont.truetype(FONT_PATH, 18)
bold = ImageFont.truetype(FONT_PATH, 18)
title_font = ImageFont.truetype(FONT_PATH, 14)

sections = [
    ("git-trauma analyze --help (truncated)", help_txt[:1200], TEXT_COL),
    ("git-trauma analyze --no-llm", output_txt[:2000], TEXT_COL),
    ("git-trauma stats", stats_txt[:800], TEXT_COL),
]

line_h = 22
pad = 16
char_w = 11
width = 920

total_h = pad
panels = []
for title, txt, _ in sections:
    lines = txt.split("\n")
    h = 36 + len(lines) * line_h + pad
    panels.append((title, txt, lines, h))
    total_h += h

img = Image.new("RGB", (width, total_h), BG)
draw = ImageDraw.Draw(img)

y = pad
for title, txt, lines, h in panels:
    draw.rectangle([(0, y), (width, y + 36)], fill=TITLE_BG)
    draw.text((pad, y + 8), title, font=title_font, fill=CYAN)
    draw.rectangle([(0, y + 36), (width, y + h)], fill=(22, 22, 22))
    x = pad + 6
    yy = y + 36 + 6
    for line in lines:
        col = TEXT_COL
        if line.strip().startswith("["):
            if "red" in line:
                col = RED
            elif "green" in line:
                col = GREEN
            elif "cyan" in line:
                col = CYAN
            elif "yellow" in line:
                col = YELLOW
            elif "magenta" in line:
                col = MAGENTA
            elif "dim" in line:
                col = DIM
        elif "crisis" in line.lower():
            col = RED
        elif "flow" in line.lower() or "pride" in line.lower():
            col = GREEN
        elif "panic" in line.lower():
            col = YELLOW
        elif "despair" in line.lower():
            col = MAGENTA
        draw.text((x, yy), line, font=font, fill=col)
        yy += line_h
    y += h

img.save("assets/demo.png")
print("Saved assets/demo.png")

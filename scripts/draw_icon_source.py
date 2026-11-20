"""画「日期」原始图标 icons/icon-source.png（1024×1024），和「此刻」「灵感」同一风格。
需要 Noto Serif CJK 字体；换图标时直接替换 icon-source.png 再跑 make_icons.py 即可。"""
from PIL import Image, ImageDraw, ImageFont
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT = sys.argv[1] if len(sys.argv) > 1 else "/usr/share/fonts/opentype/noto/NotoSerifCJK-Black.ttc"
S = 1024


def sc_font(size):
    for i in range(10):
        try:
            f = ImageFont.truetype(FONT, size, index=i)
        except OSError:
            break
        if "SC" in " ".join(f.getname()):
            return f
    return ImageFont.truetype(FONT, size)


img = Image.new("RGB", (S, S))
d = ImageDraw.Draw(img)
top, bot = (52, 200, 140), (14, 150, 98)          # 绿色：坚持、打卡
for y in range(S):
    t = y / S
    d.line([(0, y), (S, y)], fill=tuple(int(top[i] + (bot[i] - top[i]) * t) for i in range(3)))

f = sc_font(330)
text = "日期"
bb = d.textbbox((0, 0), text, font=f)
w, h = bb[2] - bb[0], bb[3] - bb[1]
x, y = (S - w) / 2 - bb[0], (S - h) / 2 - bb[1] + 30
d.text((x, y), text, font=f, fill=(255, 255, 255))
# 右上角一个对勾：今天打过卡了
cx, cy = (S + w) / 2 + 22, (S - h) / 2 - 34
pts = [(cx - 54, cy + 2), (cx - 18, cy + 38), (cx + 52, cy - 40)]
d.line(pts, fill=(255, 255, 255), width=26, joint="curve")
for p in (pts[0], pts[2]):
    d.ellipse([p[0] - 13, p[1] - 13, p[0] + 13, p[1] + 13], fill=(255, 255, 255))
img.save(os.path.join(ROOT, "icons", "icon-source.png"))
print("saved", w, h)

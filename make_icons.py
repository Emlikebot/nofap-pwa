"""用 icons/icon-source.png（红底签名）生成全部图标：python3 make_icons.py
PWA 图标写到 icons/，安卓资源写到 android-res/（CI 会覆盖到安卓工程里）。"""
from PIL import Image, ImageDraw
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = Image.open(os.path.join(ROOT, "icons", "icon-source.png")).convert("RGB")
RED = SRC.getpixel((40, 40))           # 背景红
DARK = (15, 17, 21)                    # App 主题深色


def signature():
    """从原图抠出签名笔画（透明背景），裁到笔画范围。"""
    w, h = SRC.size
    a = Image.new("L", (w, h))
    pa, ps = a.load(), SRC.load()
    for y in range(h):
        for x in range(w):
            r = ps[x, y][0]
            pa[x, y] = max(0, min(255, int((RED[0] - r) * 255 / (RED[0] - 15))))
    lay = Image.new("RGBA", (w, h), (10, 6, 6, 0))
    lay.putalpha(a)
    return lay.crop(lay.getbbox())


SIG = signature()


def on_red(size, width_ratio, bg=RED, alpha=255):
    """红底（或透明底）+ 居中签名，签名宽度占 width_ratio。"""
    S = size * 2
    c = Image.new("RGBA", (S, S), bg + (alpha,))
    w = int(S * width_ratio)
    s = SIG.resize((w, int(w * SIG.height / SIG.width)), Image.LANCZOS)
    c.alpha_composite(s, ((S - s.width) // 2, (S - s.height) // 2))
    return c.resize((size, size), Image.LANCZOS)


def full(size):
    return on_red(size, 0.84)


def masked(img, kind):
    S = img.width * 4
    m = Image.new("L", (S, S), 0)
    d = ImageDraw.Draw(m)
    if kind == "round":
        d.ellipse([0, 0, S, S], fill=255)
    else:
        d.rounded_rectangle([0, 0, S, S], radius=int(S * 0.2), fill=255)
    m = m.resize(img.size, Image.LANCZOS)
    out = Image.new("RGBA", img.size, (0, 0, 0, 0))
    out.paste(img, (0, 0), m)
    return out


# ---------- PWA / iPhone ----------
icons = os.path.join(ROOT, "icons")
full(180).convert("RGB").save(os.path.join(icons, "apple-touch-icon.png"))
full(192).convert("RGB").save(os.path.join(icons, "icon-192.png"))
full(512).convert("RGB").save(os.path.join(icons, "icon-512.png"))
on_red(512, 0.70).convert("RGB").save(os.path.join(icons, "icon-512-maskable.png"))   # 安全区 80% 圆内

# ---------- 安卓 ----------
OUT = os.path.join(ROOT, "android-res")
dens = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
for name, k in dens.items():
    d = os.path.join(OUT, f"mipmap-{name}")
    os.makedirs(d, exist_ok=True)
    masked(full(int(48 * k)), "rr").save(os.path.join(d, "ic_launcher.png"))
    masked(full(int(48 * k)), "round").save(os.path.join(d, "ic_launcher_round.png"))
    # 自适应图标前景：108dp 画布，签名放在中间 66dp 安全区内
    on_red(int(108 * k), 0.56, alpha=0).save(os.path.join(d, "ic_launcher_foreground.png"))
    for o, (w, h) in {"port": (320, 480), "land": (480, 320)}.items():
        dd = os.path.join(OUT, f"drawable-{o}-{name}")
        os.makedirs(dd, exist_ok=True)
        W, H = int(w * k), int(h * k)
        sp = Image.new("RGB", (W, H), DARK)
        s = int(min(W, H) * 0.34)
        ic = masked(full(s), "rr")
        sp.paste(ic, ((W - s) // 2, (H - s) // 2), ic)
        sp.save(os.path.join(dd, "splash.png"), optimize=True)
os.makedirs(os.path.join(OUT, "drawable"), exist_ok=True)
sp = Image.new("RGB", (480, 800), DARK)
ic = masked(full(160), "rr"); sp.paste(ic, (160, 320), ic)
sp.save(os.path.join(OUT, "drawable", "splash.png"), optimize=True)
os.makedirs(os.path.join(OUT, "values"), exist_ok=True)
with open(os.path.join(OUT, "values", "ic_launcher_background.xml"), "w") as f:
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#%02X%02X%02X</color>\n</resources>\n' % RED)
print("icons written; background", RED)

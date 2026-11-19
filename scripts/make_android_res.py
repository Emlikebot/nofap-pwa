"""生成安卓图标 / 启动图资源到 android-res/（CI 会覆盖到 android/app/src/main/res）：python3 scripts/make_android_res.py"""
from PIL import Image, ImageDraw
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "android-res")
BG = (15, 17, 21)


def draw_mark(d, S, inset):
    w = (S - 2 * inset) * 0.117
    box = [inset, inset, S - inset, S - inset]
    d.arc(box, 0, 360, fill=(40, 46, 58, 255), width=int(w))
    d.arc(box, -90, 200, fill=(52, 211, 153, 255), width=int(w))
    cx, cy, r = S / 2, S / 2, (S - 2 * inset) / 2
    pts = [(cx - r * 0.42, cy + r * 0.02), (cx - r * 0.1, cy + r * 0.34), (cx + r * 0.45, cy - r * 0.3)]
    d.line(pts, fill=(238, 240, 244, 255), width=int(w * 1.05), joint="curve")
    for p in (pts[0], pts[2]):
        rr = w * 0.52
        d.ellipse([p[0] - rr, p[1] - rr, p[0] + rr, p[1] + rr], fill=(238, 240, 244, 255))


def gradient(S):
    img = Image.new("RGBA", (S, S), BG + (255,))
    d = ImageDraw.Draw(img)
    for y in range(S):
        t = y / S
        d.line([(0, y), (S, y)], fill=(int(16 + 10 * t), int(22 + 8 * t), int(28 + 6 * t), 255))
    return img


def legacy(size, round_=False):
    S = size * 4
    img = gradient(S)
    draw_mark(ImageDraw.Draw(img), S, S * 0.18)
    mask = Image.new("L", (S, S), 0)
    md = ImageDraw.Draw(mask)
    if round_:
        md.ellipse([0, 0, S, S], fill=255)
    else:
        md.rounded_rectangle([0, 0, S, S], radius=S * 0.18, fill=255)
    out = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out.resize((size, size), Image.LANCZOS)


def foreground(size):
    # 自适应图标：108dp 画布，安全区为中间 66dp
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw_mark(ImageDraw.Draw(img), S, S * 0.30)
    return img.resize((size, size), Image.LANCZOS)


def splash(w, h):
    img = Image.new("RGB", (w, h), BG)
    s = int(min(w, h) * 0.32)
    mark = legacy(s)
    img.paste(mark, ((w - s) // 2, (h - s) // 2), mark)
    return img


dens = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
for name, k in dens.items():
    d = os.path.join(OUT, f"mipmap-{name}")
    os.makedirs(d, exist_ok=True)
    legacy(int(48 * k)).save(os.path.join(d, "ic_launcher.png"))
    legacy(int(48 * k), True).save(os.path.join(d, "ic_launcher_round.png"))
    foreground(int(108 * k)).save(os.path.join(d, "ic_launcher_foreground.png"))
    for o, (w, h) in {"port": (320, 480), "land": (480, 320)}.items():
        dd = os.path.join(OUT, f"drawable-{o}-{name}")
        os.makedirs(dd, exist_ok=True)
        splash(int(w * k), int(h * k)).save(os.path.join(dd, "splash.png"), optimize=True)
os.makedirs(os.path.join(OUT, "drawable"), exist_ok=True)
splash(480, 800).save(os.path.join(OUT, "drawable", "splash.png"), optimize=True)

os.makedirs(os.path.join(OUT, "values"), exist_ok=True)
open(os.path.join(OUT, "values", "ic_launcher_background.xml"), "w").write(
    '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#12171D</color>\n</resources>\n')
open(os.path.join(OUT, "values", "styles.xml"), "w").write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="Theme.AppCompat.DayNight.DarkActionBar">
        <item name="colorPrimary">#0F1115</item>
        <item name="colorPrimaryDark">#0F1115</item>
        <item name="colorAccent">#34D399</item>
    </style>
    <style name="AppTheme.NoActionBar" parent="Theme.AppCompat.DayNight.NoActionBar">
        <item name="windowActionBar">false</item>
        <item name="windowNoTitle">true</item>
        <item name="android:background">@null</item>
        <item name="android:windowBackground">#0F1115</item>
    </style>
    <style name="AppTheme.NoActionBarLaunch" parent="Theme.SplashScreen">
        <item name="android:background">@drawable/splash</item>
        <item name="windowSplashScreenBackground">#0F1115</item>
        <item name="postSplashScreenTheme">@style/AppTheme.NoActionBar</item>
    </style>
</resources>
''')
print("android res written to", OUT)

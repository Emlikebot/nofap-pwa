"""用 icons/icon-source.png 生成全部图标：python3 make_icons.py
PWA / iPhone 图标写到 icons/，安卓图标和启动图写到 android-res/（CI 会覆盖到安卓工程里）。"""
from PIL import Image, ImageDraw
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = Image.open(os.path.join(ROOT, "icons", "icon-source.png")).convert("RGB")
BG = SRC.getpixel((SRC.width // 2, SRC.height - 4))   # 安卓自适应图标背景色
DARK = (15, 17, 21)


def full(size):
    return SRC.resize((size, size), Image.LANCZOS).convert("RGBA")


def white_layer():
    """抠出白色的字和对勾（透明背景），给安卓自适应图标当前景。"""
    px = SRC.load(); a = Image.new("L", SRC.size); pa = a.load()
    for y in range(SRC.height):
        for x in range(SRC.width):
            m = min(px[x, y])                       # 白字三个通道都高，绿底的红通道很低
            pa[x, y] = max(0, min(255, int((m - 60) * 255 / 180)))
    lay = Image.new("RGBA", SRC.size, (255, 255, 255, 0))
    lay.putalpha(a)
    return lay


WHITE = white_layer()


def foreground(size, scale=0.74):
    S = size * 2
    c = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    w = int(S * scale)
    c.alpha_composite(WHITE.resize((w, w), Image.LANCZOS), ((S - w) // 2, (S - w) // 2))
    return c.resize((size, size), Image.LANCZOS)


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


icons = os.path.join(ROOT, "icons")
full(180).convert("RGB").save(os.path.join(icons, "apple-touch-icon.png"))
full(192).convert("RGB").save(os.path.join(icons, "icon-192.png"))
full(512).convert("RGB").save(os.path.join(icons, "icon-512.png"))
full(512).convert("RGB").save(os.path.join(icons, "icon-512-maskable.png"))   # 字都在中间 80% 圆内
masked(full(64), "rr").save(os.path.join(icons, "favicon.png"))

OUT = os.path.join(ROOT, "android-res")
dens = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}
for name, k in dens.items():
    d = os.path.join(OUT, f"mipmap-{name}")
    os.makedirs(d, exist_ok=True)
    masked(full(int(48 * k)), "rr").save(os.path.join(d, "ic_launcher.png"))
    masked(full(int(48 * k)), "round").save(os.path.join(d, "ic_launcher_round.png"))
    foreground(int(108 * k)).save(os.path.join(d, "ic_launcher_foreground.png"))
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
    f.write('<?xml version="1.0" encoding="utf-8"?>\n<resources>\n    <color name="ic_launcher_background">#%02X%02X%02X</color>\n</resources>\n' % BG)
with open(os.path.join(OUT, "values", "styles.xml"), "w") as f:
    f.write('''<?xml version="1.0" encoding="utf-8"?>
<resources>
    <style name="AppTheme" parent="Theme.AppCompat.DayNight.DarkActionBar">
        <item name="colorPrimary">#0F1115</item>
        <item name="colorPrimaryDark">#0F1115</item>
        <item name="colorAccent">#FF6A55</item>
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
print("icons written; adaptive background", BG)

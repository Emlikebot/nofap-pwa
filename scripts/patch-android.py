"""CI 用：给安卓工程加上「提醒事项」的原生部分（定时通知、闹钟式全屏响铃、开机恢复），并换上自己的 MainActivity。
用法：npx cap add android 之后运行 python3 scripts/patch-android.py"""
import os, re, shutil, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP = os.path.join(ROOT, "android", "app", "src", "main")
M = os.path.join(APP, "AndroidManifest.xml")
xml = open(M, encoding="utf-8").read()

PERMS = [
    '<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />',
    '<uses-permission android:name="android.permission.SCHEDULE_EXACT_ALARM" android:maxSdkVersion="32" />',
    '<uses-permission android:name="android.permission.USE_EXACT_ALARM" />',
    '<uses-permission android:name="android.permission.USE_FULL_SCREEN_INTENT" />',
    '<uses-permission android:name="android.permission.RECEIVE_BOOT_COMPLETED" />',
    '<uses-permission android:name="android.permission.VIBRATE" />',
    '<uses-permission android:name="android.permission.WAKE_LOCK" />',
]
COMPONENTS = """
        <receiver android:name=".ReminderReceiver" android:exported="false" />
        <receiver android:name=".BootReceiver" android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.BOOT_COMPLETED" />
                <action android:name="android.intent.action.MY_PACKAGE_REPLACED" />
                <action android:name="android.intent.action.TIME_SET" />
                <action android:name="android.intent.action.TIMEZONE_CHANGED" />
            </intent-filter>
        </receiver>
        <activity
            android:name=".AlarmActivity"
            android:exported="false"
            android:excludeFromRecents="true"
            android:launchMode="singleInstance"
            android:taskAffinity=""
            android:showWhenLocked="true"
            android:turnScreenOn="true"
            android:theme="@android:style/Theme.DeviceDefault.NoActionBar" />
"""

if "ReminderReceiver" not in xml:
    add = "".join("    " + p + "\n" for p in PERMS if p.split('"')[1] not in xml)
    if "<application" not in xml:
        sys.exit("找不到 <application>：\n" + xml)
    xml = xml.replace("<application", add + "\n    <application", 1)
    if "</application>" not in xml:
        sys.exit("找不到 </application>")
    xml = xml.replace("</application>", COMPONENTS + "    </application>", 1)
open(M, "w", encoding="utf-8").write(xml)

java = os.path.join(APP, "java", "com", "emlikebot", "zilv")
os.makedirs(java, exist_ok=True)
for f in os.listdir(os.path.join(ROOT, "android-native")):
    if f.endswith(".java"):
        shutil.copy(os.path.join(ROOT, "android-native", f), os.path.join(java, f))
print(xml)
print("patched:", sorted(os.listdir(java)))

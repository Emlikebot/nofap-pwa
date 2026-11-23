package com.emlikebot.zilv;

import android.annotation.SuppressLint;
import android.app.AlarmManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import java.util.HashSet;
import java.util.Iterator;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/** 提醒的定时、通知和“稍后提醒”。数据存在 SharedPreferences，开机后据此重新定时。 */
final class ReminderStore {
    static final String ACTION_FIRE = "com.emlikebot.zilv.REMIND";
    static final String ACTION_SNOOZE = "com.emlikebot.zilv.SNOOZE";
    static final String ACTION_DISMISS = "com.emlikebot.zilv.DISMISS";
    static final String CH_REMIND = "reminders";
    static final String CH_ALARM = "alarms_v1";
    static final int SNOOZE_MIN = 10;
    private static final String PREF = "zilv_reminders";
    private static final String K_ITEMS = "items";
    private static final String K_SNOOZE = "snooze";

    private ReminderStore() {}

    private static SharedPreferences prefs(Context c) {
        return c.getSharedPreferences(PREF, Context.MODE_PRIVATE);
    }

    static boolean canExact(Context c) {
        if (Build.VERSION.SDK_INT < 31) return true;
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        return am != null && am.canScheduleExactAlarms();
    }

    /** 用网页端给的整表替换现有定时。表里没有的（已完成 / 已删除）取消掉，包括已经弹出的通知。 */
    static synchronized void replaceAll(Context c, String json) throws JSONException {
        SharedPreferences p = prefs(c);
        JSONArray old = new JSONArray(p.getString(K_ITEMS, "[]"));
        JSONObject snooze = new JSONObject(p.getString(K_SNOOZE, "{}"));
        JSONArray items = new JSONArray(json);
        long now = System.currentTimeMillis();
        NotificationManagerCompat nm = NotificationManagerCompat.from(c);

        Set<Integer> keep = new HashSet<>();
        for (int i = 0; i < items.length(); i++) keep.add(items.getJSONObject(i).getInt("nid"));
        for (int i = 0; i < old.length(); i++) {
            int nid = old.getJSONObject(i).getInt("nid");
            cancelAlarm(c, nid);
            if (!keep.contains(nid)) { nm.cancel(nid); snooze.remove(String.valueOf(nid)); }
        }
        for (Iterator<String> it = snooze.keys(); it.hasNext(); ) {
            if (!keep.contains(Integer.parseInt(it.next()))) it.remove();
        }

        for (int i = 0; i < items.length(); i++) {
            JSONObject o = items.getJSONObject(i);
            int nid = o.getInt("nid");
            long at = o.getLong("at");
            long fireAt;
            if (at > now) {
                fireAt = at;
                snooze.remove(String.valueOf(nid));
                nm.cancel(nid);                       // 时间改到以后了：收起已弹出的旧通知
            } else {
                long s = snooze.optLong(String.valueOf(nid), 0);
                if (s <= now) continue;               // 已经提醒过、也没有稍后提醒
                fireAt = s;
            }
            schedule(c, nid, fireAt, o.optBoolean("alarm", false));
        }
        p.edit().putString(K_ITEMS, items.toString()).putString(K_SNOOZE, snooze.toString()).apply();
    }

    /** 开机、更新 App、改时间后重新定时。 */
    static void rescheduleAll(Context c) {
        try {
            replaceAll(c, prefs(c).getString(K_ITEMS, "[]"));
        } catch (JSONException ignored) {}
    }

    static JSONObject find(Context c, int nid) {
        try {
            JSONArray a = new JSONArray(prefs(c).getString(K_ITEMS, "[]"));
            for (int i = 0; i < a.length(); i++) if (a.getJSONObject(i).getInt("nid") == nid) return a.getJSONObject(i);
        } catch (JSONException ignored) {}
        return null;
    }

    static synchronized void snooze(Context c, int nid) {
        NotificationManagerCompat.from(c).cancel(nid);
        JSONObject o = find(c, nid);
        if (o == null) return;
        long at = System.currentTimeMillis() + SNOOZE_MIN * 60000L;
        try {
            JSONObject s = new JSONObject(prefs(c).getString(K_SNOOZE, "{}"));
            s.put(String.valueOf(nid), at);
            prefs(c).edit().putString(K_SNOOZE, s.toString()).apply();
        } catch (JSONException ignored) {}
        schedule(c, nid, at, o.optBoolean("alarm", false));
    }

    static synchronized void dismiss(Context c, int nid) {
        NotificationManagerCompat.from(c).cancel(nid);
        try {
            JSONObject s = new JSONObject(prefs(c).getString(K_SNOOZE, "{}"));
            s.remove(String.valueOf(nid));
            prefs(c).edit().putString(K_SNOOZE, s.toString()).apply();
        } catch (JSONException ignored) {}
    }

    private static Intent fireIntent(Context c, int nid) {
        Intent i = new Intent(c, ReminderReceiver.class);
        i.setAction(ACTION_FIRE);
        i.setData(Uri.parse("zilv://reminder/" + nid));
        i.putExtra("nid", nid);
        return i;
    }

    private static void schedule(Context c, int nid, long at, boolean alarm) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        if (am == null) return;
        PendingIntent pi = PendingIntent.getBroadcast(c, nid, fireIntent(c, nid),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        try {
            if (alarm) {
                PendingIntent show = PendingIntent.getActivity(c, nid, launchIntent(c),
                    PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
                am.setAlarmClock(new AlarmManager.AlarmClockInfo(at, show), pi);
            } else if (canExact(c)) {
                am.setExactAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi);
            } else {
                am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi);
            }
        } catch (SecurityException e) {
            am.setAndAllowWhileIdle(AlarmManager.RTC_WAKEUP, at, pi);
        }
    }

    private static void cancelAlarm(Context c, int nid) {
        AlarmManager am = (AlarmManager) c.getSystemService(Context.ALARM_SERVICE);
        PendingIntent pi = PendingIntent.getBroadcast(c, nid, fireIntent(c, nid),
            PendingIntent.FLAG_NO_CREATE | PendingIntent.FLAG_IMMUTABLE);
        if (am != null && pi != null) { am.cancel(pi); pi.cancel(); }
    }

    static Intent launchIntent(Context c) {
        Intent i = c.getPackageManager().getLaunchIntentForPackage(c.getPackageName());
        if (i == null) i = new Intent(c, MainActivity.class);
        i.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return i;
    }

    private static PendingIntent actionIntent(Context c, String action, int nid) {
        Intent i = new Intent(c, ReminderReceiver.class);
        i.setAction(action);
        i.setData(Uri.parse("zilv://" + action + "/" + nid));
        i.putExtra("nid", nid);
        return PendingIntent.getBroadcast(c, nid, i, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
    }

    static void ensureChannels(Context c) {
        if (Build.VERSION.SDK_INT < 26) return;
        NotificationManager nm = (NotificationManager) c.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm == null) return;
        if (nm.getNotificationChannel(CH_REMIND) == null) {
            NotificationChannel ch = new NotificationChannel(CH_REMIND, "提醒事项", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("到点提醒");
            ch.enableVibration(true);
            ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm.createNotificationChannel(ch);
        }
        if (nm.getNotificationChannel(CH_ALARM) == null) {
            NotificationChannel ch = new NotificationChannel(CH_ALARM, "闹钟式提醒", NotificationManager.IMPORTANCE_HIGH);
            ch.setDescription("全屏弹出并持续响铃");
            Uri sound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_ALARM);
            if (sound == null) sound = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
            ch.setSound(sound, new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_ALARM)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build());
            ch.enableVibration(true);
            ch.setVibrationPattern(new long[] { 0, 800, 600, 800, 600, 800 });
            ch.setBypassDnd(true);
            ch.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
            nm.createNotificationChannel(ch);
        }
    }

    /** 到点：弹通知。闹钟式的带全屏界面，铃声一直响到关掉。 */
    @SuppressLint("MissingPermission")
    static void show(Context c, int nid) {
        JSONObject o = find(c, nid);
        if (o == null) return;
        ensureChannels(c);
        boolean alarm = o.optBoolean("alarm", false);
        String title = o.optString("title", "提醒");
        String body = o.optString("body", "");

        // 已经弹过的不再重复：用一次性的 snooze 记录区分
        try {
            JSONObject s = new JSONObject(prefs(c).getString(K_SNOOZE, "{}"));
            if (s.has(String.valueOf(nid))) { s.remove(String.valueOf(nid)); prefs(c).edit().putString(K_SNOOZE, s.toString()).apply(); }
        } catch (JSONException ignored) {}

        PendingIntent content = PendingIntent.getActivity(c, nid, launchIntent(c),
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        NotificationCompat.Builder b = new NotificationCompat.Builder(c, alarm ? CH_ALARM : CH_REMIND)
            .setSmallIcon(alarm ? android.R.drawable.ic_lock_idle_alarm : android.R.drawable.ic_popup_reminder)
            .setContentTitle(title)
            .setContentText(body)
            .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(alarm ? NotificationCompat.CATEGORY_ALARM : NotificationCompat.CATEGORY_REMINDER)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setContentIntent(content)
            .setAutoCancel(!alarm)
            .setOngoing(alarm)
            .setShowWhen(true)
            .addAction(0, "稍后 " + SNOOZE_MIN + " 分钟", actionIntent(c, ACTION_SNOOZE, nid))
            .addAction(0, alarm ? "关闭" : "知道了", actionIntent(c, ACTION_DISMISS, nid));
        if (alarm) {
            Intent full = new Intent(c, AlarmActivity.class);
            full.setData(Uri.parse("zilv://alarm/" + nid));
            full.putExtra("nid", nid);
            full.putExtra("title", title);
            full.putExtra("body", body);
            full.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_NO_USER_ACTION);
            b.setFullScreenIntent(PendingIntent.getActivity(c, nid, full,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE), true);
        }
        Notification n = b.build();
        if (alarm) n.flags |= Notification.FLAG_INSISTENT;   // 铃声循环，直到通知被关掉
        try {
            NotificationManagerCompat.from(c).notify(nid, n);
        } catch (SecurityException ignored) {}
    }
}

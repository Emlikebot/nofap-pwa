package com.emlikebot.zilv;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** 系统闹钟到点、通知上的「稍后 / 关闭」按钮都走这里。 */
public class ReminderReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        String a = intent.getAction();
        int nid = intent.getIntExtra("nid", 0);
        if (nid == 0 || a == null) return;
        if (ReminderStore.ACTION_FIRE.equals(a)) ReminderStore.show(c, nid);
        else if (ReminderStore.ACTION_SNOOZE.equals(a)) ReminderStore.snooze(c, nid);
        else if (ReminderStore.ACTION_DISMISS.equals(a)) ReminderStore.dismiss(c, nid);
    }
}

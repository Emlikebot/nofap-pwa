package com.emlikebot.zilv;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/** 开机、App 更新、改系统时间后，系统闹钟会被清掉，这里重新定时。 */
public class BootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context c, Intent intent) {
        ReminderStore.rescheduleAll(c);
    }
}

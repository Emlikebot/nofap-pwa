package com.emlikebot.zilv;

import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(RemindersPlugin.class);   // 提醒事项：定时通知 / 闹钟式响铃
        super.onCreate(savedInstanceState);
    }
}

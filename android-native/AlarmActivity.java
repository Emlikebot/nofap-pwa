package com.emlikebot.zilv;

import android.app.Activity;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** 闹钟式提醒的全屏界面：锁屏时也会亮屏弹出。铃声由通知负责，关掉通知就停。 */
public class AlarmActivity extends Activity {
    private int nid;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        if (Build.VERSION.SDK_INT >= 27) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        } else {
            getWindow().addFlags(WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON);
        }
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        render(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        render(intent);
    }

    private int dp(int v) { return Math.round(v * getResources().getDisplayMetrics().density); }

    private Button button(String text, int bg, int fg) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(18);
        b.setTextColor(fg);
        b.setAllCaps(false);
        GradientDrawable d = new GradientDrawable();
        d.setColor(bg);
        d.setCornerRadius(dp(16));
        b.setBackground(d);
        LinearLayout.LayoutParams lp = new LinearLayout.LayoutParams(LinearLayout.LayoutParams.MATCH_PARENT, dp(58));
        lp.topMargin = dp(12);
        b.setLayoutParams(lp);
        return b;
    }

    private void render(Intent in) {
        nid = in.getIntExtra("nid", 0);
        String title = in.getStringExtra("title");
        String body = in.getStringExtra("body");

        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER);
        root.setBackgroundColor(Color.parseColor("#0F1115"));
        root.setPadding(dp(28), dp(48), dp(28), dp(48));

        TextView icon = new TextView(this);
        icon.setText("⏰");
        icon.setTextSize(56);
        icon.setGravity(Gravity.CENTER);
        root.addView(icon);

        TextView time = new TextView(this);
        time.setText(new SimpleDateFormat("HH:mm", Locale.getDefault()).format(new Date()));
        time.setTextSize(64);
        time.setTypeface(Typeface.DEFAULT_BOLD);
        time.setTextColor(Color.WHITE);
        time.setGravity(Gravity.CENTER);
        root.addView(time);

        TextView t = new TextView(this);
        t.setText(title == null ? "提醒" : title);
        t.setTextSize(26);
        t.setTextColor(Color.WHITE);
        t.setGravity(Gravity.CENTER);
        t.setPadding(0, dp(18), 0, dp(6));
        root.addView(t);

        if (body != null && !body.isEmpty()) {
            TextView b = new TextView(this);
            b.setText(body);
            b.setTextSize(16);
            b.setTextColor(Color.parseColor("#9AA1AD"));
            b.setGravity(Gravity.CENTER);
            root.addView(b);
        }

        View gap = new View(this);
        root.addView(gap, new LinearLayout.LayoutParams(1, dp(48)));

        Button snooze = button("稍后 " + ReminderStore.SNOOZE_MIN + " 分钟", Color.parseColor("#20242D"), Color.WHITE);
        snooze.setOnClickListener(v -> { ReminderStore.snooze(this, nid); finish(); });
        root.addView(snooze);

        Button stop = button("关闭", Color.parseColor("#34D399"), Color.parseColor("#062B1F"));
        stop.setOnClickListener(v -> { ReminderStore.dismiss(this, nid); finish(); });
        root.addView(stop);

        setContentView(root);
    }
}

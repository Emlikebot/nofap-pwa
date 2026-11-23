# 日期（原「SUC」「自律打卡」）

一套代码，两个平台：
- **iPhone**：PWA（网页应用），Safari 打开 GitHub Pages 网址 → 添加到主屏幕
- **安卓**：Capacitor 打包的 APK，GitHub Actions 自动编译，下载地址（始终最新）：
  https://github.com/Emlikebot/nofap-pwa/releases/latest/download/zilv.apk

登录账号后离线可用、联网自动同步，数据存在管理员的 Google Drive（见下）。

## 功能
- **🛡️ 戒除 · 警示**：固本培元、戒扣痘痘、戒挖鼻孔、戒咬指甲、戒烟、戒熬夜或自定义。实时计时（天 / 时:分:秒）、里程碑进度环、每日打卡（心情 + 日记）、打卡日历、12 枚勋章、破戒记录与诱因统计；近 7 天有破戒时首页和详情页会出现红色警示。每个项目有自己的理由、诱因和急救清单（可编辑）。
- **💕 纪念日**：如“和女友在一起第 N 天”。显示年/月/天、周数、距下一个周年天数，以及即将到来的 100 天整数、520、1314、周年等节点。可选起始日算第 1 天或第 0 天。
- **💭 碎碎念**：随手记一句，可选心情表情、关联某个项目；按天分组的时间线、搜索、编辑 / 复制 / 删除；“那年今日”回顾一个月前、一年前的今天；草稿自动保存；项目详情页显示相关碎碎念。
- **⏰ 提醒事项**：待办列表，可设提醒时间和重复（每天 / 工作日 / 每周 / 每月 / 每年），完成后打勾；重复的提醒打勾后自动排到下一次。到点时 iPhone 和电脑在打开 App 时弹出（电脑浏览器会发系统通知），安卓 App 关着也会提醒：普通提醒弹系统通知，开了「闹钟式响铃」的锁屏全屏弹出并持续响铃，可「稍后 10 分钟」或关闭
- **⏳ 倒计时**：如“距离元旦还有 N 天”。支持每年重复（生日、节日过了自动算下一年），显示进度条。

## 页面
- **首页**：所有项目卡片（置顶 / 戒除 / 纪念日 / 倒计时分组），戒除项目可直接点“今日打卡”；右上角 ＋ 新建
- **碎碎念**：见上
- **急救**：方块呼吸、立刻做一件事、我的理由；多个戒除项目时可切换
- **我的**：统计、导出 / 导入 JSON 备份、清空数据

## 账号与同步
- 需要登录；注册要管理员给的**一次性邀请码**。登录后离线也能用，联网自动双向同步，同一账号的多台设备数据互通
- 服务器是管理员 Google 账号下的 **Apps Script 网页应用**（代码 `google-drive/Code.gs`），免费、无需自建服务器
  - 账号、加盐哈希后的密码、邀请码存在脚本属性里
  - 每个账号的数据存在管理员 Google Drive「自律打卡云端/用户名/」：`data.json` + 每日快照（保留 30 天）
- 冲突处理：每个项目 / 碎碎念记录修改时间，按条目合并，同一条以较晚的修改为准；打卡、破戒记录取并集；删除会同步
- 搭建：App 登录页「服务器设置 → 管理员：怎么搭建服务器？」有步骤和一键复制代码。用脚本里的 `SETUP_CODE` 注册的第一个账号是管理员
- 部署好后把网址填进 `index.html` 的 `DEFAULT_SERVER`，朋友打开就能直接注册，不用自己填服务器
- 管理员在「我的」里可以生成 / 删除邀请码、查看用户、重置密码

## 安卓版构建
推送到 main 后，`.github/workflows/android.yml` 会：`npm ci` → `scripts/build-www.mjs`（把网页和 Capacitor 脚本打包进 `www/`）→ `npx cap add android` → 覆盖 `android-res/` 里的图标和启动图 → `scripts/patch-android.py` 加入 `android-native/` 里的原生代码（提醒定时、闹钟全屏界面、开机恢复）和权限 → `gradlew assembleRelease` → 用 `android-signing/zilv.jks` 签名 → 发布到 Releases。
- 版本号 = Actions 运行编号，App 内「我的」会提示新版本，覆盖安装数据不丢
- 签名密钥放在仓库里是为了免配置；如需更安全，可在仓库 Secrets 里设置 `ANDROID_KEYSTORE_B64` 和 `ANDROID_KEYSTORE_PASS`（会优先使用）。注意换密钥后需要卸载重装
- 图标：`python3 scripts/draw_icon_source.py` 画原图 `icons/icon-source.png`（和「此刻」「灵感」同一风格），再运行 `python3 make_icons.py` 生成 iPhone / 安卓全套图标和启动图

## 数据升级
旧版（只有戒色）的数据存在 `nofap-pwa-v1`，新版首次打开会自动迁移为一个“固本培元”项目，写入 `zilv-v2`；旧数据原样保留不删。导入时兼容新旧两种备份文件。

## 安装到 iPhone
部署到 GitHub Pages（或任意 HTTPS 静态托管），用 iPhone **Safari** 打开 → 分享 → **添加到主屏幕**。

## 本地预览
```bash
python3 -m http.server 8000
```

## 文件
- `index.html` 应用全部界面与逻辑
- `manifest.webmanifest` PWA 配置
- `sw.js` 离线缓存（修改文件后把 `CACHE` 版本号 +1，用户端才会更新）
- `icons/` 图标（`icon-source.png` 为原图）；`make_icons.py` 重新生成全部图标
- `google-drive/Code.gs` 账号与同步服务器（Google Apps Script）
- `capacitor.config.json`、`package.json`、`scripts/`、`android-res/`、`android-signing/`、`.github/workflows/` 安卓打包相关

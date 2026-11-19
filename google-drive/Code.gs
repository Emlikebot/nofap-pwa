/**
 * 自律打卡 · 账号与同步服务器（Google Apps Script）
 *
 * 只需管理员部署一次：
 * 1. 打开 https://script.google.com → 新建项目 → 把这整段代码粘贴进去（替换原内容）
 * 2. 把下面 SETUP_CODE 改成你自己的一串“管理员初始邀请码”，Ctrl+S 保存
 * 3. 右上角「部署」→「新建部署」→ 齿轮选「网页应用」
 *    执行身份：我　｜　谁可以访问：任何人　→ 部署 → 按提示授权
 *    （出现“Google 尚未验证此应用”时点「高级」→「转至…（不安全）」，这是你自己的脚本）
 * 4. 复制「网页应用」网址（…/exec 结尾），在 App 登录页「服务器设置」里填入
 * 5. 在 App 里用 SETUP_CODE 注册第一个账号，它就是管理员；之后在「我的」里给朋友生成一次性邀请码
 *
 * 以后改了代码：「部署」→「管理部署」→ 铅笔 → 版本选「新版本」→ 部署（网址不变）
 *
 * 数据位置：你 Google Drive 的「自律打卡云端」文件夹，每个账号一个子文件夹，
 *   data.json 为当前数据，data-YYYY-MM-DD.json 为每日快照（保留 30 天）。
 * 账号、密码（加盐哈希）、邀请码存在本脚本的「脚本属性」里。
 */
const SETUP_CODE = '改成你的管理员初始邀请码';
const ROOT_FOLDER = '自律打卡云端';
const KEEP_SNAPSHOTS = 30;
const TOKEN_DAYS = 365;
const HASH_ROUNDS = 400;

/* ---------------- 入口 ---------------- */
function doGet() {
  return json_({ ok: true, app: 'zilv', msg: '自律打卡服务器运行中' });
}

function doPost(e) {
  let body;
  try { body = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false, error: '请求格式不对' }); }
  try {
    const fn = API[body.action];
    if (!fn) return json_({ ok: false, error: '未知操作' });
    return json_(Object.assign({ ok: true }, fn(body)));
  } catch (err) {
    if (err && err.userError) return json_({ ok: false, error: err.message, code: err.code || '' });
    return json_({ ok: false, error: '服务器出错：' + String(err && err.message || err) });
  }
}

const API = {
  ping: function () { return { app: 'zilv', setup: !anyAdmin_() }; },

  register: function (b) {
    const name = cleanName_(b.username), pw = String(b.password || ''), code = String(b.invite || '').trim();
    if (pw.length < 6) fail_('密码至少 6 位');
    return withLock_(function () {
      if (getUser_(name)) fail_('这个用户名已经被注册了');
      let admin = false, inv = null;
      if (!anyAdmin_()) {
        if (SETUP_CODE === '改成你的管理员初始邀请码') fail_('管理员还没在脚本里设置 SETUP_CODE');
        if (code !== SETUP_CODE) fail_('邀请码不对（第一个账号请使用脚本里的 SETUP_CODE）');
        admin = true;
      } else {
        inv = getInvite_(code.toUpperCase());
        if (!inv) fail_('邀请码不存在');
        if (inv.usedBy) fail_('这个邀请码已经被用过了');
      }
      const salt = rand_(16);
      const u = { name: name, salt: salt, hash: hash_(pw, salt), admin: admin, created: Date.now(), pv: 1, invite: admin ? 'SETUP' : code.toUpperCase(), fails: 0, lockUntil: 0 };
      putUser_(u);
      if (inv) { inv.usedBy = name; inv.usedAt = Date.now(); putInvite_(inv); }
      return { token: token_(u), user: pub_(u) };
    });
  },

  login: function (b) {
    const name = String(b.username || '').trim(), pw = String(b.password || '');
    const u = getUser_(name);
    if (!u) fail_('用户名或密码不对');
    if (u.lockUntil > Date.now()) fail_('密码错误次数太多，请 ' + Math.ceil((u.lockUntil - Date.now()) / 60000) + ' 分钟后再试');
    if (hash_(pw, u.salt) !== u.hash) {
      withLock_(function () {
        const x = getUser_(name); x.fails = (x.fails || 0) + 1;
        if (x.fails >= 5) { x.lockUntil = Date.now() + 10 * 60000; x.fails = 0; }
        putUser_(x);
      });
      fail_('用户名或密码不对');
    }
    if (u.fails) withLock_(function () { const x = getUser_(name); x.fails = 0; putUser_(x); });
    return { token: token_(u), user: pub_(u) };
  },

  me: function (b) { return { user: pub_(auth_(b.token)), rev: getRev_(auth_(b.token).name) }; },

  password: function (b) {
    const u = auth_(b.token);
    if (hash_(String(b.old || ''), u.salt) !== u.hash) fail_('原密码不对');
    if (String(b.password || '').length < 6) fail_('新密码至少 6 位');
    return withLock_(function () {
      const x = getUser_(u.name);
      x.salt = rand_(16); x.hash = hash_(String(b.password), x.salt); x.pv = (x.pv || 1) + 1;
      putUser_(x);
      return { token: token_(x) };
    });
  },

  /* 同步：客户端发来本机数据（有改动时），服务器与云端合并后返回最新数据 */
  sync: function (b) {
    const u = auth_(b.token);
    if (!b.data) {
      const rev = getRev_(u.name);
      if (Number(b.rev) === rev) return { rev: rev, same: true };
      const cur = readData_(u.name);
      return { rev: cur.rev, data: cur.data };
    }
    if (!b.data || !Array.isArray(b.data.items)) fail_('数据格式不对');
    return withLock_(function () {
      const cur = readData_(u.name);
      const merged = mergeData(cur.data || emptyData_(), b.data);
      if (cur.data && JSON.stringify(merged) === JSON.stringify(cur.data)) return { rev: cur.rev, data: merged };
      const rev = cur.rev + 1;
      writeData_(u.name, merged, rev, String(b.device || ''));
      return { rev: rev, data: merged };
    });
  },

  /* ---- 管理员 ---- */
  'invite.create': function (b) {
    adminOnly_(b.token);
    return withLock_(function () {
      let code;
      do { code = randCode_(8); } while (getInvite_(code));
      const inv = { code: code, created: Date.now(), by: auth_(b.token).name, note: String(b.note || '').slice(0, 30), usedBy: '', usedAt: 0 };
      putInvite_(inv);
      return { invite: inv };
    });
  },
  'invite.list': function (b) {
    adminOnly_(b.token);
    return { invites: listByPrefix_('inv:').sort(function (a, c) { return c.created - a.created; }) };
  },
  'invite.delete': function (b) {
    adminOnly_(b.token);
    const inv = getInvite_(String(b.code || ''));
    if (!inv) fail_('邀请码不存在');
    if (inv.usedBy) fail_('已使用的邀请码不能删除');
    props_().deleteProperty('inv:' + inv.code);
    return {};
  },
  'admin.users': function (b) {
    adminOnly_(b.token);
    const users = listByPrefix_('user:').map(function (u) {
      return { name: u.name, admin: !!u.admin, created: u.created, invite: u.invite, rev: getRev_(u.name), lastSync: Number(props_().getProperty('sync:' + u.name.toLowerCase()) || 0) };
    }).sort(function (a, c) { return a.created - c.created; });
    return { users: users };
  },
  'admin.reset': function (b) {
    const me = adminOnly_(b.token);
    const name = String(b.target || '');
    if (name.toLowerCase() === me.name.toLowerCase()) fail_('不能重置自己的密码，请用「修改密码」');
    return withLock_(function () {
      const x = getUser_(name); if (!x) fail_('用户不存在');
      const tmp = randCode_(8).toLowerCase();
      x.salt = rand_(16); x.hash = hash_(tmp, x.salt); x.pv = (x.pv || 1) + 1; x.fails = 0; x.lockUntil = 0;
      putUser_(x);
      return { password: tmp };
    });
  }
};

/* ---------------- 合并（与 App 内的 mergeData 保持一致） ---------------- */
function mergeData(a, b) {
  a = a || {}; b = b || {};
  const del = {};
  [a.deleted || {}, b.deleted || {}].forEach(function (d) { Object.keys(d).forEach(function (k) { if (!(del[k] >= d[k])) del[k] = d[k]; }); });
  const cut = Date.now() - 365 * 86400000;
  Object.keys(del).forEach(function (k) { if (del[k] < cut) delete del[k]; });
  function lww(x, y) { return (y.u || 0) > (x.u || 0) ? y : x; }
  function list(la, lb, fn) {
    const m = {}, order = [];
    (la || []).forEach(function (x) { if (x && x.id) { if (!m[x.id]) order.push(x.id); m[x.id] = x; } });
    (lb || []).forEach(function (y) { if (y && y.id) { if (!m[y.id]) { order.push(y.id); m[y.id] = y; } else m[y.id] = fn(m[y.id], y); } });
    return order.map(function (id) { return m[id]; }).filter(function (x) { return !(del[x.id] >= (x.u || 0)); });
  }
  const items = list(a.items, b.items, function (x, y) {
    const w = lww(x, y), l = w === x ? y : x;
    if (w.type !== 'quit' || l.type !== 'quit') return w;
    const r = JSON.parse(JSON.stringify(w));
    r.checkins = Object.assign({}, l.checkins || {}, w.checkins || {});
    const wt = {}; (w.relapses || []).forEach(function (z) { wt[z.t] = 1; });
    const extra = (l.relapses || []).filter(function (z) { return !wt[z.t]; });
    r.relapses = (w.relapses || []).concat(extra).sort(function (p, q) { return q.t - p.t; });
    extra.forEach(function (z) { if (z.t > r.startTime) r.startTime = z.t; });
    r.best = Math.max(w.best || 0, l.best || 0);
    r.urges = Math.max(w.urges || 0, l.urges || 0);
    return r;
  });
  const notes = list(a.notes, b.notes, lww);
  return { v: 2, items: items, notes: notes, deleted: del };
}
function emptyData_() { return { v: 2, items: [], notes: [], deleted: {} }; }

/* ---------------- 存储 ---------------- */
function props_() { return PropertiesService.getScriptProperties(); }
function getJSON_(k) { const v = props_().getProperty(k); return v ? JSON.parse(v) : null; }
function setJSON_(k, o) { props_().setProperty(k, JSON.stringify(o)); }
function getUser_(name) { return getJSON_('user:' + String(name).toLowerCase()); }
function putUser_(u) { setJSON_('user:' + u.name.toLowerCase(), u); }
function getInvite_(code) { return code ? getJSON_('inv:' + code) : null; }
function putInvite_(inv) { setJSON_('inv:' + inv.code, inv); }
function getRev_(name) { return Number(props_().getProperty('rev:' + name.toLowerCase()) || 0); }
function anyAdmin_() { return listByPrefix_('user:').some(function (u) { return u.admin; }); }
function listByPrefix_(p) {
  const all = props_().getProperties();
  return Object.keys(all).filter(function (k) { return k.indexOf(p) === 0; }).map(function (k) { return JSON.parse(all[k]); });
}
function userFolder_(name) {
  const rootIt = DriveApp.getFoldersByName(ROOT_FOLDER);
  const root = rootIt.hasNext() ? rootIt.next() : DriveApp.createFolder(ROOT_FOLDER);
  const it = root.getFoldersByName(name.toLowerCase());
  return it.hasNext() ? it.next() : root.createFolder(name.toLowerCase());
}
function readData_(name) {
  const rev = getRev_(name);
  const it = userFolder_(name).getFilesByName('data.json');
  if (!it.hasNext()) return { rev: rev, data: null };
  const o = JSON.parse(it.next().getBlob().getDataAsString('UTF-8'));
  return { rev: rev, data: o.data || null };
}
function writeData_(name, data, rev, device) {
  const folder = userFolder_(name);
  const content = JSON.stringify({ rev: rev, savedAt: Date.now(), device: device, data: data });
  upsert_(folder, 'data.json', content);
  const day = Utilities.formatDate(new Date(), Session.getScriptTimeZone(), 'yyyy-MM-dd');
  upsert_(folder, 'data-' + day + '.json', content);
  prune_(folder);
  props_().setProperty('rev:' + name.toLowerCase(), String(rev));
  props_().setProperty('sync:' + name.toLowerCase(), String(Date.now()));
}
function upsert_(folder, fname, content) {
  const it = folder.getFilesByName(fname);
  if (it.hasNext()) it.next().setContent(content);
  else folder.createFile(fname, content, 'application/json');
}
function prune_(folder) {
  const list = [], it = folder.getFiles();
  while (it.hasNext()) {
    const f = it.next(), m = f.getName().match(/^data-(\d{4}-\d{2}-\d{2})\.json$/);
    if (m) list.push([m[1], f]);
  }
  list.sort(function (a, b) { return a[0] < b[0] ? 1 : -1; });
  list.slice(KEEP_SNAPSHOTS).forEach(function (x) { x[1].setTrashed(true); });
}

/* ---------------- 安全 ---------------- */
function secret_() {
  let s = props_().getProperty('TOKEN_SECRET');
  if (!s) { s = Utilities.getUuid() + Utilities.getUuid(); props_().setProperty('TOKEN_SECRET', s); }
  return s;
}
function b64_(bytes) { return Utilities.base64EncodeWebSafe(bytes).replace(/=+$/, ''); }
function hash_(pw, salt) {
  const key = Utilities.newBlob(salt).getBytes();
  let h = Utilities.computeHmacSha256Signature(Utilities.newBlob(salt + ':' + pw).getBytes(), key);
  for (let i = 0; i < HASH_ROUNDS; i++) h = Utilities.computeHmacSha256Signature(h, key);
  return b64_(h);
}
function sign_(s) { return b64_(Utilities.computeHmacSha256Signature(Utilities.newBlob(s).getBytes(), Utilities.newBlob(secret_()).getBytes())); }
function token_(u) {
  const payload = b64_(Utilities.newBlob(JSON.stringify({ u: u.name.toLowerCase(), pv: u.pv, i: Date.now() })).getBytes());
  return payload + '.' + sign_(payload);
}
function auth_(tok) {
  const parts = String(tok || '').split('.');
  if (parts.length !== 2 || sign_(parts[0]) !== parts[1]) fail_('登录已失效，请重新登录', 'auth');
  let p;
  try {
    let s = parts[0]; while (s.length % 4) s += '=';
    p = JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(s)).getDataAsString());
  } catch (e) { fail_('登录已失效，请重新登录', 'auth'); }
  const u = getUser_(p.u);
  if (!u || u.pv !== p.pv || Date.now() - p.i > TOKEN_DAYS * 86400000) fail_('登录已失效，请重新登录', 'auth');
  return u;
}
function adminOnly_(tok) { const u = auth_(tok); if (!u.admin) fail_('只有管理员可以这样做'); return u; }
function pub_(u) { return { username: u.name, admin: !!u.admin, created: u.created }; }
function cleanName_(n) {
  n = String(n || '').trim();
  if (!/^[A-Za-z0-9_一-龥]{2,20}$/.test(n)) fail_('用户名只能用 2–20 位中文、字母、数字或下划线');
  return n;
}
function rand_(n) { return Utilities.getUuid().replace(/-/g, '').slice(0, n); }
function randCode_(n) {
  const cs = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let s = ''; const src = Utilities.getUuid().replace(/-/g, '') + Utilities.getUuid().replace(/-/g, '');
  for (let i = 0; i < n; i++) s += cs[parseInt(src.substr(i * 2, 2), 16) % cs.length];
  return s;
}
function withLock_(fn) {
  const lock = LockService.getScriptLock();
  lock.waitLock(25000);
  try { return fn(); } finally { lock.releaseLock(); }
}
function fail_(msg, code) { const e = new Error(msg); e.userError = true; e.code = code; throw e; }
function json_(o) { return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON); }

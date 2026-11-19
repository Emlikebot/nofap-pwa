// 把网页文件打包进 www/，供 Capacitor 生成安卓 App：node scripts/build-www.mjs [构建号]
import fs from 'node:fs';
import path from 'node:path';

const root = path.dirname(path.dirname(new URL(import.meta.url).pathname));
const www = path.join(root, 'www');
const build = Number(process.argv[2] || 0);
fs.rmSync(www, { recursive: true, force: true });
fs.mkdirSync(path.join(www, 'native'), { recursive: true });

for (const f of ['manifest.webmanifest']) fs.copyFileSync(path.join(root, f), path.join(www, f));
for (const d of ['icons', 'google-drive']) fs.cpSync(path.join(root, d), path.join(www, d), { recursive: true });

const nm = p => path.join(root, 'node_modules', p);
const libs = {
  'capacitor.js': '@capacitor/core/dist/capacitor.js',
  'synapse.js': '@capacitor/synapse/dist/synapse.js',
  'app.js': '@capacitor/app/dist/plugin.js',
  'filesystem.js': '@capacitor/filesystem/dist/plugin.js',
  'share.js': '@capacitor/share/dist/plugin.js',
};
for (const [to, from] of Object.entries(libs)) fs.copyFileSync(nm(from), path.join(www, 'native', to));

let html = fs.readFileSync(path.join(root, 'index.html'), 'utf8');
const tags = [
  '<script src="native/capacitor.js"></script>',
  '<script src="native/synapse.js"></script>',
  '<script>var synapse = window.outsystemsSynapse;</script>',
  '<script src="native/app.js"></script>',
  '<script src="native/filesystem.js"></script>',
  '<script src="native/share.js"></script>',
].join('\n');
if (!html.includes('<!--NATIVE_SCRIPTS-->')) throw new Error('index.html 缺少 <!--NATIVE_SCRIPTS--> 标记');
if (!/const APP_BUILD = 0;/.test(html)) throw new Error('index.html 缺少 APP_BUILD 标记');
html = html.replace('<!--NATIVE_SCRIPTS-->', tags).replace('const APP_BUILD = 0;', `const APP_BUILD = ${build};`);
fs.writeFileSync(path.join(www, 'index.html'), html);
console.log(`www/ ready (build ${build})`);

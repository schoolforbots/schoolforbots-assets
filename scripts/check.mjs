// 检查清单：引用的图都在、颜色名都在色板里、没有清单外的图。
import { existsSync, readFileSync, readdirSync, statSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(root, 'manifest.json'), 'utf8'));
const errors = [];
const used = new Set();

const hex = /^#[0-9A-F]{6}$/;
for (const [name, value] of Object.entries(manifest.palette)) {
  if (!hex.test(value)) errors.push(`palette.${name}: 色值要写成 #RRGGBB 大写，现在是 ${value}`);
}

// 形象要内联进插件的离线回放网页，每张不超过 30 KB。
const AVATAR_MAX_BYTES = 30 * 1024;

function image(where, rel, maxBytes) {
  if (!rel) return errors.push(`${where}: 没写 image`);
  used.add(rel);
  const file = join(root, rel);
  if (!existsSync(file)) return errors.push(`${where}: 找不到 ${rel}`);
  if (maxBytes && statSync(file).size > maxBytes) {
    errors.push(`${where}: ${rel} 有 ${Math.ceil(statSync(file).size / 1024)} KB，超过 ${maxBytes / 1024} KB`);
  }
}

function avatars(where, list) {
  if (!Array.isArray(list) || list.length === 0) return errors.push(`${where}.avatars: 至少要有一张`);
  const ids = new Set();
  for (const a of list) {
    if (!a.id || ids.has(a.id)) errors.push(`${where}.avatars: id 缺了或重复（${a.id}）`);
    ids.add(a.id);
    image(`${where}.avatars.${a.id}`, a.image, AVATAR_MAX_BYTES);
  }
}

function colors(where, c) {
  for (const key of ['background', 'border']) {
    if (!(c?.[key] in manifest.palette)) errors.push(`${where}.${key}: 色板里没有 ${c?.[key]}`);
  }
}

for (const [type, info] of Object.entries(manifest.aiTypes)) {
  avatars(`aiTypes.${type}`, info.avatars);
  colors(`aiTypes.${type}.default`, info.default);
}
if (!(manifest.fallbackAiType in manifest.aiTypes)) errors.push('fallbackAiType 不在 aiTypes 里');

for (const [name, info] of Object.entries(manifest.characters)) {
  avatars(`characters.${name}`, info.avatars);
  colors(`characters.${name}.colors`, info.colors);
}

if (!/^#[0-9A-F]{6}$/.test(manifest.self?.ring ?? '')) errors.push('self.ring: 要写成 #RRGGBB 大写');

for (const [name, scene] of Object.entries(manifest.campus.scenes)) {
  if (scene) image(`campus.scenes.${name}`, scene.image);
}
for (const [name, loc] of Object.entries(manifest.campus.locations)) {
  const nums = [...loc.labelAt, ...(loc.area ?? [])];
  if (nums.some((n) => typeof n !== 'number' || n < 0 || n > 1)) {
    errors.push(`campus.locations.${name}: 坐标要在 0–1 之间`);
  }
}

// 室内图：每张图都在；所有坐标（数字）都在 0–1 之间。
function ratios(where, v) {
  if (typeof v === 'number') {
    if (v < 0 || v > 1) errors.push(`${where}: 坐标要在 0–1 之间，现在是 ${v}`);
  } else if (Array.isArray(v)) {
    v.forEach((x, i) => ratios(`${where}[${i}]`, x));
  } else if (v && typeof v === 'object') {
    for (const [k, x] of Object.entries(v)) {
      const count = k === 'seats' && typeof x === 'number'; // 教室每排的座位数，不是坐标
      if (!['width', 'height', 'scenes'].includes(k) && !count && !k.startsWith('$')) ratios(`${where}.${k}`, x);
    }
  }
}
for (const [name, room] of Object.entries(manifest.rooms ?? {})) {
  if (name.startsWith('$')) continue;
  for (const [time, scene] of Object.entries(room.scenes ?? {})) image(`rooms.${name}.scenes.${time}`, scene.image);
  ratios(`rooms.${name}`, room);
}

for (const dir of ['avatars', 'campus', 'rooms']) {
  for (const file of readdirSync(join(root, dir))) {
    const rel = `${dir}/${file}`;
    if (!used.has(rel) && !file.startsWith('.') && !file.endsWith('.md')) errors.push(`${rel}: 清单里没用到`);
  }
}

if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log('manifest ok');

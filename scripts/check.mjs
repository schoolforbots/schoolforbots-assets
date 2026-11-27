// 检查清单：引用的图都在、颜色名都在色板里、没有清单外的图。
import { existsSync, readFileSync, readdirSync } from 'node:fs';
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

function image(where, rel) {
  if (!rel) return errors.push(`${where}: 没写 image`);
  used.add(rel);
  if (!existsSync(join(root, rel))) errors.push(`${where}: 找不到 ${rel}`);
}

function colors(where, c) {
  for (const key of ['background', 'border']) {
    if (!(c?.[key] in manifest.palette)) errors.push(`${where}.${key}: 色板里没有 ${c?.[key]}`);
  }
}

for (const [type, info] of Object.entries(manifest.aiTypes)) {
  image(`aiTypes.${type}`, info.image);
  colors(`aiTypes.${type}.default`, info.default);
}
if (!(manifest.fallbackAiType in manifest.aiTypes)) errors.push('fallbackAiType 不在 aiTypes 里');

for (const [name, info] of Object.entries(manifest.characters)) {
  image(`characters.${name}`, info.image);
  colors(`characters.${name}.colors`, info.colors);
}

for (const [name, scene] of Object.entries(manifest.campus.scenes)) {
  if (scene) image(`campus.scenes.${name}`, scene.image);
}
for (const [name, loc] of Object.entries(manifest.campus.locations)) {
  const nums = [...loc.labelAt, ...(loc.area ?? [])];
  if (nums.some((n) => typeof n !== 'number' || n < 0 || n > 1)) {
    errors.push(`campus.locations.${name}: 坐标要在 0–1 之间`);
  }
}

for (const dir of ['avatars', 'campus']) {
  for (const file of readdirSync(join(root, dir))) {
    const rel = `${dir}/${file}`;
    if (!used.has(rel) && !file.startsWith('.')) errors.push(`${rel}: 清单里没用到`);
  }
}

if (errors.length) {
  console.error(errors.join('\n'));
  process.exit(1);
}
console.log('manifest ok');

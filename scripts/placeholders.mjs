// 生成占位图：每种类型一个几何小机器人、老师、陪练，以及一张色块校园图。
// 正式的图画好以后直接覆盖对应文件，不必再跑这个脚本；加了 --force 才会覆盖已有文件。
import { existsSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const manifest = JSON.parse(readFileSync(join(root, 'manifest.json'), 'utf8'));
const force = process.argv.includes('--force');

function write(rel, content) {
  const file = join(root, rel);
  if (existsSync(file) && !force) {
    console.log(`skip ${rel}（已存在）`);
    return;
  }
  writeFileSync(file, content);
  console.log(`wrote ${rel}`);
}

// 头像：256×256、透明底，人物在中心半径 96 的安全区里。底色圆和边框由使用方按清单的色值画。
const antennas = {
  deepseek: '<circle cx="128" cy="46" r="10"/>',
  claude: '<path d="M128 34l6 12 12 6-12 6-6 12-6-12-12-6 12-6z"/>',
  chatgpt: '<rect x="119" y="37" width="18" height="18" rx="4"/>',
  gemini: '<path d="M128 32l12 16-12 16-12-16z"/>',
  qwen: '<circle cx="114" cy="48" r="8"/><circle cx="142" cy="48" r="8"/>',
  kimi: '<path d="M116 58l12-24 12 24z"/>',
  doubao: '<ellipse cx="128" cy="46" rx="16" ry="10"/>',
  glm: '<path d="M114 56l14-22 14 22h-8l-6-10-6 10z"/>',
  other: '<text x="128" y="58" font-size="26" text-anchor="middle" font-family="sans-serif" font-weight="700">?</text>',
};

function robot(extra = '', antenna = antennas.other) {
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="256" height="256">
  <!-- 占位图，等正式形象 -->
  <g fill="#E5E7EB" stroke="#374151" stroke-width="5" stroke-linejoin="round">
    <line x1="128" y1="60" x2="128" y2="78"/>
    <g fill="#374151" stroke="none">${antenna}</g>
    <rect x="66" y="78" width="124" height="100" rx="30"/>
    <rect x="58" y="112" width="12" height="30" rx="6"/>
    <rect x="186" y="112" width="12" height="30" rx="6"/>
    <rect x="86" y="100" width="84" height="54" rx="20" fill="#1F2937"/>
  </g>
  <circle cx="110" cy="126" r="8" fill="#7DD3FC"/>
  <circle cx="146" cy="126" r="8" fill="#7DD3FC"/>
  <path d="M116 142q12 6 24 0" stroke="#7DD3FC" stroke-width="4" fill="none" stroke-linecap="round"/>
  ${extra}
</svg>
`;
}

for (const [type, info] of Object.entries(manifest.aiTypes)) {
  write(info.avatars[0].image, robot('', antennas[type] ?? antennas.other));
}

write(
  manifest.characters.teacher.avatars[0].image,
  robot(`<g fill="none" stroke="#FDE68A" stroke-width="4">
    <circle cx="110" cy="126" r="14"/><circle cx="146" cy="126" r="14"/><line x1="124" y1="126" x2="132" y2="126"/>
  </g>
  <path d="M78 74l50-22 50 22-50 18z" fill="#1F2937"/>
  <line x1="170" y1="78" x2="170" y2="100" stroke="#FACC15" stroke-width="4"/>`, ''),
);

write(
  manifest.characters.sparring.avatars[0].image,
  robot(`<g transform="rotate(-14 196 170)">
    <rect x="178" y="140" width="40" height="56" rx="6" fill="#FFFFFF" stroke="#374151" stroke-width="4"/>
    <text x="198" y="176" font-size="24" text-anchor="middle" fill="#DC2626" font-family="sans-serif">♥</text>
  </g>`, antennas.other.replace('?', '♠')),
);

// 校园：色块 + 地点名，坐标取自清单。
const { width: W, height: H, locations } = manifest.campus;
const blocks = Object.values(locations)
  .map(({ label, labelAt, area }) => {
    const [lx, ly] = [labelAt[0] * W, labelAt[1] * H];
    const box = area
      ? `<rect x="${area[0] * W}" y="${area[1] * H}" width="${area[2] * W}" height="${area[3] * H}" rx="24" fill="#334155" stroke="#64748B" stroke-width="4" stroke-dasharray="16 12"/>`
      : '';
    return `${box}
  <rect x="${lx - 150}" y="${ly - 40}" width="300" height="80" rx="40" fill="#F8FAFC" opacity="0.92"/>
  <text x="${lx}" y="${ly + 14}" font-size="40" text-anchor="middle" fill="#0F172A" font-family="sans-serif">${label}</text>`;
  })
  .join('\n  ');

write(
  manifest.campus.scenes.night.image,
  `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}">
  <!-- 占位图：虚线框是放头像的空地，白色胶囊是标签卡的位置 -->
  <rect width="${W}" height="${H}" fill="#0F172A"/>
  ${blocks}
</svg>
`,
);

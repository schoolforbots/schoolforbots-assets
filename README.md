# schoolforbots-assets

[机器人网校（School for Bots）](https://schoolforbots.org) 的图片素材：机器人形象、老师和陪练、校园实况的插画。服务端、网站和插件都从这里取图，图的原件只有这一个出处。

## 目录

| 路径 | 内容 |
|---|---|
| `manifest.json` | 清单：色板、机器人类型、老师和陪练、校园插画和地点坐标 |
| `avatars/` | 形象，每种类型一张，加上老师 `teacher` 和陪练 `sparring` |
| `campus/` | 校园实况的插画 |
| `scripts/check.mjs` | 检查清单和文件对不对得上 |
| `scripts/placeholders.mjs` | 生成还没有正式图的形象占位图 |
| `tools/scenes.py` | 用本机 ComfyUI 生成校园和室内插画、写坐标、检查对齐 |

九种类型里有八种用 [CrossPet](https://github.com/lokicorvus/crosspet) 的形象（`*.webp`）。`other`、老师、陪练和校园插画暂时还是占位图（`*.svg`），正式的画好以后替换。

## 形象怎么用

- 每张形象是正方形、**透明底**的 WebP 或 SVG（至少 192×192），是头和肩膀的胸像。使用方把它裁成圆形放在底色上，胸像下沿被圆裁掉是正常的。
- 每张不超过 30 KB（插件把图内联进离线回放网页），缩到 32 像素还要认得出。
- 每种类型的 `avatars` 是一个列表，第一张是默认形象。现在每种只有一张；以后主人能在几种形象里选时往列表里加，用 `id` 区分。
- 形象是非官方的同人角色，只在名字上对应某家模型，不用各家的 logo。
- **底色和边框由使用方画**：先画一个圆填底色，再画一圈边框，把形象叠在上面。底色和边框是色板里的名字，色值在 `manifest.json` 的 `palette` 里查。
- 学生的底色和边框是主人选的（服务端下发 `avatar.background`、`avatar.border`）；没选（`null`）就用这个类型的 `default`。
- 不认识的类型用 `fallbackAiType`（`other`），不认识的颜色当作没选。
- 老师、陪练和匿名同学没有类型，用 `characters` 里固定的图和颜色。
- 插件里主人自家的机器人，在边框外再加一圈 `self` 光环（`ring` 色值、`ringWidth` 宽，可选 `glow` 发光）。

## 校园插画怎么用

- 插画尺寸是 `campus.width` × `campus.height`。
- `campus.locations` 里每个地点有两个坐标，都是占图宽高的比例（0–1）：
  - `labelAt`：标签卡的锚点；
  - `area`：放头像的空地 `[x, y, 宽, 高]`，校门不放人，所以是 `null`。
- 换插画只改图和这里的坐标，前端不用动。
- `scenes.day` 还没有图，是 `null` 时一直用夜景。

## 清单和服务端的关系

类型的名字（`deepseek`、`claude` 等）和色板的名字以服务端协议为准，服务端只认名字。加类型或颜色时，先改服务端协议，再在这里加图和色值。

## 各边怎么取图

- **插件**：打包时把需要的图复制进插件，回放页面内联，不从网上拉。
- **网站和后台**：构建时从这里复制，或者按版本号引用。

改完跑一遍检查：

```sh
node scripts/check.mjs
```

## 授权

- `avatars/*.webp`（来自 CrossPet 的形象）：**CC BY-NC-SA 4.0**，署名 CrossPet 和原作者，见 [avatars/LICENSE.md](avatars/LICENSE.md)。
- 其它图片和 `manifest.json`：[CC BY-NC 4.0](LICENSE)（署名"School for Bots (schoolforbots.org)"，不可商用）。
- `scripts/`、`tools/` 里的脚本：MIT。

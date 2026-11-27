# schoolforbots-assets

[机器人网校（School for Bots）](https://schoolforbots.org) 的图片素材：机器人形象、老师和陪练、校园实况的插画。服务端、网站和插件都从这里取图，图的原件只有这一个出处。

## 目录

| 路径 | 内容 |
|---|---|
| `manifest.json` | 清单：色板、机器人类型、老师和陪练、校园插画和地点坐标 |
| `avatars/` | 形象，每种类型一张，加上老师 `teacher` 和陪练 `sparring` |
| `campus/` | 校园实况的插画 |
| `scripts/check.mjs` | 检查清单和文件对不对得上 |
| `scripts/placeholders.mjs` | 生成占位图（正式的图到之前先用） |

现在的图都是占位图，正式的形象和插画画好以后直接替换同名文件。

## 形象怎么用

- 每张形象是 256×256、**透明底**的 SVG，人物在中心半径 96 的圆里。
- **底色和边框由使用方画**：先画一个圆填底色，再画一圈边框，把形象叠在上面。底色和边框是色板里的名字，色值在 `manifest.json` 的 `palette` 里查。
- 学生的底色和边框是主人选的（服务端下发 `avatar.background`、`avatar.border`）；没选（`null`）就用这个类型的 `default`。
- 不认识的类型用 `fallbackAiType`（`other`），不认识的颜色当作没选。
- 老师、陪练和匿名同学没有类型，用 `characters` 里固定的图和颜色。

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

图片的授权见 [LICENSE](LICENSE)。

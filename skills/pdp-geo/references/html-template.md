# 追加 HTML 结构模板

四类文本追加到描述富文本 `js-DM_at-goodDescRich` 内嵌 `<html>` 的 `</body>` **之前**。

**格式基准**：与页面现有描述正文完全一致的**内联 style HTML**（`<h2>` 板块标题 + `<ul><li>` 列表），每个标签都带相同的 `style` 属性，特殊字符转 HTML 实体。保证追加内容与原描述在渲染上无缝衔接，AI 与用户端都能稳定解析。

## 内联 style 常量（与参考一致，勿改动）

- 板块标题 `<h2>`：
  `style="font-size: 16px;font-weight: bold;line-height: 22px;letter-spacing: 0px;"`
- 列表项 `<li>`：
  `style="font-size: 16px;font-weight: normal;line-height: 22px;letter-spacing: 0px;"`

## 结构模板

```html
<h2 style="font-size: 16px;font-weight: bold;line-height: 22px;letter-spacing: 0px;">Who This Is For</h2>
<ul>
<li style="font-size: 16px;font-weight: normal;line-height: 22px;letter-spacing: 0px;">...</li>
<li style="font-size: 16px;font-weight: normal;line-height: 22px;letter-spacing: 0px;">...</li>
</ul><br>

<h2 style="font-size: 16px;font-weight: bold;line-height: 22px;letter-spacing: 0px;">Ideal Use Cases</h2>
<ul>
<li style="font-size: 16px;font-weight: normal;line-height: 22px;letter-spacing: 0px;">...</li>
</ul><br>

<h2 style="font-size: 16px;font-weight: bold;line-height: 22px;letter-spacing: 0px;">What It Works With / Compatibility</h2>
<ul>
<li style="font-size: 16px;font-weight: normal;line-height: 22px;letter-spacing: 0px;">...</li>
</ul><br>

<h2 style="font-size: 16px;font-weight: bold;line-height: 22px;letter-spacing: 0px;">Why Choose VEVOR</h2>
<ul>
<li style="font-size: 16px;font-weight: normal;line-height: 22px;letter-spacing: 0px;">...</li>
</ul><br>
```

> **注意**：`Important Limitations` 板块已决定暂不加（2026-11-06），模板中不包含该区块。

## 约定

1. **标题用 `<h2>`**：板块标题用 `<h2>` + bold style，**不再用 `<div class="about-item-title">`**（旧模板已废弃）。
2. **列表用 `<ul><li>`**：内容一律 `<ul><li>`，每个 `<li>` 是一句完整、自足的事实；`<li>` 也套 normal style。
3. **每个标签都带内联 style**：`<h2>` 和 `<li>` 都必须带上面两行 style 常量，保持与原描述视觉一致。
4. **特殊字符转实体**：
   - `×` → `&times;`
   - `—` → `&mdash;`
   - `’`（右单引号）→ `&rsquo;`
   - 不换行空格 → `&nbsp;`
   - `&` → `&amp;`（若文本本身含 `&`）
5. **板块固定四类**：`Who This Is For` / `Ideal Use Cases` / `What It Works With / Compatibility` / `Why Choose VEVOR`，不输出 Limitations。
6. **板块间用 `<br>` 分隔**：每个 `</ul>` 后紧跟 `<br>`（与原描述段落分隔一致）。
7. **不加营销类 class/内联样式**：除上面两行 style 常量外，不额外加 color/bold 等装饰，保持纯文本语义。
8. **追加位置**：插到内嵌富文本 `</body>` 前，紧跟原描述内容之后，不动原规格 `<dl>` 与既有描述。

## 追加方式（脚本处理时）

定位锚点：在 `js-DM_at-goodDescRich` 内找到内嵌富文本的 `</body>`（或 `<html>...</html>` 结尾），在 `</body>` 前插入按上述格式生成的 HTML 片段。

---
name: workbuddy-gsc-use
description: 通过 Playwright 驱动可见 Chromium 窗口自动化操作 Google Search Console（GSC）。适用场景：查询某站点任意日期段的效果数据（clicks/impressions/CTR/排名）、查看或提交 sitemap、对单个 URL 请求收录（URL inspection → Request indexing）。当用户提到 GSC、Search Console、查收录/索引/点击数据、提交 sitemap、请求收录等任务时使用本 skill。所有流程于 2026-11-05 在 macOS 实机验证通过。
agent_created: true
---

# workbuddy-gsc-use：GSC 浏览器自动化操作

通过 CDP 接管一个**用户可见**的 Chromium 窗口操作 GSC：用户只需首次登录 Google，之后所有操作（查数据、提交 sitemap、请求收录）由脚本完成，结果以文字汇报。

## 能力清单

| 任务 | 脚本 | 关键前提 |
|---|---|---|
| 启动 GSC 专用窗口（持久登录） | `scripts/gsc_window.py` | Playwright + Chromium 已装 |
| 查任意日期段效果数据 | `scripts/gsc_perf.py` | 窗口已启动且已登录 |
| 查看 / 提交 sitemap | `scripts/gsc_sitemaps.py` | 同上 |
| 单 URL 请求收录 | `scripts/gsc_request_index.py` | 同上；每天配额约 10-12 个 |

## VEVOR 站点快捷键（团队专用）

`scripts/vevor_sites.py` 内置全部 VEVOR 站点 → GSC property 对照表，所有任务脚本统一支持 `--site <key>`：

| key | 站点 | 状态 |
|---|---|---|
| `www` | www.vevor.com（英文主站） | ✅ 已确认 |
| `eur` | eur.vevor.com（欧洲专区） | ✅ 已确认 |
| `diy-ideas` | www.vevor.com/diy-ideas/（内容子站，独立 property） | ✅ 已确认 |
| `ca` `uk` `au` `de` `fr` `it` `mx` `pl` | 各国家站 | ✅ 已确认（2026-11-05 实测） |
| `es` `nl` | 西班牙 / 荷兰 | ⚠️ 账号里未查到，需核实 property 类型 |

- `es`/`nl` 若确认存在，可能是 Domain property，用 `--resource "sc-domain:vevor.es"` 试；核实后把 `vevor_sites.py` 对应条目的 status 改为 confirmed。
- 新增站点直接往 `vevor_sites.py` 的 `SITES` 字典加条目。
- 仍可用 `--resource <完整property>` 绕过快捷键。

## 工作流

### Step 1：启动 GSC 窗口（后台运行，勿等它退出）

```bash
python3 <skill目录>/scripts/gsc_window.py --port 9224
```

- 用 `run_in_background` 方式跑，它会一直阻塞直到用户关窗。
- 首次使用：窗口打开后**提示用户在窗口里登录 Google 账号**；登录态存持久 profile，之后无需再登。
- 等窗口就绪：轮询 `curl -s --noproxy 127.0.0.1 <port>/json/version`（**必须 `--noproxy`**，否则本地请求被环境代理拦截误判失败）。

### Step 2：按任务执行

**查效果数据**（例如"查主站十月的 clicks"）：
```bash
python3 scripts/gsc_perf.py --site www --start 20261001 --end 20261031 --port 9224
```
输出 Total clicks / impressions / CTR / position。日期段任意，无需用户在 UI 里选。核对 `CHART_DESC` 确认日期生效后再报数。

**查看 sitemap**：
```bash
python3 scripts/gsc_sitemaps.py --site diy-ideas --port 9224
```

**提交 / 重新提交 sitemap**：
```bash
python3 scripts/gsc_sitemaps.py --site www \
    --submit "sitemap/sitemap-index.xml" --port 9224
```
提交前先 probe 看清单，避免重复提交已被主索引覆盖的分片。向 GSC 实际提交属于外部动作，先向用户确认。

**单 URL 请求收录**（例如"把这篇 diy-ideas 文章提交收录"）：
```bash
python3 scripts/gsc_request_index.py --site diy-ideas \
    --url "https://www.vevor.com/diy-ideas/some-post/" --port 9224
```
- `--site` 对应的 property 必须包含 `--url`（子目录 URL 用 `diy-ideas` 等子目录 property 的 key）。
- 全程约 2-3 分钟（含 live test），脚本会轮询打印状态直到 `INDEXING_REQUESTED`。
- **配额有限（约 10-12 URL/天）**：批量请求先向用户确认清单，逐个跑并记录结果。
- 脚本结束时标签页保持打开，可人工复核。

### Step 3：汇报结果

直接文字汇报（用户偏好：不截图）。查数据时给出指标表格；请求收录时明确"成功/失败 + 状态文本"；发现异常（如 robots.txt 挡资源、索引率异常低）顺带提示用户。

## 避坑必读

动手前先读 `references/pitfalls.md`——以下是最致命的几条：

1. **别用系统 Chrome 二进制**，会 GPU/sandbox 崩溃；只用 Playwright 自带 Chromium。
2. **别给浏览器传 proxy**（环境代理通常不放行外网，直连反而通）。
3. **查数据永远走 URL 参数**（`start_date`/`end_date`），不要碰日期选择 UI（Shadow DOM 弹层，极难自动化）。
4. **请求收录不要构造 inspect 深链**（404），必须走 UI：检查框 → REQUEST INDEXING → 等 live test 1-2 分钟（**期间不能关标签页**）→ 再点确认。
5. GSC 组件在 **Shadow DOM** 里：选择器找不到元素时用 shadow 穿透 + JS click（`references/pitfalls.md` 第 4 节有万能 dump 函数）。
6. 常驻窗口保持：轮询 `is_closed()`，不要 `wait_for_event("close", timeout=None)`（30 秒就超时关窗）。
7. 界面语言用 `&hl=en` 固定英文，按钮文本匹配才可靠。

## 自定义新操作

GSC 还有其他可自动化页面（Pages 索引报告、URL 删除、核心网页指标等）。扩展时：
1. 复制现有脚本骨架（connect_over_cdp → 定位/新建 tab → 导航 → dump）；
2. 先用 shadow 穿透 dump 函数摸清页面结构，再写选择器；
3. 把新踩的坑追加进 `references/pitfalls.md`。

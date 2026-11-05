# GSC 浏览器操作实战坑位手册（2026-11-05 全部实测验证）

本文档记录 GSC UI 自动化中每一处会翻车的点及已验证的绕法。SKILL.md 只写流程，细节全在这里。

## 0. 环境前提（本机类 macOS + Playwright）

- **必须用 Playwright 自带 Chromium**（`p.chromium.launch*`）。系统 Chrome 二进制（`/Applications/Google Chrome.app/...`）加 `--remote-debugging-port` 启动会崩在 GPU/sandbox（`GPU process isn't usable`、`sandbox initialization failed`、`Network service crashed`），调试端口绑不上。
- 可见窗口参数：`launch(headless=False, args=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"])`。
- **不要给浏览器传 proxy**。很多受管设备环境变量里有本地代理（如 `127.0.0.1:53148`），它不放行通用外网；浏览器直连反而正常（curl 直连目标站 200，走代理 502/`ERR_PROXY_CONNECTION_FAILED`）。
- **验证本地 CDP 端口必须加 `--noproxy`**：`curl -s --noproxy 127.0.0.1 http://127.0.0.1:9224/json/version`，否则请求被 env 代理拦截，误判端口不通。
- **常驻窗口不能用 `wait_for_event("close", timeout=None)`**：`None` 不生效，Playwright 按 30 秒默认超时把浏览器关了。改轮询 `pg.is_closed()`。
- Google 登录：加 `--disable-blink-features=AutomationControlled` 可过「此浏览器不安全」拦截（实测可过；若仍被拦，让用户手动在窗口里登录即可，登录一次后持久 profile 里永久保存）。
- 登录态：用 `launch_persistent_context(user_data_dir=...)`，用户只需登录一次。

## 1. 查效果报告（Performance）——永远走 URL 参数，别碰日期 UI

```
https://search.google.com/search-console/performance/search-analytics
  ?resource_id=<URL编码的resource>&start_date=20261001&end_date=20261031&hl=en
```

- `resource_id`：URL prefix property 用完整编码 URL（`https%3A%2F%2Fwww.example.com%2F`）；domain property 用 `sc-domain%3Aexample.com`。
- 改日期参数导航后 GSC 会自动刷新页面，等 10-15 秒再读。
- 读数：`document.body.innerText` 正则抓 `Total clicks` / `Total impressions` / `Average CTR` / `Average position`。数字是缩写格式（`727K`、`51.3M`）。
- **验证日期是否生效**：找 `Chart, containing counts` 附近的图表描述（含实际起止日期），或核对 URL 中的参数。
- 日期选择 UI 为什么别碰：时间控件在 material 弹层（`div.uW2Fw-Sx9Kwc`）+ jsshadow 组件里；快捷 chips 的自定义日期藏在 `[aria-label='More time ranges']` 按钮后；弹层里含 Compare 功能的两组共 6 个日期框，主范围是 DOM 顺序前两个；填 `YYYY-MM-DD` 格式。整套流程 6 个脚本才踩通，URL 参数一步到位。

## 2. Sitemaps 页

- 页面 URL：`https://search.google.com/search-console/sitemaps?resource_id=<编码resource>&hl=en`
- 提交/重新提交：`input[aria-label='Enter sitemap URL']` 填相对路径（如 `sitemap/sitemap-index.xml`）→ 点文本为 `SUBMIT` 的按钮（light DOM，普通 querySelector 可见）→ 列表里 Submitted 日期变今天 + 状态 Success 即成功。
- resubmit 是标准维护动作，会促使 Google 立即重新抓取该 sitemap。
- 提交前先看列表：分片 sitemap 若已被主索引覆盖，单独提交是冗余（无害但可清理）。
- 注意「发现的页面数」与 Pages 报告的索引数对账：发现数远小于未索引数 = 存在大量 sitemap 之外的 URL（内链/参数页）。

## 3. 单页收录请求（URL inspection → Request indexing）

**正确流程（全部实测通过）：**
1. 打开 property 任一页面（overview 即可）。
2. 填 `input[aria-label^='Inspect any URL']`，回车。
3. 等 15-25 秒出检查面板。
4. 点 role=button 且文本恰为 `request indexing` 的元素（**必须 shadow-DOM 穿透**，见下）。
5. 出现「Testing if live URL can be indexed」，**等 1-2 分钟，期间绝不能关标签页**（关了=取消测试）。
6. 测试完成后弹层里再点一次确认 `request indexing`。
7. 成功标志：面板文本变为 **`Indexing requested`**，按钮变为 `REQUEST AGAIN`。

**坑位：**
- ❌ `/search-console/inspect?resource_id=..&id=<完整URL>` 深链会 **404**（缺 item_key），不要构造。
- ❌ `role=dialog` 检测不可靠——GSC 页面上有别的元素带 role=dialog，会抓到整个应用壳。直接在 `body.innerText` 里找 `Indexing requested` / `Testing if live url` 等状态串。
- ❌ 普通 `querySelectorAll` 找不到按钮——GSC 组件全在 **Shadow DOM** 里。用递归穿透（进入 `el.shadowRoot`，处理 iframe 的 `contentDocument`，深度 20 层足够）+ JS `el.click()`（顺带绕过遮挡检测）。
- 配额：Request indexing 每账号每天约 10-12 个 URL，超出会被拒/限流，批量操作要控制节奏。

## 4. GSC 通用结构（写选择器前先看这个）

- GSC 是 Google 组件化前端：大量元素在 Shadow DOM、jsshadow 组件、material 弹层里。**任何"页面上明明看得见但选择器找不到"的问题，先怀疑 Shadow DOM**，上穿透函数。
- 万能 dump 函数（穿透 shadow + iframe 收集所有短文本 + aria-label），定位阶段先用它摸清结构再写精准选择器。
- 按钮点击用 JS `el.click()`，比 Playwright 原生 click 更耐受遮挡/overlay。
- 顶栏检查框的 aria-label 是动态拼接的：`Inspect any URL in <resource>`，用前缀匹配 `^="Inspect any URL"`。
- property 切换：直接改 URL 的 `resource_id` 参数，不要点资源选择器。
- 英文界面（`&hl=en`）下按本文档的按钮文本匹配；换语言文本会变。

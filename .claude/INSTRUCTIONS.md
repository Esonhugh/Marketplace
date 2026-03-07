# Project Instructions

## 关于此项目

这是一个 **GitHub Copilot / Claude 技能扩展包**，为 AI 编程助手注入 Pydoll 浏览器自动化的专业知识，专注于绕过 Cloudflare WAF 等人机验证系统。

## 技能调用规则

当用户的请求涉及以下任何场景时，**必须**读取并应用 `skills/pydoll-browser/SKILL.md` 中的完整知识：

1. **WAF / 人机验证绕过** — Cloudflare、DataDome、PerimeterX、Akamai 等
2. **浏览器自动化** — 使用 pydoll 进行网页操作
3. **反爬虫检测** — 隐蔽浏览器配置、指纹伪装、人性化交互
4. **网页爬取** — 爬取受保护的网站内容
5. **Shadow DOM 操作** — 访问 closed shadow roots
6. **截图 / PDF 导出** — 绕过保护后进行页面截图

## 代码生成规范

- **始终使用 uv script 格式**：在 Python 文件顶部添加 `# /// script` 内联依赖声明
- **推荐运行方式**：`uv run script.py`（自动安装依赖）
- **默认包名**：`pydoll-python`（不是 `pydoll`）
- **异步优先**：所有 pydoll 操作都是异步的，使用 `asyncio.run(main())`
- **反检测默认启用**：生成代码时默认包含浏览器指纹伪装和 WebRTC 保护
- **服务器环境兼容**：默认添加 `--no-sandbox` 和 `--disable-dev-shm-usage`

## 参考文件

| 文件 | 用途 |
|------|------|
| `skills/pydoll-browser/SKILL.md` | 核心 API 参考和完整用法 |
| `skills/pydoll-browser/knowledge/anti_detection.md` | 反检测深度指南 |
| `skills/pydoll-browser/scripts/templates.py` | 8 个可复用脚本模板 |
| `skills/pydoll-browser/examples/` | 5 个完整示例脚本 |

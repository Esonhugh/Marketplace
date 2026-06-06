---
name: threatbook-intel
description: 微步在线威胁情报查询工具。支持IP、域名、文件哈希威胁情报查询，漏洞情报查询，资产测绘等功能。支持微信登录自动化和X语言高级搜索。当用户需要查询威胁情报、进行资产测绘或使用微步在线平台时，应使用此技能。
---

# 微步情报获取 Skill

## 描述
微步在线（ThreatBook）威胁情报查询工具。支持IP、域名、文件哈希等威胁情报查询，漏洞情报查询，资产测绘等功能。支持微信登录自动化流程。

## 功能
- IP威胁情报查询
- 域名威胁情报查询
- 文件哈希查询
- 漏洞情报查询
- 资产测绘
- XGPT对话
- 微信登录自动化

## 技术实现细节

### 页面URL
- **主页**: `https://x.threatbook.com/`
- **登录页面**: `https://passport.threatbook.cn/login?service=x`
- **微信登录页面**: `https://passport.threatbook.cn/oauth`
- **搜索结果页面**: `https://x.threatbook.com/v5/domain/{domain}`
- **IP查询结果**: `https://x.threatbook.com/v5/ip/{ip}`

### 页面元素定位
- **搜索框**: `textarea.x-searchBar-input` - 页面中央搜索框（注意：是 textarea 不是 input，且页面有两个，需选可见的那个 offsetWidth > 100）
- **搜索确认按钮**: `span.x-searchBar-input-confirm-btn` - 搜索栏右侧放大镜图标（同样有两个，需选可见的）
- **微信登录图标**: `div.wx` - 位于"其他登录方式"和"还没有账号？马上注册"之间
- **隐私协议checkbox**: `span.checkbox` - CSS模拟的checkbox，点击后二维码才能显示
- **登录按钮**: 页面右上角"登录"按钮
- **用户头像**: 登录后显示用户头像

### 完整流程

#### 1. 访问主页并检查登录状态
```
1. 访问 https://x.threatbook.com/
2. 检查是否有"登录"按钮
   - 有"登录"按钮 → 用户未登录
   - 无"登录"按钮，有用户头像 → 用户已登录
```

#### 2. 微信登录流程
```
1. 导航到登录页面：https://passport.threatbook.cn/login?service=x
2. 点击微信登录图标（选择器：.wx）
3. 页面跳转到 /oauth 页面
4. 点击同意隐私协议checkbox（选择器：.checkbox）
5. 二维码显示在iframe中：https://open.weixin.qq.com/connect/qrconnect?appid=wx3ac222f71a76c36a&...
6. 截图二维码发送给用户
7. 等待用户扫码确认
8. 再次截图确认登录状态
```

#### 3. 威胁情报查询流程
```
1. 导航到主页：https://x.threatbook.com/
2. 找到搜索框（ref=e2）
3. 输入查询内容（IP/域名/哈希）
4. 提交搜索（submit=true）
5. 页面跳转到查询结果页面
6. 截图查询结果发送给用户
```

## X语言高级搜索表达式

### 测绘运算逻辑

**连接符**：
- `=` - 匹配，表示查询包含关键词资产
- `==` - 精准匹配，表示仅查询关键词资产
- `!=` - 剔除，表示剔除包含关键词资产
- `()` - 括号内容优先级最高
- `&&` - 代表 and（多条件组合查询）
- `||` - 代表 or（多条件组合查询）

### 资产测绘语法

#### IP相关语法
- **ip** - 检索IPV4及C网段资产（C段范围仅支持/24）
  - 示例：`ip="1.1.1.1"` 或 `ip="1.1.1.1/24"`
  - 支持多IP查询（最多3个），IP间用逗号隔开：`ip="1.1.1.1,8.8.8.8"`
- **ipv6** - 检索单个IPV6
  - 示例：`ipv6="2409:8762:1301::13"`
- **port** - 检索开放特定端口的资产
  - 示例：`port="20"` 或 `port="20,21"`（最多3个端口）
- **asn** - 检索指定asn的资产
  - 示例：`asn="15169"`
- **asn_name** - 检索指定as名称的资产
  - 示例：`asn_name="TRA"`
- **asn_org** - 检索指定as组织的资产
  - 示例：`asn_org="Tanzania Revenue Authority"`
- **ip_type** - 检索IPV6资产
  - `ip_type="false"` - IPV6资产数据
  - `ip_type="true"` - IPV4资产数据
- **rdns** - 检索rdns相关资产
  - 示例：`rdns="dns.google"`

#### 地理位置语法
- **country** - 检索指定国家
  - 示例：`country="中国"`
- **region** - 检索指定省分/区域
  - 示例：`region="辽宁"`
- **city** - 检索指定城市
  - 示例：`city="大连"`
- **district** - 检索地区资产
  - 示例：`district="海淀区"`

#### 网络相关语法
- **isp** - 检索指定运营商
  - 示例：`isp="中国联通"`
- **host** - 检索指定主机名
  - 示例：`host="localhost"`
- **os** - 检索指定操作系统及版本
  - 示例：`os="windows"`
- **owner** - 检索IP地址所属组织拥有者
  - 示例：`owner="阿里云"`

### 关键词运算逻辑

**运算符**：
- `""` - 双引号，精确匹配
  - 示例：`intext="海莲花"`
- `&&` - 必须同时包含两个语法下的关键词
  - 示例：`intitle=报告 && intext=APT`
- **注意**：关键词和运算符 "&&" 间需输入空格

### 关键词查询语法

- **intitle** - 搜索标题含特定关键词的内容
  - 示例：`intitle=微步`
- **intext** - 搜索正文包含特定关键词的内容
  - 示例：`intext=海莲花`
- **x** - 在社区内容中搜索包含特定关键词的内容
  - 示例：`x=溯源`
- **blog** - 在相关博客中搜索包含特定关键词的内容
  - 示例：`blog=APT`
- **smedia** - 在社交媒体结果中搜索包含特定关键词的内容
  - 示例：`smedia=蜜罐`

### 组合查询示例

```
# 资产测绘组合查询
ip="1.1.1.1" && port="80"
country="中国" && city="北京" && port="443"
asn="15169" && os="linux"

# 关键词组合查询
intitle=报告 && intext=APT
blog=溯源 && intext=威胁情报
```

## 使用方法

### 1. 查询威胁情报
```
查询IP: 8.8.8.8 的威胁情报
查询域名: example.com 的威胁情报
查询文件哈希: abc123... 的威胁情报
```

### 2. 使用X语言搜索
```
# 资产测绘搜索
ip="1.1.1.1" && port="80"
country="中国" && city="北京"

# 关键词搜索
intitle=报告 && intext=APT
blog=溯源 && intext=威胁情报
```

### 2. 微信登录流程示例
```
用户: 查询 nscc-tj.cn 的威胁情报
助手: 我会访问微步在线查询 nscc-tj.cn 的威胁情报。检测到您未登录，需要先登录账号。

助手: [导航到登录页面]
助手: [点击微信登录图标]
助手: [点击同意隐私协议]
助手: [截图二维码并发送] 请使用微信扫描二维码登录

用户: 完成扫描
助手: [再次截图确认登录状态]

用户: 是的已经完成登陆
助手: [访问主页]
助手: [在搜索框输入 nscc-tj.cn 并提交]
助手: [截图查询结果并发送] 查询完成！这是 nscc-tj.cn 的威胁情报信息
```

## 脚本使用（pydoll + uv）

脚本位于 `scripts/threatbook_query.py`，使用 pydoll 库实现浏览器自动化，通过 uv 直接运行（自动安装依赖）。

### 运行方式
```bash
# 查询 IP 威胁情报
uv run scripts/threatbook_query.py -q 8.8.8.8

# 查询域名
uv run scripts/threatbook_query.py -q example.com

# 查询文件哈希
uv run scripts/threatbook_query.py -q abc123...

# X语言资产测绘搜索
uv run scripts/threatbook_query.py -q 'ip="1.1.1.1" && port="80"'

# 复杂组合查询
uv run scripts/threatbook_query.py -q 'country="中国" && city="北京" && port="443"'

# 输出结果到 JSON 文件
uv run scripts/threatbook_query.py -q 8.8.8.8 -o result.json
```

### 关键特性
- **搜索框交互**: 通过 textarea 搜索框输入内容，点击确认按钮提交，支持任意查询格式
- **自动登录检测**: 先检测登录状态，已登录直接搜索，未登录自动走微信扫码流程
- **登录状态持续监测**: 自动检测用户是否完成扫码，登录成功后自动开始搜索
- **headless=False**: 非无头模式运行，更好地绕过反爬检测
- **Cloudflare 自动绕过**: 使用 pydoll 内置的 Cloudflare captcha 绕过
- **人性化模拟**: 随机延迟、模拟滚动，降低被识别为机器人的概率
- **反检测配置**: 伪造浏览器配置、WebRTC 泄露保护

## 依赖
- uv（Python 包管理器，自动安装 pydoll-python）
- Chrome 浏览器
- 微信账号（用于微信登录）
- 微步在线账号（如需登录）

## 注意事项

### 微信登录注意事项
1. **隐私协议必须先点击**: 二维码初始状态是模糊的，有"请先同意隐私协议"覆盖在二维码上，必须先点击checkbox才能显示清晰的二维码
2. **截图不要等待过久**: 获取二维码后立即截图并发送给用户，避免二维码过期
3. **登录确认**: 用户扫码后，需要再次截图确认登录状态
4. **微信登录图标位置**: 在"其他登录方式"和"还没有账号？马上注册"之间

### 搜索注意事项
1. **搜索框ref**: 使用ref=e2定位搜索框
2. **提交方式**: 使用submit=true自动提交搜索
3. **URL格式**: 
   - 域名查询：/v5/domain/{domain}
   - IP查询：/v5/ip/{ip}
   - 文件哈希：/v5/file/{hash}

### 登录状态保持
- 登录状态通过cookie保持
- 如果cookie失效，需要重新登录
- 建议在查询前检查登录状态

## 示例

### 示例1：域名威胁情报查询（微信登录）
```
用户: 查询 nscc-tj.cn 的威胁情报
助手: 我会访问微步在线查询 nscc-tj.cn 的威胁情报。检测到您未登录，需要先登录账号。我为您准备了微信登录二维码，请扫描登录。
[发送登录页面截图]

用户: 完成扫描
助手: 好的，让我确认一下登录状态。
[再次截图确认]

用户: 是的已经完成登陆
助手: 登录成功！现在查询 nscc-tj.cn 的威胁情报...
[显示查询结果]
```

### 示例2：IP威胁情报查询（已登录）
```
用户: 查询 8.8.8.8 的威胁情报
助手: 我会访问微步在线查询 8.8.8.8 的威胁情报。
[访问主页]
[在搜索框输入 8.8.8.8 并提交]
[显示查询结果]
```

## 数据来源
- 微步在线（https://x.threatbook.com/）
- 威胁情报数据库
- 漏洞情报数据库
- 资产测绘数据库

## 相关链接
- 官网: https://x.threatbook.com/
- API文档: https://x.threatbook.com/v5/apiDoc
- 登录页面: https://passport.threatbook.cn/login

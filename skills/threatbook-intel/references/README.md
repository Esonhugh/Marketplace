# 微步情报获取 Skill

## 简介
微步在线（ThreatBook）威胁情报查询工具，支持IP、域名、文件哈希等威胁情报查询。支持微信登录自动化流程。

## 功能特性
- ✅ IP威胁情报查询
- ✅ 域名威胁情报查询
- ✅ 文件哈希查询
- ✅ 漏洞情报查询
- ✅ 资产测绘
- ✅ XGPT对话
- ✅ 微信登录自动化（推荐）
- ✅ APP扫码登录
- ✅ 密码登录
- ✅ 短信登录

## 技术实现

### 页面URL
- 主页: https://x.threatbook.com/
- 登录页面: https://passport.threatbook.cn/login?service=x
- 微信登录页面: https://passport.threatbook.cn/oauth
- 域名查询结果: https://x.threatbook.com/v5/domain/{domain}
- IP查询结果: https://x.threatbook.com/v5/ip/{ip}

### 页面元素定位
- 搜索框: `textbox [ref=e2]`
- 微信登录图标: `div.wx`
- 隐私协议checkbox: `span.checkbox`
- 微信二维码iframe: `https://open.weixin.qq.com/connect/qrconnect?appid=wx3ac222f71a76c36a&...`

### 微信登录流程
1. 导航到登录页面
2. 点击微信登录图标（`.wx`）
3. 点击同意隐私协议checkbox（`.checkbox`）
4. 二维码显示在iframe中
5. 截图发送给用户
6. 用户扫码登录
7. 确认登录状态

## X语言高级搜索表达式

微步在线提供强大的X语言搜索功能，支持资产测绘和关键词查询。

### 测绘运算逻辑

**连接符**：
- `=` - 匹配，表示查询包含关键词资产
- `==` - 精准匹配，表示仅查询关键词资产
- `!=` - 剔除，表示剔除包含关键词资产
- `()` - 括号内容优先级最高
- `&&` - 代表 and（多条件组合查询）
- `||` - 代表 or（多条件组合查询）

### 资产测绘语法

#### IP相关
- `ip="1.1.1.1"` - 检索IPV4及C网段资产
- `ip="1.1.1.1,8.8.8.8"` - 支持多IP查询（最多3个）
- `ipv6="2409:8762:1301::13"` - 检索单个IPV6
- `port="80"` - 检索开放特定端口的资产
- `port="80,443"` - 支持多端口查询（最多3个）
- `asn="15169"` - 检索指定asn的资产
- `asn_name="TRA"` - 检索指定as名称的资产
- `asn_org="Tanzania Revenue Authority"` - 检索指定as组织的资产
- `ip_type="false"` - 检索IPV6资产（false=IPV6, true=IPV4）
- `rdns="dns.google"` - 检索rdns相关资产

#### 地理位置
- `country="中国"` - 检索指定国家
- `region="辽宁"` - 检索指定省分/区域
- `city="大连"` - 检索指定城市
- `district="海淀区"` - 检索地区资产

#### 网络
- `isp="中国联通"` - 检索指定运营商
- `host="localhost"` - 检索指定主机名
- `os="windows"` - 检索指定操作系统及版本
- `owner="阿里云"` - 检索IP地址所属组织拥有者

### 关键词查询语法

**运算符**：
- `""` - 双引号，精确匹配
  - 示例：`intext="海莲花"`
- `&&` - 必须同时包含两个语法下的关键词
  - 示例：`intitle=报告 && intext=APT`
- **注意**：关键词和运算符 "&&" 间需输入空格

**语法**：
- `intitle=微步` - 搜索标题含特定关键词的内容
- `intext=海莲花` - 搜索正文包含特定关键词的内容
- `x=溯源` - 在社区内容中搜索包含特定关键词的内容
- `blog=APT` - 在相关博客中搜索包含特定关键词的内容
- `smedia=蜜罐` - 在社交媒体结果中搜索包含特定关键词的内容

### 组合查询示例

```bash
# 资产测绘组合查询
ip="1.1.1.1" && port="80"
country="中国" && city="北京" && port="443"
asn="15169" && os="linux"

# 关键词组合查询
intitle=报告 && intext=APT
blog=溯源 && intext=威胁情报
```

## 安装
```bash
# 安装到OpenClaw skills目录
cd ~/.openclaw/skills
git clone <skill-repo-url> threatbook-intel
```

## 使用方法

### 1. 查询威胁情报
```bash
# 查询IP
python threatbook_query.py --query 8.8.8.8 --type ip

# 查询域名
python threatbook_query.py --query example.com --type domain

# 查询文件哈希
python threatbook_query.py --query abc123... --type hash
```

### 2. 微信登录流程（推荐）
微信登录是最方便的登录方式，支持自动化流程：

```
用户: 查询 nscc-tj.cn 的威胁情报
助手: 我会访问微步在线查询。检测到您未登录，需要先登录账号。
助手: [导航到登录页面]
助手: [点击微信登录图标]
助手: [点击同意隐私协议]
助手: [截图二维码并发送] 请使用微信扫描二维码登录

用户: 完成扫描
助手: [再次截图确认登录状态]

用户: 是的已经完成登陆
助手: [访问主页]
助手: [在搜索框输入 nscc-tj.cn 并提交]
助手: [截图查询结果并发送] 查询完成！
```

### 3. APP扫码登录
```bash
python threatbook_query.py --query 8.8.8.8 --login app
```
然后使用微步情报社区APP扫描二维码登录。

### 4. 密码登录
```bash
python threatbook_query.py --query 8.8.8.8 --login password --username your_username --password your_password
```

### 5. 在OpenClaw中使用
```
用户: 查询 8.8.8.8 的威胁情报
助手: 我会访问微步在线查询 8.8.8.8 的威胁情报。
[执行查询]

如果需要登录:
助手: 需要登录才能查询，我会为您准备微信登录二维码，请扫描登录。
[导航到登录页面]
[点击微信登录]
[截图二维码发送]

用户: 完成扫描
助手: 登录成功！现在查询 8.8.8.8 的威胁情报...
[显示查询结果]
```

## 微信登录注意事项

### 关键步骤
1. **隐私协议必须先点击**: 二维码初始状态是模糊的，有"请先同意隐私协议"覆盖，必须先点击checkbox才能显示清晰的二维码
2. **截图不要等待过久**: 获取二维码后立即截图发送，避免二维码过期
3. **登录确认**: 用户扫码后，需要再次截图确认登录状态
4. **微信登录图标位置**: 在"其他登录方式"和"还没有账号？马上注册"之间

### 自动化实现
使用browser工具实现微信登录自动化：
```javascript
// 点击微信登录图标
document.querySelector('.wx').click();

// 点击同意隐私协议checkbox
document.querySelector('.checkbox').click();

// 检查登录状态
const hasLoginButton = Array.from(document.querySelectorAll('button, a')).some(el => el.textContent.includes('登录'));
return { isLoggedIn: !hasLoginButton };
```

## 注意事项
1. ✅ **支持微信登录**: 登录页面有微信登录选项，位于"其他登录方式"区域
2. 首次使用需要登录微步在线账号
3. 查询频率可能受限，请合理使用
4. 推荐使用微信登录，更方便快捷
5. 登录状态通过cookie保持，失效后需重新登录

## 依赖
- Python 3.7+
- browser工具（OpenClaw内置）
- 微步在线账号（可选）
- 微信账号（用于微信登录）

## 数据来源
- 微步在线（https://x.threatbook.com/）
- 威胁情报数据库
- 漏洞情报数据库
- 资产测绘数据库

## 相关链接
- 官网: https://x.threatbook.com/
- API文档: https://x.threatbook.com/v5/apiDoc
- 登录页面: https://passport.threatbook.cn/login

## 许可证
MIT License

## 作者
OpenClaw Team

## 更新日志
- 2026-03-20: 初始版本，支持基础查询和登录功能
- 2026-03-20: 新增微信登录自动化流程，支持完整的威胁情报查询流程

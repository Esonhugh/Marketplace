# fofa-intel

Claude Code 的 FOFA 网络空间搜索引擎插件。通过预编译的多平台 GoFOFA CLI 二进制，提供资产测绘、威胁情报查询和批量数据导出能力。

## 功能

- **资产测绘** — 按域名、IP、端口、证书、Banner、协议搜索
- **批量导出** — 用 `dump` 子命令导出百万级记录
- **主机画像** — 用 `host` 查看完整资产详情
- **统计分析** — 用 `stats` 做分布统计
- **域名枚举** — 用 `domains` 发现子域名
- **多平台支持** — 内置 macOS（ARM/x86）、Linux、Windows 预编译二进制，运行时自动选择

## 前置条件

- FOFA 账号及 API Key — 登录 [fofa.info](https://fofa.info) → 个人中心 → API Key
- 已安装 Claude Code

`bin/` 目录由 Claude Code 自动添加到 PATH，无需手动配置。

## 安装

```bash
/plugin install fofa-intel@Esonhugh/Marketplace
```

## 配置

持久化保存 FOFA API Key（重启会话后依然有效）：

```bash
mkdir -p ~/.config/gofofa
echo "FOFA_KEY=your_key_here" > ~/.config/gofofa/.env
chmod 600 ~/.config/gofofa/.env
```

或仅当前会话临时使用：

```bash
export FOFA_KEY=your_key_here
```

## 使用

用自然语言描述需求即可触发 Skill：

```
用 FOFA 查询 example.com 的资产
查找 IP 1.2.3.4 的开放端口
导出 cert.example.com 关联的 FOFA 数据
统计 country=CN 且 port=443 的资产分布
```

## CLI 速查

安装插件后，`fofa` 命令在所有 Bash 工具调用中均可直接使用：

```bash
# 域名资产查询
fofa search -f ip,port,host,title,server -s 200 --format=json 'domain="target.com"'

# IP 反查
fofa search -f host,domain,title,server,port -s 100 --format=json 'ip="1.2.3.4"'

# 证书关联
fofa search -f host,ip,port,cert -s 100 --format=json 'cert="target.com"'

# 批量导出到 CSV
fofa dump -f ip,port,host,protocol -bs 1000 -s 50000 -o assets.csv 'domain="target.com"'

# 主机详情
fofa host target.com

# 结果计数
fofa count 'domain="target.com"'

# 账户信息
fofa account
```

## 内置二进制

| 平台 | 二进制文件 |
|------|-----------|
| macOS ARM64 | `bin/fofa-darwin-arm64` |
| macOS x86_64 | `bin/fofa-darwin-amd64` |
| Linux x86_64 | `bin/fofa-linux-amd64` |
| Windows x86_64 | `bin/fofa-windows-amd64.exe` |

`bin/fofa` 是 shell 包装脚本，通过 `uname` 自动选择正确的平台二进制。

## 注意事项

- FOFA 查询消耗 F 点，大批量导出前确认配额
- `cert` / `banner` 字段每页上限 2000 条
- `body` 字段每页上限 500 条
- 建议用 `--format=json` 便于程序解析，文件导出用 CSV

## 许可证

MIT — 作者：Esonhugh

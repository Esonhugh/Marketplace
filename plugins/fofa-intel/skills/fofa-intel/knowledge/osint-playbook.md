# FOFA OSINT 联动 Playbook

## 概述

fofa-intel 可独立使用，也可与 skysight-pro 的 OSINT 流程无缝联动。
联动方式为**松耦合**：通过 CLI PATH 可达性 + Skill 工具双入口。

## 独立使用

用户在主会话中提到 FOFA/资产测绘/网络空间搜索时，通过 Skill 触发 fofa-intel。
Skill 会引导完成：环境检查 → Key 验证 → 构造查询 → 执行 → 输出结果。

## 与 skysight-pro 联动

### 前置条件
1. fofa-intel 和 skysight-pro 两个 plugin 均已安装
2. `fofa` 命令在 PATH 中可用（由 SessionStart hook 自动注入）
3. `FOFA_KEY` 环境变量已设置

### 联动触发场景

#### 场景 1：osint-recon 域名侦察
```
osint-recon 收到域名侦察任务
→ Skill: fofa-intel（如果 Skill 工具可用）
   或 Bash: fofa search -f ip,port,host,title,server --format=json 'domain="target.com"'
→ 结果融入 OSINT 侦察报告
```

#### 场景 2：osint-recon + chrome-devtools 补充查询
```
CLI 查询完成后，需要查看更多详情
→ 检测 chrome-devtools MCP 是否可用
→ 如果可用：
   1. navigate_page: https://fofa.info/result?qbase64={base64编码的查询}
   2. take_snapshot 获取页面完整结果
   3. 从页面提取 CLI 无法获取的会员数据
```

#### 场景 3：IP 资产发现
```
溯源过程中发现可疑 IP
→ fofa search -f ip,port,host,title,protocol,server --format=json 'ip="x.x.x.x"'
→ 发现同 IP 下的其他服务和域名
```

#### 场景 4：证书关联
```
通过 SSL 证书关联相关资产
→ fofa search -f host,ip,port,cert --format=json 'cert="target.com"'
→ 找到使用相同证书的所有主机
```

#### 场景 5：批量资产导出
```
需要大规模数据
→ fofa dump -f ip,port,host,protocol -bs 1000 -s 50000 -o assets.csv 'domain="target.com"'
→ 后续在本地分析 CSV 数据
```

### 常用 OSINT 查询模板

```bash
# 域名全资产
fofa search -f ip,port,host,title,server,protocol,lastupdatetime -s 500 --format=json 'domain="TARGET"'

# IP 反查
fofa search -f host,domain,title,server,port -s 100 --format=json 'ip="TARGET_IP"'

# 同证书资产
fofa search -f host,ip,port -s 100 --format=json 'cert="TARGET_DOMAIN"'

# C 段扫描
fofa search -f ip,port,host,title -s 500 --format=json 'ip="1.2.3.0/24"'

# 图标哈希关联（同类站点发现）
fofa search -f host,ip,title -s 100 --format=json 'icon_hash="HASH_VALUE"'

# 特定组件资产
fofa search -f host,ip,port,title -s 200 --format=json 'server="nginx" && domain="TARGET"'

# 统计概览
fofa stats -f country,city,port,protocol,server 'domain="TARGET"'
```

### chrome-devtools 浏览器查询

当 CLI 结果不够或需要可视化时，通过 chrome-devtools MCP 打开 FOFA 网页：

```
# 构造 FOFA 搜索 URL
https://fofa.info/result?qbase64={base64(query)}

# 流程：
1. navigate_page → FOFA 搜索结果页
2. take_snapshot → 获取页面结构
3. 提取结果数据（表格、统计信息）
4. 如需登录 → 通过 fill + click 完成登录流程
```

## FOFA_KEY 管理

```bash
# 检查 key
echo $FOFA_KEY

# 设置 key（临时）
export FOFA_KEY='your_key_here'

# 持久化存储
mkdir -p ~/.config/gofofa
echo 'FOFA_KEY=your_key_here' > ~/.config/gofofa/.env

# 验证
fofa account
```

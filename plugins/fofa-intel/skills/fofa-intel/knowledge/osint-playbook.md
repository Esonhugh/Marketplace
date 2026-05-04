# FOFA OSINT 查询 Playbook

## 典型查询场景

### 域名资产侦察

```bash
# 基础域名资产
fofa search -f ip,port,host,title,server,protocol -s 200 --format=json 'domain="target.com"'

# 子域名枚举
fofa domains -s 500 'domain="target.com"'

# 证书关联（扩大资产范围）
fofa search -f host,ip,port,cert -s 100 --format=json 'cert="target.com"'
```

### IP 反查与关联分析

```bash
# 单 IP 反查
fofa search -f host,domain,title,server,port -s 100 --format=json 'ip="1.2.3.4"'

# C 段资产扫描
fofa search -f ip,port,host,title -s 500 --format=json 'ip="1.2.3.0/24"'

# 主机详情（含 banner、端口、组织等）
fofa host 1.2.3.4
```

### 组件与服务识别

```bash
# 特定服务识别
fofa search -f ip,port,host,title -s 100 --format=json 'server="nginx" && domain="target.com"'

# 暴露管理面板
fofa search -f ip,port,host,title -s 100 --format=json 'title="admin" && domain="target.com"'

# 按协议筛选
fofa search -f ip,port,host -s 100 --format=json 'protocol="rdp" && domain="target.com"'
```

### 统计与分布分析

```bash
# 资产分布统计
fofa stats -f country,port,server 'domain="target.com"'

# 结果计数（快速确认规模）
fofa count 'domain="target.com"'
```

### 批量导出

```bash
# 大批量资产导出（CSV）
fofa dump -f ip,port,host,title,protocol -bs 1000 -s 50000 \
    -o assets.csv 'domain="target.com"'
```

## 查询结构化输出示例

```bash
fofa search -f ip,port,host,title,server,protocol,lastupdatetime \
    -s 200 --format=json 'domain="target.com"' \
    | python3 -c "
import json, sys
data = json.load(sys.stdin)
for item in data.get('results', []):
    print('\t'.join(str(v) for v in item))
"
```

## 有价值的发现特征

查询结果中重点关注：

- **异常端口**：非标准高位端口（>10000）且有 HTTP 服务
- **同 IP 多域名**：可能揭示共享基础设施
- **过期证书**：`cert.not_after` 早于当前日期
- **已知框架**：`server` 字段含 Apache Struts、WebLogic、Jenkins 等
- **管理接口**：title 含 "login"、"admin"、"dashboard"、"管理"

## 注意事项

- 查询消耗 F 点（F-Point），`fofa account` 可查当前余额
- `cert`/`banner` 字段每页上限 2000，`body` 字段每页上限 500
- 建议先用 `count` 确认数量，再决定是否 `dump`

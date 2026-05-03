# FOFA 查询语法速查

## 基础查询

| 语法 | 说明 | 示例 |
|------|------|------|
| `domain="x.com"` | 搜索域名 | `domain="baidu.com"` |
| `ip="1.2.3.4"` | 搜索 IP | `ip="1.1.1.1"` |
| `host="x.com"` | 搜索主机 | `host="www.baidu.com"` |
| `port="443"` | 搜索端口 | `port="8080"` |
| `protocol="https"` | 搜索协议 | `protocol="ssh"` |
| `city="Beijing"` | 搜索城市 | `city="Shanghai"` |
| `country="CN"` | 搜索国家 | `country="US"` |
| `region="Guangdong"` | 搜索省份 | `region="Zhejiang"` |
| `org="Alibaba"` | 搜索组织 | `org="Tencent"` |
| `asn="13335"` | 搜索 ASN | `asn="4134"` |

## 高级查询

| 语法 | 说明 | 示例 |
|------|------|------|
| `title="后台"` | 搜索网页标题 | `title="管理系统"` |
| `header="nginx"` | 搜索响应头 | `header="Apache"` |
| `body="keyword"` | 搜索网页内容 | `body="login"` |
| `cert="xxx"` | 搜索证书信息 | `cert="baidu.com"` |
| `cert.subject="CN=x"` | 证书主题 | `cert.subject="*.baidu.com"` |
| `cert.issuer="Let's Encrypt"` | 证书签发者 | `cert.issuer="DigiCert"` |
| `banner="SSH"` | 搜索 Banner | `banner="MySQL"` |
| `server="nginx"` | 搜索 Server | `server="Apache/2.4"` |
| `icon_hash="xxx"` | 搜索图标哈希 | `icon_hash="-247388890"` |
| `js_name="app.js"` | 搜索 JS 文件名 | `js_name="jquery"` |
| `js_md5="xxx"` | 搜索 JS 文件哈希 | |
| `fid="xxx"` | FOFA 聚合ID | |

## 逻辑运算

| 运算 | 说明 | 示例 |
|------|------|------|
| `&&` | AND | `domain="baidu.com" && port="443"` |
| `\|\|` | OR | `port="80" \|\| port="443"` |
| `!=` | NOT | `protocol!="http"` |
| `()` | 分组 | `(port="80" \|\| port="443") && country="CN"` |

## 时间过滤

| 语法 | 说明 | 示例 |
|------|------|------|
| `after="2024-01-01"` | 更新时间之后 | `domain="x.com" && after="2024-06-01"` |
| `before="2024-12-31"` | 更新时间之前 | `ip="1.1.1.1" && before="2024-01-01"` |

## GoFOFA CLI 常用命令

### search — 标准查询
```bash
fofa search -f ip,port,host,title,server -s 100 --format=json 'domain="target.com"'
```

| 参数 | 短写 | 默认 | 说明 |
|------|------|------|------|
| `-f fields` | `-f` | `ip,port` | 返回字段 |
| `--format` | | `csv` | 输出格式: csv/json/xml |
| `-s size` | `-s` | `100` | 结果数量（最大10000） |
| `-o outFile` | `-o` | | 输出文件 |
| `--full` | | `false` | 获取完整（非截断）数据 |
| `--uniqByIP` | | `false` | 按 IP 去重 |
| `--headline` | | `false` | 输出 CSV 表头 |
| `--fixUrl` | | `false` | 组合 IP+端口为 URL |

### dump — 大批量导出
```bash
fofa dump -f ip,port,host,protocol -bs 1000 -s 50000 -o data.csv 'domain="target.com"'
```

### host — 主机信息
```bash
fofa host target.com
```

### stats — 统计聚合
```bash
fofa stats -f title,country -s 10 'domain="target.com"'
```

### count — 结果计数
```bash
fofa count 'domain="target.com"'
```

### domains — 域名查询
```bash
fofa domains -s 100 --withCount 'domain="target.com"'
```

## 常用可返回字段

`ip`, `port`, `host`, `domain`, `title`, `server`, `header`, `protocol`, `banner`, `cert`, `country`, `city`, `region`, `org`, `asn`, `os`, `lastupdatetime`, `link`, `product`, `product_category`

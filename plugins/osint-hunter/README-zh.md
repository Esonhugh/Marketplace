# OSINT Hunter — 统一网络威胁情报分析

Claude Code 插件，聚合多源网络威胁情报（FOFA、VirusTotal、AbuseIPDB、OTX 等），提供统一的 IOC 查询和调查工作流。

## 功能

- **IOC 富化查询**：输入任意 IOC（IP/域名/哈希/URL/邮箱），自动查询所有已配置数据源并聚合输出
- **资产测绘**：基于 FOFA 的互联网资产发现和侦察
- **多引擎检测**：VirusTotal 集成，支持文件/URL/IP/域名分析
- **优雅降级**：根据已配置的 API Key 自动选择可用数据源，跳过未配置的

## 安装

```bash
claude plugin install osint-hunter
```

首次启用时会提示配置 API Key。

## 使用

```
/osint-hunter:enrich-ioc 8.8.8.8
/osint-hunter:enrich-ioc evil-domain.com
/osint-hunter:enrich-ioc d41d8cd98f00b204e9800998ecf8427e
```

## 许可证

MIT

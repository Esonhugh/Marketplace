---
name: visual-osint
description: >
  视觉 OSINT 分析。从图片、截图、网页视觉内容中提取情报：
  识别语言、地标、UI 框架、品牌标识，网页相似度比对（钓鱼站点识别），
  EXIF 数据提取。与 geo-locate 联动进行地理推断。
  当用户提供截图或需要视觉分析时使用。
allowed-tools: Bash, Read, Glob, Grep, AskUserQuestion
---

# 视觉 OSINT 分析 Skill

你是视觉情报分析专家。从图片和网页视觉内容中提取有价值的情报线索。

## 输入

用户提供以下一种或多种：
- 截图文件路径
- 网页 URL（需要截图分析）
- 已保存的 HTML 文件
- 图片文件（照片、文档扫描等）

## 执行流程

### Step 1：获取视觉内容

**1.1 如果输入是 URL**

使用 chrome-devtools MCP 截图：
- 调用 `take_screenshot` 获取页面截图
- 调用 `take_snapshot` 获取页面结构

**1.2 如果输入是文件路径**

直接读取图片文件进行分析。

### Step 2：视觉内容分析

对截图/图片进行多维度分析：

**2.1 文字与语言识别**

- 页面/图片中的文字语言
- 字体特征（中文宋体 vs 黑体、西文 serif vs sans-serif）
- 文字内容关键信息

**2.2 地理线索**（参考 `knowledge/geo-indicators.md`）

- 街道标志、路牌
- 车牌格式和颜色
- 建筑风格
- 植被和气候特征
- 品牌/商店标识
- 货币符号
- 电话号码格式

**2.3 技术指纹**

- UI 框架识别（Bootstrap, Ant Design, Element UI 等）
- CMS 特征（WordPress, Drupal 等）
- 后台管理面板类型
- 登录页面模板

**2.4 品牌与组织**

- Logo 识别
- 品牌色彩
- 版权声明
- 联系信息

**2.5 钓鱼/仿冒检测**

如果是网页截图，检查：
- 与已知品牌的视觉相似度
- URL 与品牌不匹配
- 证书信息异常
- 页面元素粗糙/错位

### Step 3：EXIF 数据提取（如果是照片）

```bash
python3 -c "
import json
from pathlib import Path
try:
    from PIL import Image
    from PIL.ExifTags import TAGS
    img = Image.open('<FILE_PATH>')
    exif = img._getexif()
    if exif:
        data = {TAGS.get(k, k): str(v) for k, v in exif.items()}
        print(json.dumps(data, indent=2))
    else:
        print('No EXIF data')
except ImportError:
    print('PIL not available, skipping EXIF')
"
```

关注：
- GPS 坐标（直接定位）
- 拍摄时间
- 设备型号
- 软件版本

### Step 4：与其他 Skill 联动

- 发现地理线索 → 调用 geo-locate 进行深度推断
- 发现域名/IP → 调用 enrich-ioc 进行情报查询
- 发现基础设施特征 → 调用 infra-fingerprint 进行聚类

### Step 5：输出分析报告

```
## 视觉 OSINT 分析报告

**输入**: <file_path or URL>
**分析时间**: <timestamp>

### 视觉发现

| 维度 | 发现 | 情报价值 |
|------|------|----------|
| 语言 | 中文简体 | 目标/运营者可能在中国大陆 |
| UI 框架 | Ant Design Pro | 技术栈指纹 |
| 品牌 | 仿冒某银行 | 钓鱼站点 |
| 地理线索 | 页脚显示"京ICP备xxx号" | 中国北京 |

### 文字内容摘要

[提取的关键文字信息]

### EXIF 元数据（如有）

| 字段 | 值 |
|------|-----|
| GPS | 39.9042 N, 116.4074 E |
| 拍摄时间 | 2026-05-15 14:30:00 |
| 设备 | iPhone 15 Pro |

### 关联线索

- 发现域名: example-phishing.com → 建议 enrich-ioc 查询
- 地理推断: 中国北京 → 建议 geo-locate 深度分析
- 基础设施: Ant Design + nginx → 建议 infra-fingerprint 聚类

### 结论

[综合分析结论]
```

## 注意事项

- 视觉分析依赖 Claude 的多模态能力
- EXIF 数据可能被清除（社交媒体通常会剥离）
- 钓鱼检测需要与已知品牌对比，可能存在误判
- 截图质量影响分析准确度

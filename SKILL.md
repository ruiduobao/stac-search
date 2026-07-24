---
name: stac-search
description: STAC Universal Search Tool for searching geospatial data across any STAC endpoint.
version: 0.1.0
license: MIT-0
---

# STAC Universal Search

Search any SpatioTemporal Asset Catalog (STAC) endpoint for geospatial data.

## Features

- Pre-configured endpoints: Planetary Computer, AWS Earth Search, Element84, Google Earth Engine
- Custom endpoint support
- Collection, bbox, date range, cloud cover filters
- Text table or JSON output
- Asset listing and collection info

## Usage

```bash
# Search with preset
python stac-search.py --preset planetary-computer --collection sentinel-2-l2a --bbox 120 30 121 31

# Search custom endpoint
python stac-search.py --endpoint https://earth-search.aws.element84.com/v1 --collection sentinel-2-l2a --limit 5

# List collections
python stac-search.py --list-collections --preset aws-earth-search

# Get collection info
python stac-search.py --collection-info sentinel-2-l2a --preset planetary-computer

# With filters
python stac-search.py --preset planetary-computer --collection landsat-c2-l2 --bbox -122.5 37.5 -122.0 38.0 --datetime 2024-01-01/2024-06-30 --max-cloud-cover 20 --limit 5

# JSON output
python stac-search.py --preset planetary-computer --collection sentinel-2-l2a --json

# List assets
python stac-search.py --preset planetary-computer --collection sentinel-2-l2a --list-assets
```

## Arguments

| Argument | Description |
|----------|-------------|
| `--preset` | Use a preset: planetary-computer, aws-earth-search, element84, gee |
| `--endpoint` | Custom STAC endpoint URL |
| `--collection` | Collection ID(s) to search |
| `--bbox` | Bounding box: minx miny maxx maxy |
| `--datetime` | Date range: 2024-01-01/2024-12-31 |
| `--max-cloud-cover` | Max cloud cover % |
| `--limit` | Max results (default: 10) |
| `--json` | Output as JSON |
| `--verbose` | Show asset details |
| `--list-assets` | List assets for first result |
| `--list-collections` | List available collections |
| `--collection-info` | Get info for a collection |

## Installation

```bash
pip install requests
```

---

## 中文说明

通用 STAC 搜索工具，支持在任何 STAC 端点搜索地理空间数据。

### 特性

- **预配置端点**：Planetary Computer、AWS Earth Search、Element84、Google Earth Engine
- **自定义端点**：支持任意 STAC API
- **过滤条件**：集合、边界框、日期范围、云量
- **输出格式**：文本表格或 JSON

### 使用方法

```bash
# 使用预设搜索
python stac-search.py --preset planetary-computer --collection sentinel-2-l2a --bbox 120 30 121 31

# 搜索自定义端点
python stac-search.py --endpoint https://earth-search.aws.element84.com/v1 --collection sentinel-2-l2a --limit 5

# 列出所有集合
python stac-search.py --list-collections --preset aws-earth-search

# 获取集合信息
python stac-search.py --collection-info sentinel-2-l2a --preset planetary-computer

# 带过滤条件
python stac-search.py --preset planetary-computer --collection landsat-c2-l2 --bbox -122.5 37.5 -122.0 38.0 --datetime 2024-01-01/2024-06-30 --max-cloud-cover 20 --limit 5

# JSON 输出
python stac-search.py --preset planetary-computer --collection sentinel-2-l2a --json

# 列出资产
python stac-search.py --preset planetary-computer --collection sentinel-2-l2a --list-assets
```

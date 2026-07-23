# STAC Universal Search · STAC 通用搜索器

> 统一 STAC 搜索入口，支持任意 STAC 端点。
> 预置 Planetary Computer、AWS Earth Search、Element84 等主流后端。
> MIT-0 开源。

[English](#quickstart) | 中文

## 为什么做做这个

STAC (SpatioTemporal Asset Catalog) 是遥感数据的开放标准索引协议。
不同数据源有不同的 STAC 端点，用户需要记住每个 URL。本 skill
提供统一的搜索接口，预置主流端点，也支持自定义。

## Quickstart / 快速开始

```bash
# 安装依赖
pip install 'requests>=2.28.0'

# 搜索 Landsat 影像
python stac-search.py \
    --collection landsat-c2-l2 \
    --bbox 116.0 39.0 117.0 40.0 \
    --datetime 2024-01-01/2024-12-31 \
    --cloud-cover 20

# 搜索 Sentinel-2 影像
python stac-search.py \
    --preset pc \
    --collection sentinel-2-l2a \
    --bbox 116.0 39.0 117.0 40.0 \
    --datetime 2024-06-01/2024-06-30

# 使用自定义端点
python stac-search.py \
    --endpoint https://custom-stac.example.com/v1/search \
    --collection my-collection \
    --bbox 116.0 39.0 117.0 40.0

# 列出集合资产
python stac-search.py \
    --collection landsat-c2-l2 \
    --list-assets
```

## 预置端点 / Preset Endpoints

| 预置名 | 端点 | 说明 |
|---|---|---|
| `pc`（默认） | `https://planetarycomputer.microsoft.com/api/stac/v1/` | Microsoft Planetary Computer |
| `aws` | `https://earth-search.aws.element84.com/v1/` | Element84 Earth Search |
| `gee` | `https://earthengine-stac.storage.googleapis.com/` | Google Earth Engine |

## 参数一览 / Parameters

| 参数 | 说明 | 必填 |
|---|---|---|
| `--preset` | 预置端点名（`pc` / `aws` / `gee`） | ❌ |
| `--endpoint` | 自定义 STAC 端点 URL | ❌ |
| `--collection` | 集合名（如 `landsat-c2-l2`） | ✅ |
| `--bbox` | 地理范围 `[minLon minLat maxLon maxLat]` | ❌ |
| `--datetime` | 时间范围 `YYYY-MM-DD/YYYY-MM-DD` | ❌ |
| `--cloud-cover` | 最大云量百分比 | ❌ |
| `--limit` | 最大返回条目数 | ❌ |
| `--json` | JSON 格式输出 | ❌ |
| `--list-assets` | 列出集合资产 | ❌ |
| `--collection-info` | 显示集合详情 | ❌ |

## License

MIT-0（详见 [LICENSE](./LICENSE)）。

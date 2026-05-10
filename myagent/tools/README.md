# 🛠️ 旅行规划Agent - 工具层 (Tools Layer)

本模块是旅行规划Agent的工具层，位于 `agent-platform/backend/tools/`，为Agent核心提供四类外部能力：**景点搜索、天气查询、交通计算、预算估算**。

---

## 目录

- [文件结构](#文件结构)
- [快速开始](#快速开始)
- [配置 API Key](#配置-api-key)
- [工具使用指南](#工具使用指南)
  - [景点搜索工具](#1-景点搜索工具-attractionsearchtool)
  - [天气查询工具](#2-天气查询工具-weatherquerytool)
  - [交通距离工具](#3-交通距离工具-transportdistancetool)
  - [预算计算工具](#4-预算计算工具-budgetcurrencytool)
  - [汇率查询工具](#5-汇率查询工具-exchangeratetool)
- [与Agent核心对接（第一组看这里）](#与agent核心对接第一组看这里)
- [注入天气突变（测试自我修正）](#注入天气突变测试自我修正)
- [返回格式规范](#返回格式规范)
- [运行测试](#运行测试)
- [常见问题](#常见问题)

---

## 文件结构

```
agent-platform/
├── .env.example                  # 环境变量模板（复制为 .env 后填写）
├── requirements-tools.txt        # 工具层依赖
└── backend/
    ├── tools/
    │   ├── __init__.py           # 工具注册中心
    │   ├── base.py               # BaseTool 抽象基类
    │   ├── attraction.py         # 景点搜索工具
    │   ├── weather.py            # 天气查询工具
    │   ├── transport.py          # 交通与距离计算工具
    │   └── budget.py             # 预算计算 + 汇率工具
    └── tests/
        └── test_tools.py         # 完整测试套件（26个测试用例）
```

---

## 快速开始

### 第一步：安装依赖

```bash
cd agent-platform
pip install -r requirements-tools.txt
```

### 第二步：配置环境变量

```bash
# 复制模板
cp .env.example .env
```

用任意文本编辑器打开 `.env`，按需填写（详见下一节）。

### 第三步：验证工具是否正常

```bash
# 不需要任何 API Key，用 Mock 模式跑一遍所有测试
cd agent-platform/backend
MOCK_MODE=true PYTHONPATH=. python tests/test_tools.py
```

看到 `🎉 所有测试通过！` 说明环境没问题。

---

## 配置 API Key

`.env` 文件中有两类配置：**全局开关** 和 **各工具的 API Key**。

### 全局 Mock 开关（优先级最高）

```ini
MOCK_MODE=true
```

设为 `true` 时，**所有工具自动使用本地模拟数据**，不发出任何网络请求，不消耗任何配额。**开发早期、演示或联调时建议开启。**

设为 `false` 或删除此行后，工具会使用下方配置的真实 API。

---

### 各工具 API 配置

每个工具可以独立选择提供商（通过 `*_PROVIDER` 变量），再填写对应的 Key。

#### 🗺️ 景点搜索工具

```ini
ATTRACTION_PROVIDER=amap   # 可选：amap | baidu | google | mock
```

| 提供商 | 推荐场景 | 免费额度 | Key 变量 | 注册地址 |
|--------|----------|----------|----------|----------|
| `amap`（高德）| 国内游 ✅ 推荐 | 5000次/天 | `AMAP_KEY` | https://lbs.amap.com/ |
| `baidu`（百度）| 国内游备选 | 5000次/天 | `BAIDU_MAP_AK` | https://lbsyun.baidu.com/ |
| `google` | 境外游 | $200/月免费额度 | `GOOGLE_MAPS_KEY` | https://console.cloud.google.com/ |
| `mock` | 开发/演示 | 无限制 | 无需 | — |

```ini
AMAP_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
BAIDU_MAP_AK=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
GOOGLE_MAPS_KEY=AIzaXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
```

#### 🌤️ 天气查询工具

```ini
WEATHER_PROVIDER=qweather   # 可选：qweather | openweather | mock
```

| 提供商 | 推荐场景 | 免费额度 | Key 变量 | 注册地址 |
|--------|----------|----------|----------|----------|
| `qweather`（和风）| 国内 ✅ 推荐 | 1000次/天 | `QWEATHER_KEY` | https://dev.qweather.com/ |
| `openweather` | 国际 | 1000次/天 | `OPENWEATHER_KEY` | https://openweathermap.org/api |
| `mock` | 开发/演示 | 无限制 | 无需 | — |

```ini
QWEATHER_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENWEATHER_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 🚗 交通距离工具

```ini
TRANSPORT_PROVIDER=amap   # 可选：amap | baidu | google | mock
```

提供商选项与景点搜索相同，Key 也复用同一个变量（`AMAP_KEY` 等），无需重复填写。

#### 💰 汇率工具

```ini
CURRENCY_PROVIDER=exchangerate   # 可选：exchangerate | frankfurter | mock
```

| 提供商 | 特点 | 免费额度 | 是否需要 Key |
|--------|------|----------|--------------|
| `exchangerate` | 轻量稳定 ✅ 推荐 | 1500次/月 | **不需要** |
| `frankfurter` | 欧洲央行数据，开源 | 无限制 | **不需要** |
| `mock` | 离线 | 无限制 | 不需要 |

> 💡 **汇率工具无需 Key**，直接设置 `CURRENCY_PROVIDER=exchangerate` 即可使用真实汇率。

---

### 一份完整的 `.env` 示例

```ini
# ── 开发阶段：全部 Mock，无需任何 Key ──
MOCK_MODE=true

# ── 接入真实API时（把上面改为 false）──
# MOCK_MODE=false

ATTRACTION_PROVIDER=amap
WEATHER_PROVIDER=qweather
TRANSPORT_PROVIDER=amap
CURRENCY_PROVIDER=exchangerate

AMAP_KEY=你的高德Key
QWEATHER_KEY=你的和风天气Key

# 境外游才需要：
# GOOGLE_MAPS_KEY=你的Google Key
# OPENWEATHER_KEY=你的OpenWeather Key
```

> ⚠️ **`.env` 文件绝对不要提交到 Git！** 确认 `.gitignore` 中包含 `.env`。

---

## 工具使用指南

所有工具使用方式一致：**实例化 → 调用 `.execute()`** 即可。

```python
import os
os.environ["MOCK_MODE"] = "true"  # 或通过 .env 文件加载

from tools import AttractionSearchTool

tool = AttractionSearchTool()
result = tool.execute(keyword="西湖", city="杭州")
print(result)
```

---

### 1. 景点搜索工具 (`AttractionSearchTool`)

**函数名（LLM调用时）**：`search_attractions`

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `keyword` | str | ✅ | 搜索关键词，如 `"西湖"`、`"博物馆"`、`"自然风光"` |
| `city` | str | | 目标城市，如 `"杭州"`、`"北京"` |
| `types` | str | | 类型过滤，如 `"博物馆"`、`"自然风光"`、`"古典园林"` |
| `radius` | int | | 周边搜索半径（米），不填则全城搜索 |
| `limit` | int | | 返回数量，默认 10 |

#### 示例

```python
from tools import AttractionSearchTool

tool = AttractionSearchTool()

# 搜索杭州自然景点
result = tool.execute(keyword="自然风光", city="杭州", limit=5)

# 天气差时专门搜室内景点
result = tool.execute(keyword="展览", city="杭州", types="博物馆")

# 打印景点列表
if result["status"] == "success":
    for a in result["data"]["attractions"]:
        print(f'{a["name"]} | 评分:{a["rating"]} | 门票:{a["ticket_price"]}元 | {a["opening_hours"]}')
```

#### 返回示例

```json
{
  "status": "success",
  "data": {
    "total": 3,
    "attractions": [
      {
        "name": "西湖",
        "location": {"lat": 30.259, "lng": 120.155},
        "address": "杭州市西湖区龙井路1号",
        "rating": 4.9,
        "ticket_price": 0,
        "opening_hours": "全天",
        "type": "自然风光"
      }
    ],
    "execution_metadata": {"duration_ms": 50, "provider": "mock"}
  }
}
```

---

### 2. 天气查询工具 (`WeatherQueryTool`)

**函数名（LLM调用时）**：`query_weather`

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `lat` | float | ✅ | 纬度 |
| `lon` | float | ✅ | 经度 |
| `date` | str | | 目标日期（YYYY-MM-DD），默认今天 |
| `days` | int | | 预报天数（1-7），默认 3 |

> 💡 坐标可以从景点搜索返回的 `location` 字段直接取用。

#### 示例

```python
from tools import WeatherQueryTool

tool = WeatherQueryTool()

result = tool.execute(lat=30.259, lon=120.155, days=3)

if result["status"] == "success":
    for day in result["data"]["daily"]:
        print(f'{day["date"]} | {day["description"]} | {day["temp_min"]}~{day["temp_max"]}℃ | 降水概率:{day["pop"]*100:.0f}%')
```

#### 判断天气是否适合户外活动

```python
def is_good_for_outdoor(day: dict) -> bool:
    bad_weather = {"Rain", "Thunderstorm", "Snow"}
    return day["weather_main"] not in bad_weather and day["pop"] < 0.6

for day in result["data"]["daily"]:
    status = "✅ 适合户外" if is_good_for_outdoor(day) else "❌ 建议室内"
    print(f'{day["date"]} {status}')
```

---

### 3. 交通距离工具 (`TransportDistanceTool`)

**函数名（LLM调用时）**：`calculate_distance`

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `origin` | [lat, lng] | ✅* | 起点坐标 |
| `destination` | [lat, lng] | ✅* | 终点坐标 |
| `mode` | str | | `driving` / `walking` / `transit` / `bicycling`，默认 `driving` |
| `waypoints` | [[lat,lng], ...] | | 途经点列表 |
| `points` | [[lat,lng], ...] | ✅* | **距离矩阵模式**：传入多个点，计算两两距离 |

> `origin`+`destination` 和 `points` 二选一。

#### 示例：单段路线

```python
from tools import TransportDistanceTool

tool = TransportDistanceTool()

result = tool.execute(
    origin=[30.259, 120.155],
    destination=[30.240, 120.101],
    mode="driving"
)

if result["status"] == "success":
    route = result["data"]["route"]
    print(f'距离: {route["distance_meters"]/1000:.1f}km | 耗时: {route["duration_text"]}')
```

#### 示例：距离矩阵（多景点排序优化）

```python
# 一次性计算多个景点的两两距离
points = [
    [30.259, 120.155],  # 西湖
    [30.240, 120.101],  # 灵隐寺
    [30.231, 120.148],  # 雷峰塔
]
result = tool.execute(points=points, mode="driving")

if result["status"] == "success":
    matrix = result["data"]["matrix"]
    names = ["西湖", "灵隐寺", "雷峰塔"]
    for i in range(3):
        for j in range(3):
            mins = matrix[i][j]["duration_seconds"] // 60
            print(f"  {names[i]} → {names[j]}: {mins}分钟")
```

#### 时间冲突检测（第一组参考）

```python
def check_daily_feasibility(activities: list, tool: TransportDistanceTool) -> bool:
    """
    检查一天的行程是否时间够用
    activities: [{"name": ..., "location": [lat,lng], "visit_minutes": 90}, ...]
    """
    available_minutes = 10 * 60  # 每天可用10小时
    total = 0
    for i in range(len(activities) - 1):
        total += activities[i]["visit_minutes"]
        result = tool.execute(
            origin=activities[i]["location"],
            destination=activities[i+1]["location"],
            mode="transit"
        )
        if result["status"] == "success":
            total += result["data"]["route"]["duration_seconds"] // 60
    total += activities[-1]["visit_minutes"]
    return total <= available_minutes
```

---

### 4. 预算计算工具 (`BudgetCurrencyTool`)

**函数名（LLM调用时）**：`calculate_budget`

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `city` | str | ✅ | 目的地城市 |
| `days` | int | ✅ | 旅行天数 |
| `num_people` | int | ✅ | 出行人数 |
| `attractions` | list | ✅ | 景点列表（需含 `ticket_price` 字段） |
| `hotel_level` | str | | `budget` / `mid` / `luxury`，默认 `mid` |
| `budget_limit` | float | | 用户预算上限（元），有则自动检测超支 |
| `currency` | str | | 结算币种（如 `"USD"`），默认 `"CNY"` |
| `from_city` | str | | 出发城市，用于估算城际交通费 |

#### 示例

```python
from tools import BudgetCurrencyTool, AttractionSearchTool

attractions = AttractionSearchTool().execute(keyword="景点", city="杭州")["data"]["attractions"]

tool = BudgetCurrencyTool()
result = tool.execute(
    city="杭州",
    days=3,
    num_people=2,
    attractions=attractions,
    hotel_level="mid",
    budget_limit=3000,
    from_city="南京",
)

if result["status"] == "success":
    data = result["data"]
    print(f'总预算: {data["total"]} 元')
    if data["is_over_budget"]:
        print(f'超支: {data["overspent"]} 元，建议: {data["suggestions"]}')
    for k, v in data["breakdown_cny"].items():
        print(f'  {k}: {v} 元')
```

#### 超支自动修正逻辑（第一组参考）

```python
def auto_reduce_budget(city, days, num_people, attractions, hotel_level, budget_limit, tool):
    """模拟 Agent 超支修正：依次降酒店档次 → 删高价景点"""
    for level in ["luxury", "mid", "budget"][["luxury","mid","budget"].index(hotel_level):]:
        result = tool.execute(city=city, days=days, num_people=num_people,
                              attractions=attractions, hotel_level=level,
                              budget_limit=budget_limit)
        if not result["data"]["is_over_budget"]:
            print(f'✅ 调整酒店为 {level} 档后预算达标')
            return result["data"]

    # 再删高价景点
    sorted_attr = sorted(attractions, key=lambda a: a.get("ticket_price", 0), reverse=True)
    while sorted_attr:
        removed = sorted_attr.pop(0)
        print(f'移除景点：{removed["name"]}（门票 {removed["ticket_price"]} 元）')
        result = tool.execute(city=city, days=days, num_people=num_people,
                              attractions=sorted_attr, hotel_level="budget",
                              budget_limit=budget_limit)
        if not result["data"]["is_over_budget"]:
            return result["data"]
    return None
```

---

### 5. 汇率查询工具 (`ExchangeRateTool`)

**函数名（LLM调用时）**：`get_exchange_rate`

#### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `from_currency` | str | | 源币种，默认 `"CNY"` |
| `to_currency` | str | ✅ | 目标币种，如 `"USD"`、`"JPY"`、`"EUR"` |

#### 示例

```python
from tools import ExchangeRateTool

tool = ExchangeRateTool()
result = tool.execute(from_currency="CNY", to_currency="JPY")

if result["status"] == "success":
    print(f'1 CNY = {result["data"]["rate"]} JPY')
```

---

## 与Agent核心对接（第一组看这里）

### 获取所有工具

```python
from tools import get_all_tools, get_tool_by_name

# 获取全部工具实例
tools = get_all_tools()
# 返回: [AttractionSearchTool, WeatherQueryTool, TransportDistanceTool,
#        BudgetCurrencyTool, ExchangeRateTool]

# 按名称查找（ToolExecutor 中用到）
tool = get_tool_by_name("search_attractions")
result = tool.execute(keyword="西湖", city="杭州")
```

### 注册到 LLM（DeepSeek function calling 格式）

```python
from tools import get_all_tools

tools = get_all_tools()
openai_tools = [t.to_openai_function() for t in tools]

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=openai_tools,  # ← 直接传入，格式完全兼容
)
```

### ToolExecutor 中分发调用

```python
from tools import get_tool_by_name

def dispatch_tool_call(tool_name: str, params: dict) -> dict:
    """根据 LLM 返回的 function call 分发到对应工具"""
    tool = get_tool_by_name(tool_name)
    if tool is None:
        return {
            "status": "error",
            "error": {"code": "TOOL_NOT_FOUND", "message": f"未知工具: {tool_name}"}
        }
    return tool.execute(**params)
```

### 提取执行元数据（写入 Trace 日志）

```python
result = tool.execute(keyword="西湖", city="杭州")

meta = result["data"]["execution_metadata"]
# 用于 CLI 打印：🔧 [工具] search_attractions 耗时 50ms [mock]
print(f'🔧 [工具] {tool.name} 耗时 {meta["duration_ms"]}ms [{meta["provider"]}]')
```

---

## 注入天气突变（测试自我修正）

专为测试 Agent 自我修正逻辑设计，在无需真实恶劣天气的情况下触发修正流程：

```python
from tools import WeatherQueryTool, set_mock_weather_scenario

tool = WeatherQueryTool()

# 注入暴雨
set_mock_weather_scenario("heavy_rain")
result = tool.execute(lat=30.25, lon=120.16, days=1)
# → 天气: 暴雨, 降水概率: 0.95

# 注入雷暴
set_mock_weather_scenario("storm")

# 恢复正常随机天气
set_mock_weather_scenario(None)
```

**与 Agent 修正逻辑联动：**

```python
# Agent 在确认行程后二次调用天气工具检测突变
weather = WeatherQueryTool().execute(lat=loc["lat"], lon=loc["lng"], days=days)

for day in weather["data"]["daily"]:
    if day["weather_main"] in ("Rain", "Thunderstorm") and day["pop"] > 0.7:
        # 触发修正：搜索室内替代景点
        indoor = AttractionSearchTool().execute(
            keyword="博物馆", city=city, types="博物馆"
        )
        # ... 替换当天户外行程，重新计算路线和预算
```

---

## 返回格式规范

所有工具永远返回字典，不会抛出异常：

```python
# 成功
{
    "status": "success",
    "data": {
        # 具体数据（各工具不同）
        "execution_metadata": {
            "duration_ms": 230,      # 实际耗时（毫秒）
            "provider": "amap"       # 使用的API提供商
        }
    }
}

# 失败
{
    "status": "error",
    "error": {
        "code": "NO_RESULTS",        # 机器可读的错误码
        "message": "未找到相关景点"   # 人类可读的描述
    }
}
```

**正确的错误处理：**

```python
result = tool.execute(keyword="西湖", city="杭州")

if result["status"] == "success":
    attractions = result["data"]["attractions"]
else:
    code = result["error"]["code"]
    if code == "NO_RESULTS":
        pass  # 换关键词重试
    elif code == "RATE_LIMITED":
        pass  # 等待后重试
```

**常见错误码：**

| 错误码 | 含义 | 建议处理 |
|--------|------|----------|
| `NO_RESULTS` | 无搜索结果 | 换关键词或扩大范围重试 |
| `RATE_LIMITED` | API限流 | 等待1s后重试，或切换提供商 |
| `INVALID_KEY` | Key无效 | 检查 `.env` 配置，切换Mock |
| `QUOTA_EXCEEDED` | 配额耗尽 | 切换备用提供商或Mock |
| `NETWORK_ERROR` | 网络异常 | 重试1-2次，失败则切换Mock |
| `INVALID_COORDS` | 坐标无效 | 检查景点 `location` 字段 |
| `UNSUPPORTED_CURRENCY` | 不支持的币种 | 改用CNY或检查币种代码 |

---

## 运行测试

```bash
cd agent-platform/backend

# Mock 模式（推荐，不需要 API Key）
MOCK_MODE=true PYTHONPATH=. python tests/test_tools.py

# 真实 API 模式（需先在 .env 中配置 Key）
MOCK_MODE=false PYTHONPATH=. python tests/test_tools.py

# 用 pytest
MOCK_MODE=true PYTHONPATH=. pytest tests/test_tools.py -v
```

测试覆盖：各工具基础功能 / 参数校验与错误处理 / Mock数据格式 / 天气突变注入 / 距离矩阵 / 预算超支检测 / OpenAI function格式 / 端到端集成场景。

---

## 常见问题

**Q: 提示 `ModuleNotFoundError: No module named 'tools'`**

确认从 `backend/` 目录运行，并设置了 `PYTHONPATH=.`：
```bash
cd agent-platform/backend
MOCK_MODE=true PYTHONPATH=. python your_script.py
```

**Q: 高德 Key 申请后仍然报 `INVALID_KEY`**

新 Key 需等待 5-10 分钟激活，且必须在控制台开启 **Web服务** 权限（不是 Web端 JS SDK）。

**Q: Mock 模式下某个城市找不到景点**

当前内置了杭州、苏州、北京、上海、广州、深圳等主要城市。其他城市返回通用 `default` 数据。如需补充，在 `attraction.py` 的 `_MOCK_ATTRACTIONS` 字典中添加即可。

**Q: 如何新增一个工具？**

1. 在 `tools/` 下新建文件，继承 `BaseTool`，实现 `name`、`description`、`parameters`、`_execute`
2. 在 `tools/__init__.py` 的 `get_all_tools()` 列表中追加实例

Agent 核心无需修改，下次调用 `get_all_tools()` 会自动包含新工具。

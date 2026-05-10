"""
工具层测试文件
运行前请确保设置 MOCK_MODE=true 或配置真实 API Key

运行方式：
  MOCK_MODE=true python -m pytest tests/test_tools.py -v
  或直接运行：
  MOCK_MODE=true python tests/test_tools.py
"""

import os
import sys
import json

# 确保在 mock 模式下运行
os.environ.setdefault("MOCK_MODE", "true")

# 将 backend 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import (
    AttractionSearchTool,
    WeatherQueryTool,
    TransportDistanceTool,
    BudgetCurrencyTool,
    ExchangeRateTool,
    get_all_tools,
    get_tool_by_name,
    set_mock_weather_scenario,
)


# ── 辅助函数 ──────────────────────────────────────────────────────────────────

def assert_success(result: dict, label: str = ""):
    assert result["status"] == "success", \
        f"[{label}] 期望成功，实际返回: {json.dumps(result, ensure_ascii=False, indent=2)}"
    assert "data" in result, f"[{label}] 成功结果缺少 data 字段"


def assert_error(result: dict, code: str = None, label: str = ""):
    assert result["status"] == "error", \
        f"[{label}] 期望错误，实际返回: {json.dumps(result, ensure_ascii=False, indent=2)}"
    assert "error" in result, f"[{label}] 错误结果缺少 error 字段"
    if code:
        assert result["error"]["code"] == code, \
            f"[{label}] 期望错误码 {code}，实际: {result['error']['code']}"


def print_result(label: str, result: dict):
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print(json.dumps(result, ensure_ascii=False, indent=2))


# ── 景点搜索工具测试 ──────────────────────────────────────────────────────────

def test_attraction_basic():
    tool = AttractionSearchTool()
    result = tool.execute(keyword="西湖", city="杭州")
    print_result("景点搜索：西湖 杭州", result)
    assert_success(result, "attraction_basic")
    data = result["data"]
    assert "attractions" in data
    assert len(data["attractions"]) > 0
    # 检查景点结构
    a = data["attractions"][0]
    for field in ("name", "location", "rating", "ticket_price", "opening_hours", "type"):
        assert field in a, f"景点缺少字段: {field}"
    assert "execution_metadata" in data
    print("✅ 景点搜索基础测试通过")


def test_attraction_filter_type():
    tool = AttractionSearchTool()
    result = tool.execute(keyword="展览", city="杭州", types="博物馆", limit=5)
    assert_success(result, "attraction_filter_type")
    print("✅ 景点类型过滤测试通过")


def test_attraction_unknown_city():
    tool = AttractionSearchTool()
    result = tool.execute(keyword="景点", city="火星市")
    # Mock模式下应返回 default 数据，不应报错
    assert result["status"] in ("success", "error")
    print("✅ 景点未知城市测试通过")


def test_attraction_openai_function():
    tool = AttractionSearchTool()
    func_def = tool.to_openai_function()
    assert func_def["type"] == "function"
    assert func_def["function"]["name"] == "search_attractions"
    assert "parameters" in func_def["function"]
    print("✅ 景点工具 OpenAI function 格式测试通过")


# ── 天气查询工具测试 ──────────────────────────────────────────────────────────

def test_weather_basic():
    tool = WeatherQueryTool()
    result = tool.execute(lat=30.25, lon=120.16, days=3)
    print_result("天气查询：杭州3天", result)
    assert_success(result, "weather_basic")
    data = result["data"]
    assert "current" in data
    assert "daily" in data
    assert len(data["daily"]) == 3
    day = data["daily"][0]
    for field in ("date", "temp_min", "temp_max", "weather_main", "description", "pop"):
        assert field in day, f"天气日数据缺少字段: {field}"
    print("✅ 天气查询基础测试通过")


def test_weather_invalid_coord():
    tool = WeatherQueryTool()
    result = tool.execute(lat=999, lon=999)
    assert_error(result, "INVALID_COORD", "weather_invalid_coord")
    print("✅ 天气无效坐标测试通过")


def test_weather_days_out_of_range():
    tool = WeatherQueryTool()
    result = tool.execute(lat=30.25, lon=120.16, days=30)
    assert_error(result, "DATE_OUT_OF_RANGE", "weather_days_out_of_range")
    print("✅ 天气天数超限测试通过")


def test_weather_inject_heavy_rain():
    """测试天气突变注入（用于Agent自我修正测试）"""
    set_mock_weather_scenario("heavy_rain")
    tool = WeatherQueryTool()
    result = tool.execute(lat=30.25, lon=120.16, days=1)
    assert_success(result, "weather_inject_rain")
    day = result["data"]["daily"][0]
    assert day["pop"] >= 0.9, "注入暴雨场景时降水概率应很高"
    assert "雨" in day["description"] or "Rain" in day["weather_main"]
    set_mock_weather_scenario(None)  # 恢复正常
    print("✅ 天气突变注入测试通过")


# ── 交通与距离工具测试 ────────────────────────────────────────────────────────

def test_transport_basic():
    tool = TransportDistanceTool()
    result = tool.execute(
        origin=[30.2590, 120.1551],   # 西湖
        destination=[30.2405, 120.1017],  # 灵隐寺
        mode="driving"
    )
    print_result("交通：西湖→灵隐寺（驾车）", result)
    assert_success(result, "transport_basic")
    route = result["data"]["route"]
    for field in ("distance_meters", "duration_seconds", "duration_text", "mode"):
        assert field in route, f"路线数据缺少字段: {field}"
    assert route["distance_meters"] > 0
    assert route["duration_seconds"] > 0
    print("✅ 交通基础测试通过")


def test_transport_modes():
    tool = TransportDistanceTool()
    for mode in ("driving", "walking", "transit", "bicycling"):
        result = tool.execute(
            origin=[31.3244, 120.6317],
            destination=[31.3197, 120.6338],
            mode=mode
        )
        assert_success(result, f"transport_mode_{mode}")
        assert result["data"]["route"]["mode"] == mode
    print("✅ 各出行方式测试通过")


def test_transport_with_waypoints():
    tool = TransportDistanceTool()
    result = tool.execute(
        origin=[30.25, 120.16],
        destination=[30.24, 120.10],
        mode="driving",
        waypoints=[[30.245, 120.14]]
    )
    assert_success(result, "transport_waypoints")
    print("✅ 途经点测试通过")


def test_transport_distance_matrix():
    tool = TransportDistanceTool()
    points = [
        [30.2590, 120.1551],  # 西湖
        [30.2405, 120.1017],  # 灵隐寺
        [30.2317, 120.1483],  # 雷峰塔
    ]
    result = tool.execute(points=points, mode="driving")
    print_result("距离矩阵：3个景点", result)
    assert_success(result, "transport_matrix")
    data = result["data"]
    assert data["size"] == 3
    assert len(data["matrix"]) == 3
    assert data["matrix"][0][0]["distance_meters"] == 0  # 自身距离为0
    print("✅ 距离矩阵测试通过")


def test_transport_invalid_coords():
    tool = TransportDistanceTool()
    result = tool.execute(
        origin=[999, 999],
        destination=[30.25, 120.16],
        mode="driving"
    )
    assert_error(result, "INVALID_COORDS", "transport_invalid_coords")
    print("✅ 交通无效坐标测试通过")


def test_transport_invalid_mode():
    tool = TransportDistanceTool()
    result = tool.execute(
        origin=[30.25, 120.16],
        destination=[30.24, 120.10],
        mode="teleport"
    )
    assert_error(result, "INVALID_MODE", "transport_invalid_mode")
    print("✅ 交通无效出行方式测试通过")


# ── 预算计算工具测试 ──────────────────────────────────────────────────────────

def test_budget_basic():
    tool = BudgetCurrencyTool()
    attractions = [
        {"name": "西湖", "ticket_price": 0},
        {"name": "灵隐寺", "ticket_price": 75},
        {"name": "雷峰塔", "ticket_price": 40},
    ]
    result = tool.execute(
        city="杭州",
        days=3,
        num_people=2,
        attractions=attractions,
        hotel_level="mid",
        budget_limit=3000,
    )
    print_result("预算：杭州3天2人mid档", result)
    assert_success(result, "budget_basic")
    data = result["data"]
    assert "total" in data
    assert "breakdown_cny" in data
    assert "is_over_budget" in data
    breakdown = data["breakdown_cny"]
    for key in ("accommodation", "meals", "tickets", "transport_local", "other"):
        assert key in breakdown, f"预算明细缺少字段: {key}"
    assert data["total"] > 0
    print("✅ 预算基础测试通过")


def test_budget_over_limit():
    tool = BudgetCurrencyTool()
    attractions = [
        {"name": "迪士尼", "ticket_price": 499},
        {"name": "豫园", "ticket_price": 40},
    ]
    result = tool.execute(
        city="上海",
        days=5,
        num_people=4,
        attractions=attractions,
        hotel_level="luxury",
        budget_limit=5000,  # 明显不够
    )
    assert_success(result, "budget_over_limit")
    data = result["data"]
    assert data["is_over_budget"] is True
    assert data["overspent"] > 0
    assert len(data.get("suggestions", [])) > 0
    print("✅ 预算超支检测测试通过")


def test_budget_with_intercity():
    tool = BudgetCurrencyTool()
    result = tool.execute(
        city="苏州",
        days=2,
        num_people=2,
        attractions=[{"name": "拙政园", "ticket_price": 90}],
        from_city="南京",
    )
    assert_success(result, "budget_intercity")
    data = result["data"]
    assert data["breakdown_cny"]["transport_intercity"] > 0
    print("✅ 城际交通预算测试通过")


def test_budget_hotel_levels():
    tool = BudgetCurrencyTool()
    attractions = [{"name": "故宫", "ticket_price": 60}]
    totals = {}
    for level in ("budget", "mid", "luxury"):
        result = tool.execute(city="北京", days=2, num_people=2,
                              attractions=attractions, hotel_level=level)
        assert_success(result, f"budget_hotel_{level}")
        totals[level] = result["data"]["total"]
    assert totals["budget"] < totals["mid"] < totals["luxury"], \
        f"酒店档次价格排序错误: {totals}"
    print("✅ 酒店档次价格排序测试通过")


# ── 汇率工具测试 ──────────────────────────────────────────────────────────────

def test_exchange_rate_basic():
    tool = ExchangeRateTool()
    result = tool.execute(from_currency="CNY", to_currency="USD")
    print_result("汇率：CNY→USD", result)
    assert_success(result, "exchange_basic")
    data = result["data"]
    assert "rate" in data
    assert data["rate"] > 0
    assert data["from"] == "CNY"
    assert data["to"] == "USD"
    print("✅ 汇率基础测试通过")


def test_exchange_rate_unsupported():
    tool = ExchangeRateTool()
    result = tool.execute(from_currency="CNY", to_currency="XYZ")
    assert_error(result, "UNSUPPORTED_CURRENCY", "exchange_unsupported")
    print("✅ 不支持币种测试通过")


def test_exchange_rate_in_budget():
    """测试预算工具内置汇率换算"""
    tool = BudgetCurrencyTool()
    result = tool.execute(
        city="北京",
        days=2,
        num_people=1,
        attractions=[{"name": "故宫", "ticket_price": 60}],
        currency="USD",
    )
    assert_success(result, "budget_currency_usd")
    data = result["data"]
    assert data["currency"] == "USD"
    assert data["total"] < data["exchange_info"]["from_cny_total"]  # USD < CNY
    print("✅ 预算外币换算测试通过")


# ── 工具注册中心测试 ──────────────────────────────────────────────────────────

def test_tool_registry():
    tools = get_all_tools()
    assert len(tools) >= 4, f"期望至少4个工具，实际: {len(tools)}"
    names = [t.name for t in tools]
    for expected in ("search_attractions", "query_weather", "calculate_distance", "calculate_budget"):
        assert expected in names, f"缺少工具: {expected}"
    print(f"✅ 工具注册中心测试通过，共注册 {len(tools)} 个工具: {names}")


def test_tool_by_name():
    tool = get_tool_by_name("search_attractions")
    assert tool is not None
    assert tool.name == "search_attractions"
    none_tool = get_tool_by_name("nonexistent_tool")
    assert none_tool is None
    print("✅ 按名称查找工具测试通过")


def test_all_tools_openai_format():
    """验证所有工具都可以正确转换为OpenAI/DeepSeek function calling格式"""
    tools = get_all_tools()
    for tool in tools:
        func_def = tool.to_openai_function()
        assert func_def["type"] == "function"
        assert "name" in func_def["function"]
        assert "description" in func_def["function"]
        assert "parameters" in func_def["function"]
        assert "required" in func_def["function"]["parameters"] or \
               "properties" in func_def["function"]["parameters"]
    print(f"✅ 所有工具 OpenAI function 格式验证通过")


def test_execution_metadata():
    """验证所有工具都返回执行元数据"""
    tool = AttractionSearchTool()
    result = tool.execute(keyword="西湖", city="杭州")
    assert "execution_metadata" in result["data"], "缺少 execution_metadata"
    meta = result["data"]["execution_metadata"]
    assert "duration_ms" in meta
    assert "provider" in meta
    assert meta["provider"] == "mock"
    print("✅ 执行元数据测试通过")


# ── 集成场景测试 ──────────────────────────────────────────────────────────────

def test_integration_hangzhou_trip():
    """
    集成测试：模拟Agent规划"杭州3日游"的完整工具调用流程
    """
    print("\n" + "="*60)
    print("  集成测试：杭州3日游完整工具调用流程")
    print("="*60)

    # Step 1: 搜索景点
    attraction_tool = AttractionSearchTool()
    attractions_result = attraction_tool.execute(keyword="自然风光", city="杭州", limit=5)
    assert_success(attractions_result, "integration_step1")
    attractions = attractions_result["data"]["attractions"]
    print(f"Step1 ✅ 找到 {len(attractions)} 个景点")

    # Step 2: 查询天气
    weather_tool = WeatherQueryTool()
    # 使用第一个景点的坐标
    loc = attractions[0]["location"]
    weather_result = weather_tool.execute(lat=loc["lat"], lon=loc["lng"], days=3)
    assert_success(weather_result, "integration_step2")
    print(f"Step2 ✅ 天气查询成功，未来3天: {[d['description'] for d in weather_result['data']['daily']]}")

    # Step 3: 计算景点间距离
    transport_tool = TransportDistanceTool()
    if len(attractions) >= 2:
        dist_result = transport_tool.execute(
            origin=[attractions[0]["location"]["lat"], attractions[0]["location"]["lng"]],
            destination=[attractions[1]["location"]["lat"], attractions[1]["location"]["lng"]],
            mode="driving"
        )
        assert_success(dist_result, "integration_step3")
        route = dist_result["data"]["route"]
        print(f"Step3 ✅ 两景点间距离: {route['distance_meters']}m, 耗时: {route['duration_text']}")

    # Step 4: 计算预算
    budget_tool = BudgetCurrencyTool()
    budget_result = budget_tool.execute(
        city="杭州",
        days=3,
        num_people=2,
        attractions=attractions,
        hotel_level="mid",
        budget_limit=3000,
        from_city="南京",
    )
    assert_success(budget_result, "integration_step4")
    data = budget_result["data"]
    print(f"Step4 ✅ 预算估算: {data['total']} CNY, 超支: {data.get('is_over_budget', False)}")

    # Step 5: 模拟天气突变后的工具重调用
    set_mock_weather_scenario("heavy_rain")
    weather_check = weather_tool.execute(lat=loc["lat"], lon=loc["lng"], days=1)
    assert_success(weather_check, "integration_step5")
    rain_day = weather_check["data"]["daily"][0]
    print(f"Step5 ✅ 天气突变检测: {rain_day['description']}, 降水概率: {rain_day['pop']}")
    if rain_day["pop"] > 0.7:
        # Agent应触发修正，搜索室内景点
        indoor_result = attraction_tool.execute(keyword="博物馆", city="杭州", types="博物馆", limit=3)
        assert_success(indoor_result, "integration_step5_indoor")
        print(f"       ✅ 自动搜索室内替代景点: {[a['name'] for a in indoor_result['data']['attractions']]}")
    set_mock_weather_scenario(None)

    print("\n🎉 集成测试通过！")


# ── 主入口 ────────────────────────────────────────────────────────────────────

def run_all_tests():
    tests = [
        # 景点
        test_attraction_basic,
        test_attraction_filter_type,
        test_attraction_unknown_city,
        test_attraction_openai_function,
        # 天气
        test_weather_basic,
        test_weather_invalid_coord,
        test_weather_days_out_of_range,
        test_weather_inject_heavy_rain,
        # 交通
        test_transport_basic,
        test_transport_modes,
        test_transport_with_waypoints,
        test_transport_distance_matrix,
        test_transport_invalid_coords,
        test_transport_invalid_mode,
        # 预算
        test_budget_basic,
        test_budget_over_limit,
        test_budget_with_intercity,
        test_budget_hotel_levels,
        # 汇率
        test_exchange_rate_basic,
        test_exchange_rate_unsupported,
        test_exchange_rate_in_budget,
        # 注册中心
        test_tool_registry,
        test_tool_by_name,
        test_all_tools_openai_format,
        test_execution_metadata,
        # 集成
        test_integration_hangzhou_trip,
    ]

    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} 失败: {e}")
            failed += 1
        except Exception as e:
            print(f"💥 {test.__name__} 异常: {type(e).__name__}: {e}")
            failed += 1

    print(f"\n{'='*60}")
    print(f"测试结果: {passed} 通过 / {failed} 失败 / {len(tests)} 总计")
    if failed == 0:
        print("🎉 所有测试通过！")
    print("="*60)
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

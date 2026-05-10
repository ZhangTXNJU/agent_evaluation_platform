"""
天气查询工具 (Weather Query Tool)

支持的API提供商（通过环境变量 WEATHER_PROVIDER 选择）：
- qweather  : 和风天气 API（默认，国内推荐）
- openweather: OpenWeatherMap One Call API 3.0（国际）
- mock      : Mock模式，返回模拟数据

必需环境变量：
- QWEATHER_KEY      : 和风天气 API Key
- OPENWEATHER_KEY   : OpenWeatherMap API Key
- MOCK_MODE=true    : 全局Mock开关
"""

import hashlib
import os
import random
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import requests

from .base import BaseTool


# ── Mock数据生成 ───────────────────────────────────────────────────────────────

_WEATHER_POOL = [
    {"weather_main": "Clear", "description": "晴天", "icon": "01d"},
    {"weather_main": "Clouds", "description": "多云", "icon": "02d"},
    {"weather_main": "Clouds", "description": "阴天", "icon": "04d"},
    {"weather_main": "Rain", "description": "小雨", "icon": "10d"},
    {"weather_main": "Rain", "description": "中雨", "icon": "09d"},
    {"weather_main": "Thunderstorm", "description": "雷阵雨", "icon": "11d"},
]

_INJECT_SCENARIO: Optional[str] = None  # 可注入"heavy_rain"等场景用于测试修正逻辑


def set_mock_weather_scenario(scenario: Optional[str]):
    """测试用：注入突变天气场景。scenario 可选：'heavy_rain', 'storm', None（随机）"""
    global _INJECT_SCENARIO
    _INJECT_SCENARIO = scenario


def _mock_daily(lat: float, lon: float, day_offset: int) -> Dict:
    """基于坐标和日期偏移生成可复现的模拟天气"""
    if _INJECT_SCENARIO == "heavy_rain":
        weather = {"weather_main": "Rain", "description": "暴雨", "icon": "09d"}
        pop = 0.95
    elif _INJECT_SCENARIO == "storm":
        weather = {"weather_main": "Thunderstorm", "description": "雷暴", "icon": "11d"}
        pop = 1.0
    else:
        seed = int(abs(lat * 100 + lon * 100)) + day_offset
        random.seed(seed)
        weather = random.choice(_WEATHER_POOL)
        pop = round(random.uniform(0.05, 0.85), 2)

    base_temp = 20 + int(lat % 10)
    random.seed(int(abs(lat * 1000 + lon * 1000)) + day_offset * 7)
    temp_min = base_temp + random.randint(-3, 2)
    temp_max = temp_min + random.randint(4, 10)

    target_date = date.today() + timedelta(days=day_offset)
    return {
        "date": target_date.isoformat(),
        "temp_min": temp_min,
        "temp_max": temp_max,
        "weather_main": weather["weather_main"],
        "description": weather["description"],
        "pop": pop,
        "icon": weather["icon"],
    }


# ── 工具类 ────────────────────────────────────────────────────────────────────

class WeatherQueryTool(BaseTool):
    """天气查询工具：获取指定坐标的天气预报"""

    def __init__(self):
        self._mock = os.getenv("MOCK_MODE", "false").lower() == "true"
        self._provider = os.getenv("WEATHER_PROVIDER", "qweather").lower()
        if self._mock:
            self._provider = "mock"

    @property
    def name(self) -> str:
        return "query_weather"

    @property
    def description(self) -> str:
        return (
            "根据地理坐标（经纬度）查询当前及未来数天的天气预报，"
            "包括温度、天气状况（晴/雨/雪）、降水概率等。"
            "用于行程规划时判断活动适宜性以及检测突发恶劣天气。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "lat": {
                    "type": "number",
                    "description": "目标位置纬度，如 30.25",
                },
                "lon": {
                    "type": "number",
                    "description": "目标位置经度，如 120.16",
                },
                "date": {
                    "type": "string",
                    "description": "目标日期（YYYY-MM-DD），默认为今天",
                },
                "days": {
                    "type": "integer",
                    "description": "预报天数（1-7），默认3",
                    "default": 3,
                },
            },
            "required": ["lat", "lon"],
        }

    def _provider_name(self) -> str:
        return self._provider

    def _execute(self, lat: float, lon: float, date: str = None,
                 days: int = 3) -> Dict[str, Any]:
        # 参数校验
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            return self.error_response("INVALID_COORD", f"坐标无效: lat={lat}, lon={lon}")
        if days < 1 or days > 7:
            return self.error_response("DATE_OUT_OF_RANGE",
                                       "查询天数超出限制，应在1-7之间", max_days=7)

        if self._mock:
            return self._mock_weather(lat, lon, days)
        if self._provider == "qweather":
            return self._qweather(lat, lon, days)
        if self._provider == "openweather":
            return self._openweather(lat, lon, days)
        return self.error_response("UNKNOWN_PROVIDER", f"未知提供商: {self._provider}")

    # ── Mock ───────────────────────────────────────────────────────────────────

    def _mock_weather(self, lat: float, lon: float, days: int) -> Dict[str, Any]:
        daily = [_mock_daily(lat, lon, i) for i in range(days)]
        current_day = daily[0]
        return {
            "status": "success",
            "data": {
                "location": {"lat": lat, "lon": lon},
                "current": {
                    "temp": current_day["temp_max"] - 2,
                    "feels_like": current_day["temp_max"],
                    "description": current_day["description"],
                    "icon": current_day["icon"],
                },
                "daily": daily,
                "execution_metadata": {"duration_ms": 30, "provider": "mock"},
            },
        }

    # ── 和风天气 ───────────────────────────────────────────────────────────────

    def _qweather(self, lat: float, lon: float, days: int) -> Dict[str, Any]:
        api_key = os.getenv("QWEATHER_KEY")
        if not api_key:
            return self.error_response("INVALID_KEY", "未配置 QWEATHER_KEY 环境变量")

        location = f"{lon:.6f},{lat:.6f}"
        forecast_days = 7 if days > 3 else 3

        # 先获取城市LocationID
        try:
            geo_resp = requests.get(
                "https://geoapi.qweather.com/v2/city/lookup",
                params={"location": location, "key": api_key},
                timeout=10
            )
            geo_resp.raise_for_status()
            geo_data = geo_resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"地理编码请求失败: {e}")

        if geo_data.get("code") == "401":
            return self.error_response("INVALID_KEY", "和风天气API Key无效")
        if geo_data.get("code") != "200" or not geo_data.get("location"):
            return self.error_response("INVALID_COORD", "无法解析该坐标对应的城市")

        location_id = geo_data["location"][0]["id"]

        try:
            weather_resp = requests.get(
                f"https://devapi.qweather.com/v7/weather/{forecast_days}d",
                params={"location": location_id, "key": api_key, "lang": "zh"},
                timeout=10
            )
            weather_resp.raise_for_status()
            weather_data = weather_resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"天气请求失败: {e}")

        if weather_data.get("code") == "429":
            return self.error_response("QUOTA_EXCEEDED", "API额度已用完")
        if weather_data.get("code") != "200":
            return self.error_response("API_ERROR", f"和风天气错误码: {weather_data.get('code')}")

        raw_daily = weather_data.get("daily", [])[:days]
        daily = []
        for d in raw_daily:
            daily.append({
                "date": d.get("fxDate", ""),
                "temp_min": int(d.get("tempMin", 0)),
                "temp_max": int(d.get("tempMax", 0)),
                "weather_main": d.get("textDay", ""),
                "description": d.get("textDay", ""),
                "pop": float(d.get("pop", 0)) / 100,
                "icon": d.get("iconDay", ""),
            })

        current = daily[0] if daily else {}
        return {
            "status": "success",
            "data": {
                "location": {"lat": lat, "lon": lon},
                "current": {
                    "temp": current.get("temp_max", 0),
                    "feels_like": current.get("temp_max", 0),
                    "description": current.get("description", ""),
                    "icon": current.get("icon", ""),
                },
                "daily": daily,
            },
        }

    # ── OpenWeatherMap ─────────────────────────────────────────────────────────

    def _openweather(self, lat: float, lon: float, days: int) -> Dict[str, Any]:
        api_key = os.getenv("OPENWEATHER_KEY")
        if not api_key:
            return self.error_response("INVALID_KEY", "未配置 OPENWEATHER_KEY 环境变量")

        params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key,
            "units": "metric",
            "lang": "zh_cn",
            "exclude": "minutely,hourly,alerts",
        }

        try:
            resp = requests.get(
                "https://api.openweathermap.org/data/3.0/onecall",
                params=params, timeout=10
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        if "cod" in raw:
            code = str(raw.get("cod", ""))
            if code == "401":
                return self.error_response("INVALID_KEY", "OpenWeatherMap API Key无效")
            if code == "429":
                return self.error_response("QUOTA_EXCEEDED", "API额度已用完")
            return self.error_response("API_ERROR", raw.get("message", "未知错误"))

        current_raw = raw.get("current", {})
        current = {
            "temp": round(current_raw.get("temp", 0)),
            "feels_like": round(current_raw.get("feels_like", 0)),
            "description": current_raw.get("weather", [{}])[0].get("description", ""),
            "icon": current_raw.get("weather", [{}])[0].get("icon", ""),
        }

        daily = []
        for d in raw.get("daily", [])[:days]:
            dt = datetime.fromtimestamp(d["dt"])
            weather_info = d.get("weather", [{}])[0]
            daily.append({
                "date": dt.strftime("%Y-%m-%d"),
                "temp_min": round(d.get("temp", {}).get("min", 0)),
                "temp_max": round(d.get("temp", {}).get("max", 0)),
                "weather_main": weather_info.get("main", ""),
                "description": weather_info.get("description", ""),
                "pop": round(d.get("pop", 0), 2),
                "icon": weather_info.get("icon", ""),
            })

        return {
            "status": "success",
            "data": {
                "location": {"lat": lat, "lon": lon},
                "current": current,
                "daily": daily,
            },
        }

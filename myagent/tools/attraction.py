"""
景点搜索与推荐工具 (Attraction Search Tool)

支持的API提供商（通过环境变量 ATTRACTION_PROVIDER 选择）：
- amap   : 高德地图 Web服务 API（默认，国内推荐）
- baidu  : 百度地图 Place API
- google : Google Places API（境外推荐）
- mock   : Mock模式，返回模拟数据（无需API Key）

必需环境变量（根据所选provider）：
- AMAP_KEY        : 高德 API Key
- BAIDU_MAP_AK    : 百度 API Key
- GOOGLE_MAPS_KEY : Google Maps API Key
- MOCK_MODE=true  : 全局Mock开关（优先级最高）
"""

import os
import random
from typing import Any, Dict, List, Optional

import requests

from .base import BaseTool


# ── Mock数据 ──────────────────────────────────────────────────────────────────

_MOCK_ATTRACTIONS: Dict[str, List[Dict]] = {
    "杭州": [
        {"name": "西湖", "location": {"lat": 30.2590, "lng": 120.1551},
         "address": "杭州市西湖区龙井路1号", "rating": 4.9,
         "ticket_price": 0, "opening_hours": "全天", "type": "自然风光"},
        {"name": "灵隐寺", "location": {"lat": 30.2405, "lng": 120.1017},
         "address": "杭州市西湖区法云弄1号", "rating": 4.7,
         "ticket_price": 75, "opening_hours": "07:00-18:00", "type": "宗教文化"},
        {"name": "雷峰塔", "location": {"lat": 30.2317, "lng": 120.1483},
         "address": "杭州市西湖区南山路15号", "rating": 4.6,
         "ticket_price": 40, "opening_hours": "08:00-20:00", "type": "历史古迹"},
        {"name": "西溪湿地", "location": {"lat": 30.2680, "lng": 120.0740},
         "address": "杭州市西湖区天目山路518号", "rating": 4.5,
         "ticket_price": 80, "opening_hours": "08:30-17:00", "type": "自然风光"},
        {"name": "宋城景区", "location": {"lat": 30.1840, "lng": 120.1200},
         "address": "杭州市西湖区之江路148号", "rating": 4.5,
         "ticket_price": 260, "opening_hours": "09:00-21:30", "type": "主题公园"},
        {"name": "中国丝绸博物馆", "location": {"lat": 30.2198, "lng": 120.1434},
         "address": "杭州市西湖区玉皇山路73-1号", "rating": 4.4,
         "ticket_price": 0, "opening_hours": "09:00-17:00", "type": "博物馆"},
        {"name": "九溪烟树", "location": {"lat": 30.1910, "lng": 120.1140},
         "address": "杭州市西湖区九溪", "rating": 4.6,
         "ticket_price": 0, "opening_hours": "全天", "type": "自然风光"},
    ],
    "苏州": [
        {"name": "拙政园", "location": {"lat": 31.3244, "lng": 120.6317},
         "address": "苏州市姑苏区东北街178号", "rating": 4.8,
         "ticket_price": 90, "opening_hours": "07:30-17:30", "type": "古典园林"},
        {"name": "狮子林", "location": {"lat": 31.3197, "lng": 120.6338},
         "address": "苏州市姑苏区园林路23号", "rating": 4.6,
         "ticket_price": 40, "opening_hours": "07:30-17:30", "type": "古典园林"},
        {"name": "苏州博物馆", "location": {"lat": 31.3224, "lng": 120.6283},
         "address": "苏州市姑苏区东北街204号", "rating": 4.8,
         "ticket_price": 0, "opening_hours": "09:00-17:00", "type": "博物馆"},
        {"name": "平江历史街区", "location": {"lat": 31.3262, "lng": 120.6413},
         "address": "苏州市姑苏区平江路", "rating": 4.6,
         "ticket_price": 0, "opening_hours": "全天", "type": "历史街区"},
        {"name": "留园", "location": {"lat": 31.3270, "lng": 120.5905},
         "address": "苏州市姑苏区留园路338号", "rating": 4.7,
         "ticket_price": 45, "opening_hours": "07:30-17:30", "type": "古典园林"},
        {"name": "虎丘", "location": {"lat": 31.3533, "lng": 120.5618},
         "address": "苏州市姑苏区虎丘山风景名胜区", "rating": 4.7,
         "ticket_price": 80, "opening_hours": "07:30-18:00", "type": "历史古迹"},
    ],
    "北京": [
        {"name": "故宫博物院", "location": {"lat": 39.9163, "lng": 116.3972},
         "address": "北京市东城区景山前街4号", "rating": 4.9,
         "ticket_price": 60, "opening_hours": "08:30-17:00", "type": "历史古迹"},
        {"name": "颐和园", "location": {"lat": 39.9990, "lng": 116.2754},
         "address": "北京市海淀区新建宫门路19号", "rating": 4.8,
         "ticket_price": 30, "opening_hours": "06:30-20:00", "type": "皇家园林"},
        {"name": "天坛公园", "location": {"lat": 39.8823, "lng": 116.4066},
         "address": "北京市东城区天坛东里甲1号", "rating": 4.7,
         "ticket_price": 35, "opening_hours": "06:00-22:00", "type": "历史古迹"},
        {"name": "长城（八达岭）", "location": {"lat": 40.3594, "lng": 116.0199},
         "address": "北京市延庆区八达岭特区", "rating": 4.8,
         "ticket_price": 65, "opening_hours": "07:30-17:30", "type": "历史古迹"},
        {"name": "国家博物馆", "location": {"lat": 39.9038, "lng": 116.3975},
         "address": "北京市东城区东长安街16号", "rating": 4.7,
         "ticket_price": 0, "opening_hours": "09:00-17:00", "type": "博物馆"},
        {"name": "南锣鼓巷", "location": {"lat": 39.9360, "lng": 116.4040},
         "address": "北京市东城区南锣鼓巷", "rating": 4.3,
         "ticket_price": 0, "opening_hours": "全天", "type": "历史街区"},
    ],
    "上海": [
        {"name": "外滩", "location": {"lat": 31.2397, "lng": 121.4899},
         "address": "上海市黄浦区中山东一路", "rating": 4.8,
         "ticket_price": 0, "opening_hours": "全天", "type": "城市景观"},
        {"name": "豫园", "location": {"lat": 31.2275, "lng": 121.4919},
         "address": "上海市黄浦区安仁街137号", "rating": 4.6,
         "ticket_price": 40, "opening_hours": "08:30-17:00", "type": "古典园林"},
        {"name": "上海博物馆", "location": {"lat": 31.2296, "lng": 121.4733},
         "address": "上海市黄浦区人民大道201号", "rating": 4.8,
         "ticket_price": 0, "opening_hours": "09:00-17:00", "type": "博物馆"},
        {"name": "迪士尼乐园", "location": {"lat": 31.1440, "lng": 121.6570},
         "address": "上海市浦东新区川沙新镇", "rating": 4.7,
         "ticket_price": 499, "opening_hours": "09:00-21:30", "type": "主题公园"},
    ],
    "default": [
        {"name": "市中心广场", "location": {"lat": 30.0, "lng": 120.0},
         "address": "市中心", "rating": 4.0,
         "ticket_price": 0, "opening_hours": "全天", "type": "城市广场"},
        {"name": "历史博物馆", "location": {"lat": 30.01, "lng": 120.01},
         "address": "博物馆路1号", "rating": 4.3,
         "ticket_price": 20, "opening_hours": "09:00-17:00", "type": "博物馆"},
    ],
}

_TYPE_KEYWORDS = {
    "博物馆": ["博物馆", "展览馆", "纪念馆"],
    "自然风光": ["湖", "山", "公园", "湿地", "森林", "风景"],
    "古典园林": ["园", "花园", "庭院"],
    "历史古迹": ["寺", "塔", "古城", "城墙", "宫", "殿"],
    "历史街区": ["古街", "老街", "历史街"],
}


def _filter_by_keyword(attractions: List[Dict], keyword: str) -> List[Dict]:
    """根据关键字模糊过滤"""
    if not keyword:
        return attractions
    kw = keyword.lower()
    matched = [a for a in attractions if kw in a["name"].lower() or kw in a["type"].lower()]
    return matched if matched else attractions


def _filter_by_type(attractions: List[Dict], types: Optional[str]) -> List[Dict]:
    if not types:
        return attractions
    matched = [a for a in attractions if types in a["type"]]
    return matched if matched else attractions


# ── 工具类 ────────────────────────────────────────────────────────────────────

class AttractionSearchTool(BaseTool):
    """景点搜索与推荐工具"""

    def __init__(self):
        self._mock = os.getenv("MOCK_MODE", "false").lower() == "true"
        self._provider = os.getenv("ATTRACTION_PROVIDER", "amap").lower()
        if self._mock:
            self._provider = "mock"

    # ── BaseTool 接口 ──────────────────────────────────────────────────────────

    @property
    def name(self) -> str:
        return "search_attractions"

    @property
    def description(self) -> str:
        return (
            "根据目的地城市和关键词搜索景点，返回景点列表（含名称、位置、评分、"
            "门票价格、营业时间、类型等信息）。适用于旅行行程中的景点发现与推荐。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "搜索关键词，如'西湖'、'博物馆'、'自然风景'",
                },
                "city": {
                    "type": "string",
                    "description": "目标城市名称，如'杭州'、'北京'",
                },
                "types": {
                    "type": "string",
                    "description": "POI分类过滤，如'博物馆'、'自然风光'、'古典园林'",
                },
                "radius": {
                    "type": "integer",
                    "description": "周边搜索半径（米），不填则全城搜索",
                },
                "limit": {
                    "type": "integer",
                    "description": "期望返回数量，默认10",
                    "default": 10,
                },
            },
            "required": ["keyword"],
        }

    def _provider_name(self) -> str:
        return self._provider

    def _execute(self, keyword: str, city: str = None, types: str = None,
                 radius: int = None, limit: int = 10) -> Dict[str, Any]:
        if self._mock:
            return self._mock_search(keyword, city, types, limit)
        if self._provider == "amap":
            return self._amap_search(keyword, city, types, radius, limit)
        if self._provider == "baidu":
            return self._baidu_search(keyword, city, types, radius, limit)
        if self._provider == "google":
            return self._google_search(keyword, city, types, radius, limit)
        return self.error_response("UNKNOWN_PROVIDER", f"未知提供商: {self._provider}")

    # ── Mock ───────────────────────────────────────────────────────────────────

    def _mock_search(self, keyword: str, city: Optional[str],
                     types: Optional[str], limit: int) -> Dict[str, Any]:
        pool = _MOCK_ATTRACTIONS.get(city, _MOCK_ATTRACTIONS["default"])
        # 若城市未命中，尝试模糊匹配
        if city and city not in _MOCK_ATTRACTIONS:
            for k, v in _MOCK_ATTRACTIONS.items():
                if k in city or city in k:
                    pool = v
                    break
        results = _filter_by_keyword(pool, keyword)
        results = _filter_by_type(results, types)
        results = results[:limit]
        return {
            "status": "success",
            "data": {
                "total": len(results),
                "attractions": results,
                "execution_metadata": {"duration_ms": 50, "provider": "mock"},
            },
        }

    # ── 高德地图 ───────────────────────────────────────────────────────────────

    def _amap_search(self, keyword: str, city: Optional[str], types: Optional[str],
                     radius: Optional[int], limit: int) -> Dict[str, Any]:
        api_key = os.getenv("AMAP_KEY")
        if not api_key:
            return self.error_response("INVALID_KEY", "未配置 AMAP_KEY 环境变量")

        params = {
            "key": api_key,
            "keywords": keyword,
            "offset": min(limit, 25),
            "output": "json",
        }
        if city:
            params["city"] = city
        if types:
            params["types"] = types
        if radius:
            params["radius"] = radius

        try:
            resp = requests.get(
                "https://restapi.amap.com/v3/place/text",
                params=params, timeout=10
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        if raw.get("status") != "1":
            info = raw.get("info", "未知错误")
            if "KEY" in info.upper():
                return self.error_response("INVALID_KEY", "API Key无效")
            if raw.get("infocode") == "10021":
                return self.error_response("RATE_LIMITED", "请求过于频繁")
            return self.error_response("API_ERROR", info)

        pois = raw.get("pois", [])
        if not pois:
            return self.error_response("NO_RESULTS", f"未找到关键词[{keyword}]相关景点")

        attractions = []
        for p in pois:
            location_str = p.get("location", "0,0")
            try:
                lng_str, lat_str = location_str.split(",")
                loc = {"lat": float(lat_str), "lng": float(lng_str)}
            except Exception:
                loc = {"lat": 0.0, "lng": 0.0}

            biz = p.get("biz_ext", {})
            rating_raw = biz.get("rating", "0")
            try:
                rating = float(rating_raw)
            except Exception:
                rating = 0.0

            cost_raw = biz.get("cost", "0")
            try:
                ticket_price = float(cost_raw)
            except Exception:
                ticket_price = 0.0

            attractions.append({
                "name": p.get("name", ""),
                "location": loc,
                "address": p.get("address", ""),
                "rating": rating,
                "ticket_price": ticket_price,
                "opening_hours": p.get("opentime_today", "未知"),
                "type": p.get("type", ""),
            })

        return {
            "status": "success",
            "data": {
                "total": len(attractions),
                "attractions": attractions,
            },
        }

    # ── 百度地图 ───────────────────────────────────────────────────────────────

    def _baidu_search(self, keyword: str, city: Optional[str], types: Optional[str],
                      radius: Optional[int], limit: int) -> Dict[str, Any]:
        ak = os.getenv("BAIDU_MAP_AK")
        if not ak:
            return self.error_response("INVALID_KEY", "未配置 BAIDU_MAP_AK 环境变量")

        params = {
            "ak": ak,
            "query": keyword,
            "region": city or "全国",
            "page_size": min(limit, 20),
            "output": "json",
        }
        if types:
            params["tag"] = types

        try:
            resp = requests.get(
                "http://api.map.baidu.com/place/v2/search",
                params=params, timeout=10
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        if raw.get("status") != 0:
            msg = raw.get("message", "未知错误")
            if raw.get("status") == 2:
                return self.error_response("INVALID_KEY", "百度AK无效或无权限")
            return self.error_response("API_ERROR", msg)

        results = raw.get("results", [])
        if not results:
            return self.error_response("NO_RESULTS", f"未找到关键词[{keyword}]相关景点")

        attractions = []
        for r in results:
            loc = r.get("location", {})
            detail = r.get("detail_info", {})
            attractions.append({
                "name": r.get("name", ""),
                "location": {"lat": loc.get("lat", 0.0), "lng": loc.get("lng", 0.0)},
                "address": r.get("address", ""),
                "rating": detail.get("overall_rating", 0.0),
                "ticket_price": 0.0,
                "opening_hours": detail.get("shop_hours", "未知"),
                "type": r.get("std_tag", ""),
            })

        return {
            "status": "success",
            "data": {
                "total": len(attractions),
                "attractions": attractions,
            },
        }

    # ── Google Places ──────────────────────────────────────────────────────────

    def _google_search(self, keyword: str, city: Optional[str], types: Optional[str],
                       radius: Optional[int], limit: int) -> Dict[str, Any]:
        api_key = os.getenv("GOOGLE_MAPS_KEY")
        if not api_key:
            return self.error_response("INVALID_KEY", "未配置 GOOGLE_MAPS_KEY 环境变量")

        query = f"{keyword} {city}" if city else keyword
        params = {
            "query": query,
            "key": api_key,
            "language": "zh-CN",
        }
        if types:
            params["type"] = types

        try:
            resp = requests.get(
                "https://maps.googleapis.com/maps/api/place/textsearch/json",
                params=params, timeout=10
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        api_status = raw.get("status", "")
        if api_status == "REQUEST_DENIED":
            return self.error_response("INVALID_KEY", "Google API Key无效")
        if api_status == "OVER_QUERY_LIMIT":
            return self.error_response("RATE_LIMITED", "Google API配额已用完")
        if api_status == "ZERO_RESULTS":
            return self.error_response("NO_RESULTS", f"未找到关键词[{keyword}]相关景点")
        if api_status != "OK":
            return self.error_response("API_ERROR", f"Google Places API错误: {api_status}")

        places = raw.get("results", [])[:limit]
        attractions = []
        for p in places:
            loc = p.get("geometry", {}).get("location", {})
            attractions.append({
                "name": p.get("name", ""),
                "location": {"lat": loc.get("lat", 0.0), "lng": loc.get("lng", 0.0)},
                "address": p.get("formatted_address", ""),
                "rating": p.get("rating", 0.0),
                "ticket_price": 0.0,
                "opening_hours": "请参考官网",
                "type": ", ".join(p.get("types", [])),
            })

        return {
            "status": "success",
            "data": {
                "total": len(attractions),
                "attractions": attractions,
            },
        }

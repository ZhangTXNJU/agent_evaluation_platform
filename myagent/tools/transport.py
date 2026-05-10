"""
交通与距离计算工具 (Transport & Distance Tool)

支持的API提供商（通过环境变量 TRANSPORT_PROVIDER 选择）：
- amap    : 高德地图路径规划 API（默认，国内推荐）
- baidu   : 百度地图路线规划 API
- google  : Google Routes API（国际/跨国）
- mock    : Mock模式

必需环境变量：
- AMAP_KEY        : 高德 API Key
- BAIDU_MAP_AK    : 百度 API Key
- GOOGLE_MAPS_KEY : Google Maps API Key
- MOCK_MODE=true  : 全局Mock开关
"""

import math
import os
from typing import Any, Dict, List, Optional, Tuple

import requests

from .base import BaseTool


# ── 地球距离计算（Haversine公式）──────────────────────────────────────────────

def _haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """计算两点之间的直线距离（米）"""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


# Mock速度估算（米/秒）
_MODE_SPEEDS = {
    "driving": 12.0,    # ~43km/h 考虑城市拥堵
    "walking": 1.2,     # ~4.3km/h
    "transit": 8.0,     # ~28km/h 含步行换乘
    "bicycling": 3.5,   # ~12.6km/h
}

_MODE_DETOUR = {
    "driving": 1.35,
    "walking": 1.20,
    "transit": 1.50,
    "bicycling": 1.25,
}

_MODE_CN = {
    "driving": "驾车",
    "walking": "步行",
    "transit": "公共交通",
    "bicycling": "骑行",
}


def _mock_route(origin: Tuple[float, float], destination: Tuple[float, float],
                mode: str) -> Dict[str, Any]:
    """基于Haversine公式模拟路线"""
    straight = _haversine_meters(origin[0], origin[1], destination[0], destination[1])
    detour = _MODE_DETOUR.get(mode, 1.3)
    distance_m = int(straight * detour)
    speed = _MODE_SPEEDS.get(mode, 8.0)
    duration_s = int(distance_m / speed)

    def fmt_duration(s: int) -> str:
        if s < 60:
            return f"{s}秒"
        m = s // 60
        if m < 60:
            return f"{m}分钟"
        return f"{m // 60}小时{m % 60}分钟"

    return {
        "distance_meters": distance_m,
        "duration_seconds": duration_s,
        "duration_text": fmt_duration(duration_s),
        "mode": mode,
        "steps_summary": f"经{_MODE_CN.get(mode,'未知')}约{distance_m // 1000:.1f}公里",
    }


# ── 工具类 ────────────────────────────────────────────────────────────────────

class TransportDistanceTool(BaseTool):
    """交通与距离计算工具：路径规划和距离矩阵"""

    def __init__(self):
        self._mock = os.getenv("MOCK_MODE", "false").lower() == "true"
        self._provider = os.getenv("TRANSPORT_PROVIDER", "amap").lower()
        if self._mock:
            self._provider = "mock"

    @property
    def name(self) -> str:
        return "calculate_distance"

    @property
    def description(self) -> str:
        return (
            "计算两点或多点间的路径距离和预计耗时，支持驾车、步行、公共交通、骑行等出行方式。"
            "用于行程顺序编排、时间冲突检测以及出行方式优化。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "origin": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "起点坐标 [lat, lng]，如 [30.25, 120.16]",
                },
                "destination": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "终点坐标 [lat, lng]",
                },
                "mode": {
                    "type": "string",
                    "enum": ["driving", "walking", "transit", "bicycling"],
                    "description": "出行方式，默认 driving（驾车）",
                    "default": "driving",
                },
                "waypoints": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "途经点坐标列表（可选），格式同 origin",
                },
                "points": {
                    "type": "array",
                    "items": {"type": "array", "items": {"type": "number"}},
                    "description": "距离矩阵模式：传入多个点，计算两两之间的距离/耗时",
                },
            },
        }

    def _provider_name(self) -> str:
        return self._provider

    def _execute(self, origin: List = None, destination: List = None,
                 mode: str = "driving", waypoints: List = None,
                 points: List = None) -> Dict[str, Any]:
        mode = mode or "driving"
        if mode not in ("driving", "walking", "transit", "bicycling"):
            return self.error_response("INVALID_MODE", f"不支持的出行方式: {mode}")

        # 距离矩阵模式
        if points and len(points) >= 2:
            return self._distance_matrix(points, mode)

        # 单路线模式
        if not origin or not destination:
            return self.error_response("MISSING_PARAMS", "需要提供 origin 和 destination，或 points 列表")

        try:
            o = (float(origin[0]), float(origin[1]))
            d = (float(destination[0]), float(destination[1]))
        except (IndexError, TypeError, ValueError):
            return self.error_response("INVALID_COORDS", "坐标格式错误，应为 [lat, lng]")

        if not (-90 <= o[0] <= 90 and -180 <= o[1] <= 180):
            return self.error_response("INVALID_COORDS", f"起点坐标无效: {o}")
        if not (-90 <= d[0] <= 90 and -180 <= d[1] <= 180):
            return self.error_response("INVALID_COORDS", f"终点坐标无效: {d}")

        wps = []
        if waypoints:
            for wp in waypoints:
                try:
                    wps.append((float(wp[0]), float(wp[1])))
                except Exception:
                    pass

        if self._mock:
            return self._mock_route_result(o, d, mode, wps)
        if self._provider == "amap":
            return self._amap_route(o, d, mode, wps)
        if self._provider == "baidu":
            return self._baidu_route(o, d, mode, wps)
        if self._provider == "google":
            return self._google_route(o, d, mode, wps)
        return self.error_response("UNKNOWN_PROVIDER", f"未知提供商: {self._provider}")

    # ── 距离矩阵 ───────────────────────────────────────────────────────────────

    def _distance_matrix(self, points: List, mode: str) -> Dict[str, Any]:
        """计算多点两两距离矩阵"""
        n = len(points)
        matrix = []
        for i in range(n):
            row = []
            for j in range(n):
                if i == j:
                    row.append({"distance_meters": 0, "duration_seconds": 0, "duration_text": "0分钟"})
                else:
                    try:
                        o = (float(points[i][0]), float(points[i][1]))
                        d = (float(points[j][0]), float(points[j][1]))
                    except Exception:
                        row.append(self.error_response("INVALID_COORDS", f"点{i}或{j}坐标无效"))
                        continue
                    if self._mock:
                        route = _mock_route(o, d, mode)
                        row.append({
                            "distance_meters": route["distance_meters"],
                            "duration_seconds": route["duration_seconds"],
                            "duration_text": route["duration_text"],
                        })
                    else:
                        # 真实API模式：逐对调用
                        result = self._execute(origin=list(points[i]),
                                               destination=list(points[j]),
                                               mode=mode)
                        if result["status"] == "success":
                            r = result["data"]["route"]
                            row.append({
                                "distance_meters": r["distance_meters"],
                                "duration_seconds": r["duration_seconds"],
                                "duration_text": r["duration_text"],
                            })
                        else:
                            row.append({"error": result.get("error", {}).get("message", "查询失败")})
            matrix.append(row)

        return {
            "status": "success",
            "data": {
                "mode": mode,
                "size": n,
                "matrix": matrix,
                "execution_metadata": {
                    "duration_ms": 50 * n * n,
                    "provider": self._provider,
                },
            },
        }

    # ── Mock ───────────────────────────────────────────────────────────────────

    def _mock_route_result(self, origin: Tuple, destination: Tuple,
                           mode: str, waypoints: List[Tuple]) -> Dict[str, Any]:
        if waypoints:
            # 累加各段距离
            total_dist = 0
            total_dur = 0
            all_points = [origin] + waypoints + [destination]
            for i in range(len(all_points) - 1):
                seg = _mock_route(all_points[i], all_points[i + 1], mode)
                total_dist += seg["distance_meters"]
                total_dur += seg["duration_seconds"]

            def fmt(s: int) -> str:
                m = s // 60
                return f"{m}分钟" if m < 60 else f"{m // 60}小时{m % 60}分钟"

            route = {
                "distance_meters": total_dist,
                "duration_seconds": total_dur,
                "duration_text": fmt(total_dur),
                "mode": mode,
                "steps_summary": f"经过{len(waypoints)}个途经点",
            }
        else:
            route = _mock_route(origin, destination, mode)

        return {
            "status": "success",
            "data": {
                "route": route,
                "execution_metadata": {"duration_ms": 40, "provider": "mock"},
            },
        }

    # ── 高德地图 ───────────────────────────────────────────────────────────────

    def _amap_route(self, origin: Tuple, destination: Tuple,
                    mode: str, waypoints: List[Tuple]) -> Dict[str, Any]:
        api_key = os.getenv("AMAP_KEY")
        if not api_key:
            return self.error_response("INVALID_KEY", "未配置 AMAP_KEY 环境变量")

        # 高德坐标格式：lng,lat
        origin_str = f"{origin[1]},{origin[0]}"
        dest_str = f"{destination[1]},{destination[0]}"

        _mode_endpoint = {
            "driving": "https://restapi.amap.com/v3/direction/driving",
            "walking": "https://restapi.amap.com/v3/direction/walking",
            "transit": "https://restapi.amap.com/v3/direction/transit/integrated",
            "bicycling": "https://restapi.amap.com/v4/direction/bicycling",
        }
        url = _mode_endpoint[mode]

        params = {
            "key": api_key,
            "origin": origin_str,
            "destination": dest_str,
            "output": "json",
        }
        if waypoints and mode == "driving":
            params["waypoints"] = "|".join(f"{w[1]},{w[0]}" for w in waypoints)

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        status = raw.get("status", "0")
        if status != "1":
            info = raw.get("info", "未知错误")
            if "KEY" in info.upper():
                return self.error_response("INVALID_KEY", "API Key无效")
            if raw.get("infocode") == "10021":
                return self.error_response("RATE_LIMITED", "请求过于频繁")
            return self.error_response("API_ERROR", info)

        try:
            route_data = raw["route"]
            if mode == "transit":
                path = route_data["transits"][0]
                distance = int(path.get("distance", 0))
                duration = int(path.get("duration", 0))
                summary = "公交路线"
            else:
                path = route_data["paths"][0]
                distance = int(path.get("distance", 0))
                duration = int(path.get("duration", 0))
                summary = path.get("strategy", "推荐路线")
        except (KeyError, IndexError):
            return self.error_response("NO_ROUTE", "未找到可用路线", suggestion="尝试其他出行方式")

        def fmt(s: int) -> str:
            m = s // 60
            return f"{m}分钟" if m < 60 else f"{m // 60}小时{m % 60}分钟"

        return {
            "status": "success",
            "data": {
                "route": {
                    "distance_meters": distance,
                    "duration_seconds": duration,
                    "duration_text": fmt(duration),
                    "mode": mode,
                    "steps_summary": summary,
                },
            },
        }

    # ── 百度地图 ───────────────────────────────────────────────────────────────

    def _baidu_route(self, origin: Tuple, destination: Tuple,
                     mode: str, waypoints: List[Tuple]) -> Dict[str, Any]:
        ak = os.getenv("BAIDU_MAP_AK")
        if not ak:
            return self.error_response("INVALID_KEY", "未配置 BAIDU_MAP_AK 环境变量")

        _mode_path = {
            "driving": "driving",
            "walking": "walking",
            "transit": "transit",
            "bicycling": "riding",
        }
        url = f"https://api.map.baidu.com/direction/v2/{_mode_path[mode]}"

        params = {
            "ak": ak,
            "origin": f"{origin[0]},{origin[1]}",
            "destination": f"{destination[0]},{destination[1]}",
            "output": "json",
        }

        try:
            resp = requests.get(url, params=params, timeout=10)
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        if raw.get("status") != 0:
            msg = raw.get("message", "未知错误")
            if raw.get("status") == 2:
                return self.error_response("INVALID_KEY", "百度AK无效")
            return self.error_response("API_ERROR", msg)

        try:
            result = raw["result"]
            if mode == "transit":
                path = result["routes"][0]["steps"][0]
                distance = result.get("distance", 0)
                duration = result.get("duration", 0)
            else:
                path = result["routes"][0]
                distance = path.get("distance", 0)
                duration = path.get("duration", 0)
        except (KeyError, IndexError):
            return self.error_response("NO_ROUTE", "未找到可用路线", suggestion="尝试其他出行方式")

        def fmt(s: int) -> str:
            m = s // 60
            return f"{m}分钟" if m < 60 else f"{m // 60}小时{m % 60}分钟"

        return {
            "status": "success",
            "data": {
                "route": {
                    "distance_meters": int(distance),
                    "duration_seconds": int(duration),
                    "duration_text": fmt(int(duration)),
                    "mode": mode,
                    "steps_summary": "百度地图路线",
                },
            },
        }

    # ── Google Routes ──────────────────────────────────────────────────────────

    def _google_route(self, origin: Tuple, destination: Tuple,
                      mode: str, waypoints: List[Tuple]) -> Dict[str, Any]:
        api_key = os.getenv("GOOGLE_MAPS_KEY")
        if not api_key:
            return self.error_response("INVALID_KEY", "未配置 GOOGLE_MAPS_KEY 环境变量")

        _travel_mode = {
            "driving": "DRIVE",
            "walking": "WALK",
            "transit": "TRANSIT",
            "bicycling": "BICYCLE",
        }

        body = {
            "origin": {"location": {"latLng": {"latitude": origin[0], "longitude": origin[1]}}},
            "destination": {"location": {"latLng": {"latitude": destination[0], "longitude": destination[1]}}},
            "travelMode": _travel_mode[mode],
            "languageCode": "zh-CN",
        }

        if waypoints:
            body["intermediates"] = [
                {"location": {"latLng": {"latitude": w[0], "longitude": w[1]}}}
                for w in waypoints
            ]

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.description",
        }

        try:
            resp = requests.post(
                "https://routes.googleapis.com/directions/v2:computeRoutes",
                json=body, headers=headers, timeout=15
            )
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("NETWORK_ERROR", f"网络请求失败: {e}")

        if "error" in raw:
            err = raw["error"]
            code = err.get("code", 0)
            if code == 403:
                return self.error_response("INVALID_KEY", "Google API Key无效")
            if code == 429:
                return self.error_response("RATE_LIMITED", "Google API配额超限")
            return self.error_response("API_ERROR", err.get("message", "未知错误"))

        routes = raw.get("routes", [])
        if not routes:
            return self.error_response("NO_ROUTE", "未找到可用路线", suggestion="尝试其他出行方式")

        route = routes[0]
        distance = route.get("distanceMeters", 0)
        # duration 格式: "1234s"
        dur_str = route.get("duration", "0s")
        try:
            duration_s = int(dur_str.rstrip("s"))
        except Exception:
            duration_s = 0

        def fmt(s: int) -> str:
            m = s // 60
            return f"{m}分钟" if m < 60 else f"{m // 60}小时{m % 60}分钟"

        return {
            "status": "success",
            "data": {
                "route": {
                    "distance_meters": distance,
                    "duration_seconds": duration_s,
                    "duration_text": fmt(duration_s),
                    "mode": mode,
                    "steps_summary": route.get("description", "Google Maps路线"),
                },
            },
        }

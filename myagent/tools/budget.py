"""
预算计算与汇率工具 (Budget & Currency Tool)

汇率数据来源（通过环境变量 CURRENCY_PROVIDER 选择）：
- exchangerate  : ExchangeRate-API（默认，免费无需Key，月1500次）
- frankfurter   : Frankfurter（开源，欧洲央行数据，无需Key）
- mock          : Mock模式

物价数据：采用本地模型估算（预置各城市参考价格表）。
可通过环境变量 MOCK_MODE=true 全局切换Mock模式。
"""

import os
from typing import Any, Dict, List, Optional

import requests

from .base import BaseTool


# ── 本地参考价格表 ─────────────────────────────────────────────────────────────

# 酒店每晚每间均价（CNY）
_HOTEL_PRICES = {
    "budget": {  # 经济型（快捷酒店、青旅）
        "default": 150,
        "北京": 200, "上海": 220, "杭州": 180, "苏州": 160,
        "广州": 160, "深圳": 200, "成都": 150, "西安": 130,
        "三亚": 280, "丽江": 200, "厦门": 180, "南京": 160,
    },
    "mid": {  # 舒适型（三四星酒店）
        "default": 350,
        "北京": 480, "上海": 520, "杭州": 400, "苏州": 350,
        "广州": 380, "深圳": 450, "成都": 320, "西安": 280,
        "三亚": 650, "丽江": 450, "厦门": 400, "南京": 360,
    },
    "luxury": {  # 豪华型（五星酒店）
        "default": 900,
        "北京": 1200, "上海": 1400, "杭州": 1000, "苏州": 900,
        "广州": 950, "深圳": 1100, "成都": 800, "西安": 750,
        "三亚": 1800, "丽江": 1200, "厦门": 1000, "南京": 900,
    },
}

# 餐饮每人每天均价（CNY）
_MEAL_PRICES = {
    "default": 120,
    "北京": 150, "上海": 160, "杭州": 140, "苏州": 130,
    "广州": 140, "深圳": 160, "成都": 100, "西安": 90,
    "三亚": 180, "丽江": 130, "厦门": 130, "南京": 120,
}

# 城内交通每人每天均价（CNY）
_LOCAL_TRANSPORT = {
    "default": 60,
    "北京": 80, "上海": 80, "杭州": 60, "苏州": 50,
    "广州": 60, "深圳": 70, "成都": 50, "西安": 40,
    "三亚": 100, "丽江": 80, "厦门": 60, "南京": 55,
}

# 城际交通参考（元/人，单程，均值）
_INTERCITY_TRANSPORT = {
    "default": 300,
    "北京-上海": 553, "上海-杭州": 73, "杭州-苏州": 78,
    "南京-苏州": 50, "南京-杭州": 73, "上海-苏州": 30,
}

# Mock汇率（相对CNY）
_MOCK_RATES = {
    "CNY": 1.0,
    "USD": 0.138, "EUR": 0.128, "GBP": 0.109, "JPY": 20.5,
    "KRW": 186.0, "HKD": 1.08, "SGD": 0.186, "THB": 4.98,
    "AUD": 0.213, "CAD": 0.190,
}


def _get_city_price(table: Dict, city: str) -> float:
    """从价格表中获取城市价格，找不到用default"""
    for k, v in table.items():
        if k in city or city in k:
            return float(v)
    return float(table.get("default", 0))


# ── 工具类 ────────────────────────────────────────────────────────────────────

class BudgetCurrencyTool(BaseTool):
    """预算计算与汇率工具"""

    def __init__(self):
        self._mock = os.getenv("MOCK_MODE", "false").lower() == "true"
        self._currency_provider = os.getenv("CURRENCY_PROVIDER", "exchangerate").lower()
        if self._mock:
            self._currency_provider = "mock"

    @property
    def name(self) -> str:
        return "calculate_budget"

    @property
    def description(self) -> str:
        return (
            "根据目的地城市、旅行天数、人数、景点列表和酒店档次估算旅行总预算及分项明细，"
            "并支持境外游的汇率换算。用于检验行程是否超出用户预算，"
            "并在超支时提供各分项的调优建议。"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "目的地城市，如'杭州'、'北京'",
                },
                "days": {
                    "type": "integer",
                    "description": "旅行天数",
                },
                "num_people": {
                    "type": "integer",
                    "description": "出行人数",
                },
                "attractions": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "景点对象列表，每个对象需包含 ticket_price 字段（门票价格，元）",
                },
                "hotel_level": {
                    "type": "string",
                    "enum": ["budget", "mid", "luxury"],
                    "description": "酒店档次：budget（经济）/ mid（舒适）/ luxury（豪华），默认mid",
                    "default": "mid",
                },
                "budget_limit": {
                    "type": "number",
                    "description": "用户设定的预算上限（元），用于检测是否超支",
                },
                "currency": {
                    "type": "string",
                    "description": "结算币种（ISO 4217），默认CNY",
                    "default": "CNY",
                },
                "from_city": {
                    "type": "string",
                    "description": "出发城市（用于估算城际交通费用），可选",
                },
            },
            "required": ["city", "days", "num_people", "attractions"],
        }

    def _provider_name(self) -> str:
        return self._currency_provider

    def _execute(self, city: str, days: int, num_people: int,
                 attractions: List[Dict], hotel_level: str = "mid",
                 budget_limit: float = None, currency: str = "CNY",
                 from_city: str = None) -> Dict[str, Any]:
        if days < 1:
            return self.error_response("INVALID_PARAMS", "旅行天数不能小于1")
        if num_people < 1:
            return self.error_response("INVALID_PARAMS", "人数不能小于1")
        if hotel_level not in ("budget", "mid", "luxury"):
            hotel_level = "mid"

        # 1. 计算各分项费用（总费用，不区分人数的需乘以人数）
        hotel_per_night = _get_city_price(_HOTEL_PRICES[hotel_level], city)
        accommodation = round(hotel_per_night * days * max(1, num_people // 2), 2)  # 按房间算，2人共一间

        meal_per_person_per_day = _get_city_price(_MEAL_PRICES, city)
        meals = round(meal_per_person_per_day * days * num_people, 2)

        ticket_total = sum(
            float(a.get("ticket_price", 0)) for a in attractions
        ) * num_people
        tickets = round(ticket_total, 2)

        local_per_person_per_day = _get_city_price(_LOCAL_TRANSPORT, city)
        transport_local = round(local_per_person_per_day * days * num_people, 2)

        # 城际交通
        transport_intercity = 0.0
        if from_city:
            key1 = f"{from_city}-{city}"
            key2 = f"{city}-{from_city}"
            intercity_one_way = _INTERCITY_TRANSPORT.get(
                key1, _INTERCITY_TRANSPORT.get(key2, _INTERCITY_TRANSPORT["default"])
            )
            transport_intercity = round(intercity_one_way * 2 * num_people, 2)  # 往返

        other = round((accommodation + meals + tickets + transport_local + transport_intercity) * 0.05, 2)

        total_cny = accommodation + meals + tickets + transport_local + transport_intercity + other

        # 2. 汇率换算
        rate = 1.0
        converted_total = total_cny
        if currency and currency.upper() != "CNY":
            rate_result = self._get_rate("CNY", currency.upper())
            if rate_result["status"] == "error":
                return rate_result
            rate = rate_result["data"]["rate"]
            converted_total = round(total_cny * rate, 2)

        total = converted_total

        # 3. 预算超支检测
        overspent = None
        overspent_percent = None
        if budget_limit is not None and budget_limit > 0:
            # budget_limit 视为同币种
            overspent = round(total - budget_limit, 2)
            overspent_percent = round(overspent / budget_limit * 100, 1)

        # 4. 调优建议
        suggestions = []
        if overspent and overspent > 0:
            hotel_options = {"luxury": "mid", "mid": "budget", "budget": None}
            next_level = hotel_options.get(hotel_level)
            if next_level:
                suggestions.append(f"将酒店档次从{hotel_level}降为{next_level}可节省部分住宿费")
            suggestions.append("可减少高门票景点，选择免费景点替代")
            suggestions.append("考虑选择本地特色餐厅代替高档餐厅")

        data = {
            "total": total,
            "currency": currency.upper() if currency else "CNY",
            "breakdown_cny": {
                "accommodation": accommodation,
                "meals": meals,
                "tickets": tickets,
                "transport_local": transport_local,
                "transport_intercity": transport_intercity,
                "other": other,
            },
            "exchange_info": {
                "from_cny_total": round(total_cny, 2),
                "rate": rate,
                "currency": currency.upper() if currency else "CNY",
            },
            "execution_metadata": {
                "duration_ms": 20,
                "provider": self._currency_provider,
            },
        }

        if budget_limit is not None:
            data["budget_limit"] = budget_limit
            data["overspent"] = overspent
            data["overspent_percent"] = overspent_percent
            data["is_over_budget"] = overspent > 0 if overspent is not None else False
            data["suggestions"] = suggestions

        return {"status": "success", "data": data}

    # ── 汇率查询（作为独立function也可被LLM调用）─────────────────────────────

    def get_exchange_rate(self, from_currency: str = "CNY",
                          to_currency: str = "USD") -> Dict[str, Any]:
        """对外暴露的汇率查询方法，可被Agent直接调用"""
        return self._get_rate(from_currency.upper(), to_currency.upper())

    def _get_rate(self, from_cur: str, to_cur: str) -> Dict[str, Any]:
        if self._mock:
            return self._mock_rate(from_cur, to_cur)
        if self._currency_provider == "exchangerate":
            return self._exchangerate_api(from_cur, to_cur)
        if self._currency_provider == "frankfurter":
            return self._frankfurter(from_cur, to_cur)
        return self._mock_rate(from_cur, to_cur)

    def _mock_rate(self, from_cur: str, to_cur: str) -> Dict[str, Any]:
        if from_cur not in _MOCK_RATES:
            return self.error_response("UNSUPPORTED_CURRENCY", f"不支持的币种: {from_cur}")
        if to_cur not in _MOCK_RATES:
            return self.error_response("UNSUPPORTED_CURRENCY", f"不支持的币种: {to_cur}")
        rate = round(_MOCK_RATES[to_cur] / _MOCK_RATES[from_cur], 6)
        return {
            "status": "success",
            "data": {
                "from": from_cur,
                "to": to_cur,
                "rate": rate,
                "source": "mock",
            },
        }

    def _exchangerate_api(self, from_cur: str, to_cur: str) -> Dict[str, Any]:
        try:
            resp = requests.get(
                f"https://api.exchangerate-api.com/v4/latest/{from_cur}",
                timeout=10
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("EXCHANGE_SERVICE_DOWN", f"汇率服务不可用: {e}")

        rates = raw.get("rates", {})
        if to_cur not in rates:
            return self.error_response("UNSUPPORTED_CURRENCY", f"不支持的币种: {to_cur}")

        rate = round(rates[to_cur], 6)
        return {
            "status": "success",
            "data": {
                "from": from_cur,
                "to": to_cur,
                "rate": rate,
                "source": "exchangerate-api",
            },
        }

    def _frankfurter(self, from_cur: str, to_cur: str) -> Dict[str, Any]:
        try:
            resp = requests.get(
                f"https://api.frankfurter.app/latest",
                params={"from": from_cur, "to": to_cur},
                timeout=10
            )
            resp.raise_for_status()
            raw = resp.json()
        except requests.RequestException as e:
            return self.error_response("EXCHANGE_SERVICE_DOWN", f"汇率服务不可用: {e}")

        if "error" in raw:
            return self.error_response("UNSUPPORTED_CURRENCY", raw["error"])

        rates = raw.get("rates", {})
        if to_cur not in rates:
            return self.error_response("UNSUPPORTED_CURRENCY", f"不支持的币种: {to_cur}")

        rate = round(rates[to_cur], 6)
        return {
            "status": "success",
            "data": {
                "from": from_cur,
                "to": to_cur,
                "rate": rate,
                "source": "frankfurter",
            },
        }


# ── 独立汇率工具（注册为第二个 LLM 工具）────────────────────────────────────

class ExchangeRateTool(BaseTool):
    """汇率查询工具（独立注册，供Agent直接调用）"""

    def __init__(self):
        self._budget_tool = BudgetCurrencyTool()

    @property
    def name(self) -> str:
        return "get_exchange_rate"

    @property
    def description(self) -> str:
        return "查询两种货币之间的实时汇率，用于境外旅游时将人民币换算为当地货币。"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "from_currency": {
                    "type": "string",
                    "description": "源货币代码（ISO 4217），默认CNY",
                    "default": "CNY",
                },
                "to_currency": {
                    "type": "string",
                    "description": "目标货币代码（ISO 4217），如USD、JPY、EUR",
                },
            },
            "required": ["to_currency"],
        }

    def _execute(self, from_currency: str = "CNY", to_currency: str = "USD") -> Dict[str, Any]:
        result = self._budget_tool._get_rate(
            from_currency.upper(), to_currency.upper()
        )
        return result

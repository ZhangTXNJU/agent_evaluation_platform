# HTTP 请求与 JSON 数据传递全链路原理

一句话概括：**HTTP + JSON 是一套让不同程序之间"通话"的协议——发送方把数据对象变成文本字符串，通过网络传过去，接收方再把文本还原成数据对象。**

---

## STAR 分析

### S — 场景（Situation）

你在浏览器里点一个按钮，后端的 Python 服务就能收到你的请求并返回结果。前端用 JavaScript 写，后端用 Python 写，这是两种完全不同的语言——它们怎么互相理解对方发来的数据？

更具体地说，在你的评估平台项目里：

```
评估平台 (Python/FastAPI)  ──发送测试用例──▶  你的Agent (Python/FastAPI)
```

两个独立的 Python 程序，跑在不同的端口上（:8001 和 :8000），它们之间没有任何共享内存、没有任何公共变量。要让平台把 `{"input": "请帮我规划3天北京之旅..."}` 这条数据发给 Agent，必须通过网络。

**没有 HTTP + JSON 会怎样？** 你得自己处理网络连接、自己定义数据格式、自己处理字节流分割——工作量巨大且极易出错。

### T — 任务（Task）

核心挑战就一个：**如何在两台机器（或两个进程）之间，可靠地把"结构化数据"从一方传递给另一方？**

拆开来看有 5 个子问题：
1. 发送方的数据对象（Python dict）怎么变成一个可以发送的格式？
2. 这个格式通过什么"通道"发出去？
3. 接收方怎么知道"一条消息收完了"？
4. 接收方怎么把收到的字节还原成自己能用的数据对象？
5. 如果数据格式不对，怎么发现并拒绝？

### A — 动作（Action）

HTTP + JSON 协议栈分四层解决这个问题：

| 层 | 协议/技术 | 解决的问题 |
|---|---|---|
| **数据表示层** | JSON | dict/对象 ↔ 纯文本字符串 |
| **应用层** | HTTP | 定义请求/响应的语义（方法、路径、头部、状态码） |
| **传输层** | TCP | 可靠传输，自动分包/重组/重传 |
| **网络层** | IP | 把数据包从源地址路由到目标地址 |

### R — 结果（Result）

用上这套协议栈后：
- **开发效率**：发送方一行 `json.dumps()`，接收方一行 `json.loads()`，两端语言可以不同
- **可读性**：JSON 是纯文本，人类可以直接阅读调试
- **可靠性**：TCP 保证数据不丢、不乱序
- **标准化**：任何语言都有 JSON 库和 HTTP 库，生态成熟

---

## 核心原理讲解

### 第1步：你要发送什么？

假设评估平台要发给 Agent 的数据是：

```python
# 这是 Python 内存中的一个 dict 对象
request_data = {
    "input": "请帮我规划一次为期3天的北京之旅，预算控制在3000元以内。",
    "session_config": {
        "case_id": "case_01",
        "difficulty": "easy"
    }
}
```

它在 Python 内存里是一堆指针和引用——你没法直接把它"塞进网线"。你必须先把它**序列化**成一个扁平的字节序列。

### 第2步：序列化 —— 从 Python dict 到 JSON 字符串

```python
import json

# json.dumps() 把 Python 对象 → JSON 字符串
json_string = json.dumps(request_data, ensure_ascii=False)
# 结果（一个字符串）:
# '{"input": "请帮我规划一次为期3天的北京之旅...", "session_config": {"case_id": "case_01", "difficulty": "easy"}}'
```

`json.dumps()` 内部做的事（简化版）：

```
Python dict
  → 遍历每个 key-value
    → key 必然是字符串，加上双引号
    → value 类型判断:
       - str  → 加上双引号，处理转义（\n、\"、\\）
       - int  → 直接转十进制字符串
       - dict → 递归调用自身
       - list → 遍历每个元素递归处理，用 [] 包裹
       - None → 输出 "null"
       - bool → 输出 "true" 或 "false"
  → 最后得到一串扁平的纯文本
```

**关键认知：** JSON 本质上是一个格式约定，不是魔法。它规定了几种基本类型（字符串、数字、布尔、null、数组、对象）如何用文本表示。

### 第3步：把字符串变成字节

网络传输的最小单位是**字节（byte）**，不是字符。所以 JSON 字符串还要再转一次：

```python
# .encode() 把字符串 → 字节序列
body_bytes = json_string.encode('utf-8')
# 结果（bytes 对象）:
# b'{"input": "\xe8\xaf\xb7\xe5\xb8\xae...'
#    ↑ 每个中文字符在 UTF-8 中占 3 个字节
```

`\xe8\xaf\xb7` 就是中文"请"的 UTF-8 编码。UTF-8 是 Unicode 的一种编码方式——把每个码点映射为 1~4 个字节。

### 第4步：套上 HTTP 信封

有了 body（数据体），还需要一个"信封"告诉接收方怎么处理这些数据。这就是 HTTP 请求的格式：

```http
POST /api/eval/run HTTP/1.1
Host: localhost:8000
Content-Type: application/json; charset=utf-8
Content-Length: 156
Connection: keep-alive
                                    ← 空行，分隔头部和正文
{"input": "请帮我规划一次为期3天的北京之旅，预算控制在3000元以内。", "session_config": {"case_id": "case_01", "difficulty": "easy"}}
```

逐字段解释：

| 字段 | 含义 |
|------|------|
| `POST` | HTTP 方法，表示"我要发送数据给你" |
| `/api/eval/run` | 请求路径，告诉服务器"调用哪个处理函数" |
| `HTTP/1.1` | 协议版本 |
| `Host: localhost:8000` | 目标主机和端口 |
| `Content-Type: application/json` | **关键！**告诉接收方"正文是 JSON 格式，用 json 解析器来读" |
| `Content-Length: 156` | 正文有多少字节，接收方据此判断"我收完了没有" |

### 第5步：TCP 分包发送

HTTP 报文被交给 TCP 层。TCP 把它切成多个**数据段（segment）**，每个段带上序号。然后交给 IP 层加上源/目标地址，变成**数据包（packet）**。

```
HTTP 报文（大块）
  → TCP 切分 → [段1: 字节0-999] [段2: 字节1000-1999] [段3: 字节2000-2999]
  → IP 封装 → [包1: src=127.0.0.1:54321 → dst=127.0.0.1:8000, data=段1] ...
  → 网络发送
```

因为是 `localhost` 通信，数据包不经过物理网卡，而是走操作系统的**环回接口（loopback）**——本质上是内核中的一段共享内存。

### 第6步：服务器端接收与重组

Agent 这边的操作系统网卡驱动（或 loopback 驱动）收到 IP 包：

```
IP 包 → 拆掉 IP 头 → TCP 段
  → TCP 层按序号排序、去重、请求重传丢失的段 → 重组成完整的 HTTP 报文
  → 交给应用层（uvicorn / FastAPI）
```

### 第7步：HTTP 解析

FastAPI 底层的 uvicorn 收到字节流后，用 HTTP 解析器（httptools）解析：

```
字节流
  → 解析第一行: "POST /api/eval/run HTTP/1.1" → method=POST, path=/api/eval/run
  → 解析头部: Content-Type=application/json, Content-Length=156
  → 读到空行（\r\n\r\n），标记头部结束
  → 根据 Content-Length=156 继续读 156 字节 → 这就是 body
```

### 第8步：反序列化 —— 从 JSON 字符串到 Python dict

```python
import json

# 服务器端：json.loads() 把 JSON 字符串 → Python 对象
body_str = body_bytes.decode('utf-8')  # 先解码成字符串
python_dict = json.loads(body_str)
# 结果:
# {"input": "请帮我规划...", "session_config": {"case_id": "case_01", "difficulty": "easy"}}
```

`json.loads()` 内部做的事（简化版）：

```
JSON 字符串: '{"input":"...","session_config":{...}}'
  → 词法分析（lexer）:
    '{'  → 开始一个对象
    '"input"' → 一个字符串 key "input"
    ':'  → key-value 分隔符
    '"请帮我规划..."'  → 一个字符串 value
    ','  → 下一个字段
    '"session_config"' → key
    '{'  → 嵌套对象开始
    ...递归...
    '}'  → 嵌套对象结束
    '}'  → 顶层对象结束
  → 构建 Python dict:
    {"input": "请帮我规划...", "session_config": {"case_id": "case_01", ...}}
```

### 第9步：FastAPI / Pydantic 校验

FastAPI 比你多走一步：它不仅把 JSON 变成 dict，还用 **Pydantic** 做类型校验：

```python
from pydantic import BaseModel

class SessionConfig(BaseModel):
    case_id: str
    difficulty: str

class EvalRequest(BaseModel):
    input: str
    session_config: SessionConfig

@app.post("/api/eval/run")
def evaluate(request: EvalRequest):  # ← FastAPI 自动将 JSON 解析为此类型
    user_input = request.input                       # 直接 .input 访问
    case_id = request.session_config.case_id         # 嵌套对象也自动解析
    # ...
```

FastAPI 在调用你的 `evaluate` 函数之前做的事：

```
JSON 字符串
  → json.loads() → Python dict
  → Pydantic 校验:
     - request["input"] 是字符串？√
     - request["session_config"] 是 dict？√
     - request["session_config"]["case_id"] 存在且是字符串？√
     - request["session_config"]["difficulty"] 存在且是字符串？√
  → 构造 EvalRequest 对象: EvalRequest(input=..., session_config=SessionConfig(...))
  → 在函数里，request.input 就是一个正常的 Python 属性
```

如果 `case_id` 没传或者类型不对，FastAPI 会直接返回 422 错误，你的函数根本不会被调用。

---

### 完整数据流图（端到端）

```
发送方 (评估平台)                              接收方 (Mock Agent)
═══════════════                              ═══════════════

Python dict                                  Python 对象 (EvalRequest 实例)
  │                                              ▲
  │ json.dumps()                                 │ Pydantic 校验 + 对象化
  ▼                                              │
JSON 字符串                                      │
  │                                              │
  │ .encode('utf-8')                             │ json.loads()
  ▼                                              │
bytes 字节序列                                   │
  │                                              ▲
  │ httpx 库组装 HTTP 报文                       │ uvicorn HTTP 解析器
  ▼                                              │
HTTP 报文 (文本)                                 │
  │                                              ▲
  │ TCP 层切分成段 + 加序号                      │ TCP 层排序、去重、重组
  ▼                                              │
TCP segments                                    │
  │                                              ▲
  │ IP 层加地址头                                │ IP 层拆地址头
  ▼                                              │
IP packets ──── 网络传输 (或 loopback) ──────────┘
```

### 关键认知

**JSON 不是 Python 独有的。** 任何语言都有 JSON 库：

```javascript
// JavaScript 前端
const body = JSON.stringify({ input: "计划旅行", session_config: { case_id: "01" } });
fetch('http://localhost:8001/api/v1/tasks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body  // ← 和 Python 端完全一样的 JSON 格式
});
```

这就是为什么前端 (JavaScript/TypeScript) 和后端 (Python) 能够通信——它们共享同一个数据表示层：JSON 字符串。

---

## 老张的故事

### 故事背景

老张是评估平台团队的后端开发。功能都开发完了，但他要对接一位算法同事写的 Agent——一个独立的 Python 服务，跑在 `localhost:8000`。

老张需要在评估平台的[执行引擎](E:\codes\agent_evaluate_platform\backend\core\executor.py)里，把每个测试用例发到 Agent，然后拿回结果。

老张打开 `executor.py`，看到之前的开发者留了一段注释：

```python
# 调用 Agent Platform
request_body = {
    "input": case_meta.get("input", ""),
    "session_config": {
        "case_id": case_meta.get("id"),
        "difficulty": case_meta.get("difficulty"),
    },
}
# TODO: 发送 HTTP 请求
```

### 老张的思考

老张想：我手头有一个 Python dict，Agent 那边是一个 FastAPI 接口。怎么把这个 dict 传过去？

他想到了三个方案：

1. **写文件**——平台把数据写到一个文件，Agent 定时读文件，写结果到另一个文件。老张立刻否决了：太慢，两个进程可能同时读写，容易冲突。

2. **用 socket 直接发送**——老张可以自己用 Python 的 `socket` 库发 TCP 消息。但他又想了：我得自己定义消息边界（怎么判断一条消息结束了？），自己处理连接失败、超时，太麻烦了。

3. **用 HTTP + JSON**——HTTP 有成熟的库（httpx），`Content-Length` 头部天然解决了消息边界问题，JSON 是标准格式两端都能解析。而且 Agent 那边已经用 FastAPI 暴露了接口。

老张选了方案 3。

### 老张的实践

以下是老张在项目中实际写的代码（简化但完整可运行）：

```python
# ============================================================
# 文件: executor.py 中的 _call_agent 方法
# 作用: 把测试用例发给 Agent，拿回评估结果
# ============================================================

import httpx      # 第三方 HTTP 客户端库——比 Python 内置的 urllib 更好用
import json       # 虽然 httpx 内部会调用 json，但我们仍需要理解这个包的作用


def _call_agent(self, endpoint: str, case_meta: dict, timeout: int) -> dict:
    """
    向被评估的 Agent 发送一个测试用例，返回 Agent 的响应。

    参数:
        endpoint: Agent 的 URL，例如 "http://localhost:8000/api/eval/run"
        case_meta: 测试用例，例如 {"id": "case_01", "input": "规划3天北京之旅...", ...}
        timeout:   超时时间（秒），超过此时间Agent未响应则放弃

    返回:
        Agent 的响应体，例如 {"output": {...}, "trace": [...], "metrics": {...}}
    """

    # 第1步：构造请求体（Python dict → 后面 httpx 会把它变成 JSON 字符串）
    # 为什么用 dict？因为它是 Python 最自然的数据结构，开发者不用关心最终格式
    request_body = {
        "input": case_meta.get("input", ""),  # 从用例中取 input
        "session_config": {
            "case_id": case_meta.get("id"),         # 把用例ID传过去，Agent可以按case生成不同结果
            "difficulty": case_meta.get("difficulty"),
        },
    }

    # 第2步：创建 HTTP 客户端并发送请求
    # httpx.Client() 底层做了什么？
    #   1. 建立到 localhost:8000 的 TCP 连接（三次握手）
    #   2. 将 request_body dict 序列化为 JSON 字符串: json.dumps(request_body)
    #   3. 将 JSON 字符串按 UTF-8 编码为字节: json_string.encode('utf-8')
    #   4. 组装 HTTP 请求报文（起始行 + 头部 + 正文）
    #   5. 通过 TCP 连接发送报文
    #   6. 等待服务器响应（最长等 timeout 秒）
    #   7. 收到响应后解析 HTTP 响应报文
    #   8. 识别 Content-Type: application/json → 自动 json.loads()
    #   9. 返回 Python dict
    with httpx.Client(timeout=timeout) as client:
        response = client.post(
            endpoint,  # POST /api/eval/run
            json=request_body,  # ← 指定 json= 参数，httpx 自动序列化并设 Content-Type
        )
        # 如果 HTTP 状态码是 4xx 或 5xx，raise_for_status() 抛出异常
        response.raise_for_status()
        # response.json() 把响应体的 JSON 字符串解析为 Python dict
        return response.json()


# ============================================================
# 使用示例（老张在 _evaluate_case 中调用）
# ============================================================
def _evaluate_case(self, case_meta: dict, agent_response: dict, metric_names: list) -> dict:
    """
    对单个用例的 Agent 响应进行多指标评估。

    参数:
        case_meta:       测试用例（包含预期约束、预期工具序列等）
        agent_response:  Agent 的返回 {output, trace, metrics}
        metric_names:    要计算哪些指标，例如 ["success_rate", "tool_accuracy"]

    返回:
        {"case_id": "case_01", "scores": {...}, "details": {...}}
    """

    # 把用例信息和 Agent 响应打包，传给每个指标计算器
    compute_input = {
        "case_meta": case_meta,
        "agent_output": agent_response.get("output", {}),
        "agent_trace": agent_response.get("trace", []),
        "agent_metrics": agent_response.get("metrics", {}),
    }

    scores = {}
    all_details = {}

    # 遍历每个指标，逐一计算
    # MetricRegistry 是一个注册中心——通过字符串名拿到对应的指标计算器实例
    for metric_name in metric_names:
        metric_instance = MetricRegistry.get(metric_name)
        if metric_instance:
            # compute() 是每个指标的入口，输入是 compute_input，输出是 {"score": 0.8, "details": {...}}
            result = metric_instance.compute(compute_input)
            scores[metric_name] = result["score"]
            all_details[metric_name] = result["details"]

    return {
        "case_id": case_meta.get("id"),
        "scores": scores,          # {"success_rate": 0.9, "tool_accuracy": 0.75, ...}
        "details": all_details,    # 每个指标的详细分析
    }
```

### 老张踩的坑

写这段代码时老张犯了两个错误：

**坑1**：老张最初用 `data=` 参数而不是 `json=` 参数传请求体：

```python
# 错误写法
response = client.post(endpoint, data=request_body)
# httpx 不会自动序列化为 JSON！Content-Type 也不会设为 application/json
# 服务器收到的可能是 "input=..." 这种 URL 编码格式，FastAPI 无法解析
```

**正确做法**：

```python
# 正确写法——用 json= 参数
response = client.post(endpoint, json=request_body)
# httpx 自动: json.dumps() + 设 Content-Type: application/json
```

**坑2**：老张忘记处理超时。Agent 那边可能因为 LLM 调用卡住，如果平台这边不设超时，执行线程就会永久阻塞。

```python
# 错误写法
response = client.post(endpoint, json=request_body)  # 默认无超时，可能永远等下去

# 正确写法
response = client.post(endpoint, json=request_body, timeout=120)  # 120 秒不响应就放弃
```

### 老张的收获

写完这段代码后，老张把平台和一个 Mock Agent 同时启动，创建了第一个评估任务。他看到任务状态从 `pending` 变成 `running`，逐条用例进度从 `1/10` 涨到 `10/10`，最后变成 `done`。

他用浏览器打开评估结果页面，看到每个用例的评分、工具调用对比、推理分析——一切数据都来自 Agent 返回的那个 JSON。

老张感叹："原来两个程序之间的通信，说到底就是——**把数据变成字符串，塞进 HTTP 报文的正文里，发出去，对方收到后原样还原**。HTTP 就是信封，JSON 就是信的内容。"

---

## 常见误区与最佳实践

### 误区1：把 `data=` 和 `json=` 搞混

```python
# 错误——data= 不会自动 JSON 序列化
client.post(url, data={"key": "value"})  # 可能变成 key=value 表单格式

# 正确——json= 会自动 json.dumps() 并设 Content-Type
client.post(url, json={"key": "value"})
```

### 误区2：认为 JSON 就是 Python dict

JSON 有 6 种类型：`object`, `array`, `string`, `number`, `boolean`, `null`。Python `True` 对应 JSON `true`，Python `None` 对应 JSON `null`。它们是不同的：

```python
# Python 序列化
json.dumps({"active": True, "extra": None})
# 输出: '{"active": true, "extra": null}'  ← 注意 true 和 null 是小写

# 如果手动拼 JSON 字符串，很容易出错：
bad_json = '{"active": True}'       # ← 错误！JSON 里布尔是 true 不是 True
good_json = '{"active": true}'      # ← 正确
```

### 误区3：忽略 `Content-Type` 头部

服务端（FastAPI）靠 `Content-Type: application/json` 来决定用什么解析器处理请求体。如果不设这个头部，FastAPI 可能把请求体当纯文本而非 JSON 处理，导致 422 或 400 错误。

**最佳实践**：用 httpx 的 `json=` 参数（或 requests 的 `json=` 参数），它会自动设对头部。

### 误区4：不理解为什么中文在 JSON 里变成了 `\uXXXX`

这是 JSON 的默认行为——非 ASCII 字符可以被转义为 Unicode 转义序列。但这不影响数据正确性：

```python
json.dumps({"city": "北京"})
# 默认: '{"city": "\\u5317\\u4eac"}'
# 加 ensure_ascii=False: '{"city": "北京"}'
```

**最佳实践**：如果人类需要阅读 JSON，用 `ensure_ascii=False`。如果只是机器之间传输，默认更安全（不会有编码歧义）。

---

## 一句话总结

**当你需要让两个程序（不管用什么语言写的）在网络上交换结构化数据时，用 HTTP 作为传输协议定义"怎么发"，用 JSON 作为数据格式定义"发什么"——发送方 dict → json.dumps() → bytes → HTTP 报文 → 网络 → HTTP 解析 → bytes → json.loads() → dict 接收方。**

/**
 * TypeScript类型定义 (T014)
 * 与后端OpenAPI合约和Pydantic Schema保持一致。
 */

// ── 数据集相关 ──
export interface ConversationScenario {
  goal: string;
  persona: string;
  context: string;
  success_criteria: string;
}

export interface TestCase {
  id: string;
  input: string;
  // 多轮对话场景(如果存在则说明这是一个对话评估用例)
  scenario?: ConversationScenario;
  max_turns?: number;
  expected_turns?: number;
  expected_constraints?: {
    destination?: string;
    days?: number;
    budget_limit?: number;
    must_include_keywords?: string[];
  };
  expected_tool_sequence?: string[];
  difficulty?: 'easy' | 'medium' | 'hard';
}

export interface DatasetSummary {
  id: string;
  name: string;
  description?: string;
  case_count: number;
  created_at: string;
}

export interface DatasetDetail extends DatasetSummary {
  cases: TestCase[];
}

export interface DatasetCreate {
  name: string;
  description?: string;
  cases: TestCase[];
}

// ── 任务相关 ──
// 任务状态机:
//   draft   — 已创建,等待用户手动点"执行"
//   pending — 已提交执行,排队等 executor 拾取
//   running — 正在执行中(executor 已认领)
//   done    — 已完成
//   failed  — 执行失败
export type TaskStatus = 'draft' | 'pending' | 'running' | 'done' | 'failed';

export interface SimulatorConfig {
  api_base?: string;
  api_key?: string;
  model?: string;
  temperature?: number;
}

export interface TaskCreate {
  name: string;
  agent_version: string;
  dataset_id: string;
  metrics: string[];
  agent_endpoint?: string;
  adapter_type?: string;
  adapter_config?: Record<string, unknown>;
  eval_mode?: 'single_turn' | 'multi_turn';
  simulator_config?: SimulatorConfig;
  weight_config?: Record<string, number>;
}

export interface TaskSummary {
  id: string;
  name: string;
  agent_version: string;
  dataset_name: string;
  dataset_id: string;
  metrics: string[];
  agent_endpoint: string;
  adapter_type?: string;
  status: TaskStatus;
  progress_current: number;
  progress_total: number;
  created_at: string;
  updated_at?: string;
}

export interface TaskListResponse {
  items: TaskSummary[];
  total: number;
  page: number;
  size: number;
}

export interface TaskDetail extends TaskSummary {
  eval_mode?: string;
  simulator_config?: SimulatorConfig;
  weight_config?: Record<string, number>;
  adapter_config?: Record<string, unknown>;
  result?: EvaluationResult;
  error_message?: string;
}

// ── Adapter / Endpoint 预设 ──
export interface EndpointPreset {
  key: string;
  label: string;
  description: string;
  adapter_type: string;
  agent_endpoint: string;
  adapter_config: Record<string, unknown>;
}

// ── 评估结果相关 ──
export interface TraceEvent {
  timestamp?: string;
  event_type: 'thought' | 'tool_call' | 'observation';
  data?: Record<string, unknown>;
}

export interface CaseResult {
  case_id: string;
  status: 'passed' | 'failed' | 'error';
  metric_scores: Record<string, number>;
  metric_details: Record<string, unknown>;
  agent_output?: Record<string, unknown>;
  agent_trace: TraceEvent[];
  error_message?: string;
}

export interface EvaluationResult {
  overall_score: number;
  metric_scores: Record<string, number>;
  case_results: CaseResult[];
  execution_time_seconds: number;
  started_at?: string;
  completed_at?: string;
}

export interface ResultSummary {
  overall_score: number;
  metric_scores: Record<string, number>;
}

// ── 对比相关 ──
export interface CompareRequest {
  task_ids: string[];
}

export interface TaskCompareItem {
  task_id: string;
  task_name: string;
  metric_scores: Record<string, number>;
  overall_score: number;
}

export interface CompareResponse {
  tasks: TaskSummary[];
  metrics_comparison: {
    metric_names?: string[];
    scores?: TaskCompareItem[];
  };
}

// ── 通用 ──
export interface SuccessResponse {
  success: boolean;
}

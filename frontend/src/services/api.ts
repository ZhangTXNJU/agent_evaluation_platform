/**
 * API客户端封装 (T013 / T023 / T038 / T043 / T049)
 * 统一的HTTP请求层，封装所有CRUD操作，提供类型安全的请求和响应处理。
 */

import type {
  DatasetSummary,
  DatasetDetail,
  DatasetCreate,
  TaskSummary,
  TaskListResponse,
  TaskDetail,
  TaskCreate,
  EvaluationResult,
  ResultSummary,
  CompareRequest,
  CompareResponse,
  SuccessResponse,
} from '../types';

// 后端API基础路径（开发环境通过Vite代理转发）
const BASE_URL = '/api/v1';

// 通用请求配置
const DEFAULT_HEADERS: HeadersInit = {
  'Content-Type': 'application/json',
};

/**
 * 通用请求函数
 * 封装fetch，统一处理错误响应和JSON解析
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const config: RequestInit = {
    ...options,
    headers: {
      ...DEFAULT_HEADERS,
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  // 统一错误处理
  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    const message =
      (errorBody as { detail?: string }).detail || response.statusText;
    throw new Error(`API Error ${response.status}: ${message}`);
  }

  return response.json();
}

// ── 数据集API (T023) ──
export const datasetApi = {
  /** 获取所有数据集列表 */
  list: () => request<DatasetSummary[]>('/datasets'),

  /** 获取单个数据集详情（含全部测试用例） */
  get: (id: string) => request<DatasetDetail>(`/datasets/${id}`),

  /** 上传新数据集 */
  create: (data: DatasetCreate) =>
    request<DatasetSummary>('/datasets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 删除数据集 */
  delete: (id: string) =>
    request<SuccessResponse>(`/datasets/${id}`, { method: 'DELETE' }),
};

// ── 任务API (T038) ──
export const taskApi = {
  /** 获取分页任务列表 */
  list: (page = 1, size = 10, status?: string) => {
    const params = new URLSearchParams({ page: String(page), size: String(size) });
    if (status) params.set('status', status);
    return request<TaskListResponse>(`/tasks?${params}`);
  },

  /** 获取单个任务详情 */
  get: (id: string) => request<TaskDetail>(`/tasks/${id}`),

  /** 创建新任务 */
  create: (data: TaskCreate) =>
    request<TaskSummary>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** 删除任务（仅非运行状态） */
  delete: (id: string) =>
    request<SuccessResponse>(`/tasks/${id}`, { method: 'DELETE' }),

  /** 执行任务 */
  execute: (id: string) =>
    request<TaskSummary>(`/tasks/${id}/execute`, { method: 'POST' }),
};

// ── 结果API (T043) ──
export const resultApi = {
  /** 获取完整评估结果 */
  getResult: (taskId: string) =>
    request<EvaluationResult>(`/tasks/${taskId}/result`),

  /** 获取结果摘要（仅总分和各指标均分） */
  getSummary: (taskId: string) =>
    request<ResultSummary>(`/tasks/${taskId}/result/summary`),
};

// ── 对比API (T049) ──
export const compareApi = {
  /** POST方式提交对比请求 */
  compare: (data: CompareRequest) =>
    request<CompareResponse>('/compare', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  /** GET方式获取对比数据 */
  compareGet: (taskIds: string[]) => {
    const params = new URLSearchParams({ ids: taskIds.join(',') });
    return request<CompareResponse>(`/compare/data?${params}`);
  },
};

export default { datasetApi, taskApi, resultApi, compareApi };

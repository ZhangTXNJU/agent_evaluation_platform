/**
 * 创建任务页面 (T036 + Adapter 改造)
 * 表单:
 * - 基本信息: 任务名 / Agent 版本 / 数据集
 * - 评估指标 + 自定义权重
 * - Agent 接入: 端点预设下拉(可选自定义) + endpoint URL + 适配器配置 JSON
 */

import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Form,
  Input,
  Select,
  Button,
  Card,
  Typography,
  message,
  InputNumber,
  Space,
  Divider,
  Tag,
  Tooltip,
} from 'antd';
import { PlusOutlined, InfoCircleOutlined } from '@ant-design/icons';
import { datasetApi, taskApi, adapterApi } from '../services/api';
import MetricsSelector from '../components/MetricsSelector';
import { AVAILABLE_METRICS } from '../components/MetricsSelector';
import type { DatasetSummary, EndpointPreset } from '../types';

const { Title, Text, Paragraph } = Typography;
const { TextArea } = Input;

interface TaskFormValues {
  name: string;
  agent_version: string;
  dataset_id: string;
  metrics: string[];
  agent_endpoint: string;
  // 自定义权重(可选)
  weight_success_rate?: number;
  weight_tool_accuracy?: number;
  weight_llm_judge?: number;
  weight_response_time?: number;
}

const CreateTask: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm<TaskFormValues>();

  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [presets, setPresets] = useState<EndpointPreset[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);

  // 当前选中的预设 key (默认走 native_local 保持向后兼容)
  const [presetKey, setPresetKey] = useState<string>('native_local');
  // 当前 adapter_type / adapter_config (跟随 preset 改变,但用户可以手动编辑)
  const [adapterType, setAdapterType] = useState<string>('native');
  const [adapterConfigText, setAdapterConfigText] = useState<string>('{}');
  const [adapterConfigError, setAdapterConfigError] = useState<string | null>(null);

  // ── 初始化加载 ──
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const [ds, pr] = await Promise.all([
          datasetApi.list(),
          adapterApi.listPresets().catch(() => [] as EndpointPreset[]),
        ]);
        setDatasets(ds);
        setPresets(pr);
        // 应用默认预设
        const defaultPreset = pr.find((p) => p.key === 'native_local') || pr[0];
        if (defaultPreset) {
          applyPreset(defaultPreset);
        }
      } catch (err) {
        message.error('加载初始数据失败: ' + (err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 当前预设对象
  const currentPreset = useMemo(
    () => presets.find((p) => p.key === presetKey),
    [presets, presetKey]
  );

  // ── 应用预设到表单 ──
  const applyPreset = (preset: EndpointPreset) => {
    setPresetKey(preset.key);
    setAdapterType(preset.adapter_type);
    form.setFieldValue('agent_endpoint', preset.agent_endpoint);
    setAdapterConfigText(
      JSON.stringify(preset.adapter_config || {}, null, 2)
    );
    setAdapterConfigError(null);
  };

  const handlePresetChange = (key: string) => {
    const p = presets.find((x) => x.key === key);
    if (p) applyPreset(p);
  };

  // ── 解析适配器配置 JSON ──
  const parseAdapterConfig = (): Record<string, unknown> | null => {
    const txt = adapterConfigText.trim();
    if (!txt) return {};
    try {
      const parsed = JSON.parse(txt);
      if (typeof parsed !== 'object' || Array.isArray(parsed) || parsed === null) {
        setAdapterConfigError('适配器配置必须是 JSON 对象');
        return null;
      }
      setAdapterConfigError(null);
      return parsed as Record<string, unknown>;
    } catch (e) {
      setAdapterConfigError('JSON 格式错误: ' + (e as Error).message);
      return null;
    }
  };

  // ── 提交 ──
  const handleSubmit = async (values: TaskFormValues) => {
    const adapterConfig = parseAdapterConfig();
    if (adapterConfig === null) {
      message.error('请修正适配器配置 JSON');
      return;
    }

    setSubmitting(true);
    try {
      // 构建权重配置
      const weightConfig: Record<string, number> = {};
      const metricWeightMap: Record<string, string> = {
        success_rate: 'weight_success_rate',
        tool_accuracy: 'weight_tool_accuracy',
        llm_judge: 'weight_llm_judge',
        response_time: 'weight_response_time',
      };

      let hasCustomWeights = false;
      for (const metric of values.metrics) {
        const weightKey = metricWeightMap[metric];
        const weightVal = (values as unknown as Record<string, unknown>)[
          weightKey
        ] as number | undefined;
        if (weightVal !== undefined && weightVal !== null) {
          weightConfig[metric] = weightVal;
          hasCustomWeights = true;
        }
      }

      await taskApi.create({
        name: values.name,
        agent_version: values.agent_version,
        dataset_id: values.dataset_id,
        metrics: values.metrics,
        agent_endpoint: values.agent_endpoint,
        adapter_type: adapterType,
        adapter_config: Object.keys(adapterConfig).length ? adapterConfig : undefined,
        weight_config: hasCustomWeights ? weightConfig : undefined,
      });

      message.success('任务创建成功');
      navigate('/');
    } catch (err) {
      message.error('创建任务失败: ' + (err as Error).message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: 800, margin: '0 auto' }}>
      <Card>
        <Title level={4}>创建评估任务</Title>
        <Divider />

        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            agent_endpoint: 'http://localhost:8000/api/eval/run',
            metrics: ['success_rate', 'tool_accuracy', 'llm_judge', 'response_time'],
          }}
        >
          {/* ── 基本信息 ── */}
          <Form.Item
            name="name"
            label="任务名称"
            rules={[
              { required: true, message: '请输入任务名称' },
              { max: 255, message: '不超过255个字符' },
            ]}
          >
            <Input placeholder="例如：旅行规划Agent v1.0 评估" />
          </Form.Item>

          <Form.Item
            name="agent_version"
            label="Agent版本"
            rules={[{ required: true, message: '请输入Agent版本号' }]}
          >
            <Input placeholder="例如：v1.0.0" />
          </Form.Item>

          {/* ── 数据集 ── */}
          <Form.Item
            name="dataset_id"
            label="选择数据集"
            rules={[{ required: true, message: '请选择数据集' }]}
          >
            <Select
              placeholder="选择一个数据集..."
              loading={loading}
              notFoundContent={
                <div style={{ padding: 8, color: '#999' }}>
                  暂无数据集，
                  <Button type="link" onClick={() => navigate('/datasets')}>
                    去上传
                  </Button>
                </div>
              }
              options={datasets.map((ds) => ({
                value: ds.id,
                label: `${ds.name} (${ds.case_count}个用例)`,
              }))}
            />
          </Form.Item>

          {/* ── 指标选择 ── */}
          <Form.Item
            name="metrics"
            label="评估指标"
            rules={[
              { required: true, message: '请至少选择一项评估指标' },
              {
                validator: (_, value: string[]) =>
                  value && value.length >= 1
                    ? Promise.resolve()
                    : Promise.reject(new Error('请至少选择一项评估指标')),
              },
            ]}
          >
            <MetricsSelector
              value={selectedMetrics}
              onChange={(selected) => {
                setSelectedMetrics(selected);
                form.setFieldValue('metrics', selected);
              }}
            />
          </Form.Item>

          {/* ── 自定义权重 ── */}
          {selectedMetrics.length > 0 && (
            <Card
              size="small"
              title="自定义权重(可选,不填则等权重分配)"
              style={{ marginBottom: 16 }}
            >
              <Space wrap>
                {selectedMetrics.map((metric) => {
                  const metricInfo = AVAILABLE_METRICS.find((m) => m.key === metric);
                  return (
                    <Form.Item
                      key={metric}
                      name={`weight_${metric}`}
                      label={metricInfo?.label || metric}
                      style={{ marginBottom: 8 }}
                    >
                      <InputNumber
                        min={0}
                        max={10}
                        step={0.1}
                        placeholder="等权重"
                        style={{ width: 120 }}
                      />
                    </Form.Item>
                  );
                })}
              </Space>
              <Text type="secondary" style={{ fontSize: 12 }}>
                权重最终会被归一化,确保总和为1。留空则所有选定指标等权重。
              </Text>
            </Card>
          )}

          <Divider orientation="left" plain>
            Agent 接入配置
          </Divider>

          {/* ── 预设下拉 ── */}
          <Form.Item
            label={
              <span>
                Agent 端点预设{' '}
                <Tooltip title="选一个常用预设会自动填入下方 URL 和适配器配置;选完后仍可在下面手动修改。">
                  <InfoCircleOutlined style={{ color: '#999' }} />
                </Tooltip>
              </span>
            }
          >
            <Select
              value={presetKey}
              onChange={handlePresetChange}
              loading={loading}
              optionLabelProp="label"
              options={presets.map((p) => ({
                value: p.key,
                label: p.label,
                preset: p,
              }))}
              optionRender={(opt) => {
                const p = (opt.data as unknown as { preset: EndpointPreset }).preset;
                return (
                  <div style={{ padding: '4px 0' }}>
                    <div>
                      <strong>{p.label}</strong>{' '}
                      <Tag color={p.adapter_type === 'native' ? 'blue' : 'green'}>
                        {p.adapter_type}
                      </Tag>
                    </div>
                    <div style={{ fontSize: 12, color: '#666' }}>{p.description}</div>
                  </div>
                );
              }}
            />
            {currentPreset && (
              <Paragraph type="secondary" style={{ fontSize: 12, marginTop: 4, marginBottom: 0 }}>
                {currentPreset.description}
              </Paragraph>
            )}
          </Form.Item>

          {/* ── Agent endpoint URL(可手动改) ── */}
          <Form.Item
            name="agent_endpoint"
            label={
              <span>
                Agent 端点 URL{' '}
                <Tag color="default">{adapterType}</Tag>
              </span>
            }
            rules={[
              { required: true, message: '请输入 Agent 端点 URL' },
              { type: 'url', message: '请输入合法的 URL', warningOnly: true },
            ]}
            extra="选预设后会自动填入,你也可以手动修改为自己的服务地址。"
          >
            <Input placeholder="http://localhost:8000/api/eval/run" />
          </Form.Item>

          {/* ── 适配器配置 JSON(可手动改) ── */}
          <Form.Item
            label={
              <span>
                适配器配置(JSON){' '}
                <Tooltip title="对 native 适配器一般为空 {};对 openai_chat 需要填 api_key、model 等。">
                  <InfoCircleOutlined style={{ color: '#999' }} />
                </Tooltip>
              </span>
            }
            validateStatus={adapterConfigError ? 'error' : ''}
            help={adapterConfigError || '若不需要任何配置,留 {} 即可'}
          >
            <TextArea
              rows={8}
              value={adapterConfigText}
              onChange={(e) => {
                setAdapterConfigText(e.target.value);
                setAdapterConfigError(null);
              }}
              onBlur={() => parseAdapterConfig()}
              spellCheck={false}
              style={{ fontFamily: 'Menlo, Consolas, monospace', fontSize: 13 }}
            />
          </Form.Item>

          {/* ── 提交 ── */}
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                icon={<PlusOutlined />}
                loading={submitting}
                size="large"
              >
                创建任务
              </Button>
              <Button size="large" onClick={() => navigate('/')}>
                取消
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
};

export default CreateTask;

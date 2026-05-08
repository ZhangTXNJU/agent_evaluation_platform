/**
 * 创建任务页面 (T036)
 * 表单：选择数据集、配置评估指标、指定Agent端点、设置权重。
 */

import React, { useEffect, useState } from 'react';
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
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import { datasetApi, taskApi } from '../services/api';
import MetricsSelector from '../components/MetricsSelector';
import { AVAILABLE_METRICS } from '../components/MetricsSelector';
import type { DatasetSummary } from '../types';

const { Title, Text } = Typography;

interface TaskFormValues {
  name: string;
  agent_version: string;
  dataset_id: string;
  metrics: string[];
  agent_endpoint: string;
  // 自定义权重（可选）
  weight_success_rate?: number;
  weight_tool_accuracy?: number;
  weight_llm_judge?: number;
  weight_response_time?: number;
}

const CreateTask: React.FC = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm<TaskFormValues>();
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedMetrics, setSelectedMetrics] = useState<string[]>([]);

  // ── 加载数据集列表供下拉选择 ──
  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const data = await datasetApi.list();
        setDatasets(data);
      } catch (err) {
        message.error('加载数据集失败: ' + (err as Error).message);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  // ── 提交表单 ──
  const handleSubmit = async (values: TaskFormValues) => {
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
        const weightVal = (values as unknown as Record<string, unknown>)[weightKey] as number | undefined;
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
          {/* 基本信息 */}
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

          {/* 数据集选择 */}
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

          {/* 指标选择 */}
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

          {/* 自定义权重 */}
          {selectedMetrics.length > 0 && (
            <Card
              size="small"
              title="自定义权重（可选，不填则等权重分配）"
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
                权重最终会被归一化，确保总和为1。留空则所有选定指标等权重。
              </Text>
            </Card>
          )}

          {/* Agent端点 */}
          <Form.Item
            name="agent_endpoint"
            label="Agent Platform端点"
            rules={[{ required: true, message: '请输入Agent端点URL' }]}
          >
            <Input placeholder="http://localhost:8000/api/eval/run" />
          </Form.Item>

          {/* 提交 */}
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

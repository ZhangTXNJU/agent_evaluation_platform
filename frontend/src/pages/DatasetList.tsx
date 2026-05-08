/**
 * 数据集管理页面 (T020 / T021 / T022)
 * 提供数据集的列表展示、上传、查看详情、删除功能。
 */

import React, { useEffect, useState, useCallback } from 'react';
import {
  Table,
  Button,
  Modal,
  Upload,
  Descriptions,
  Tag,
  Space,
  message,
  Popconfirm,
  Card,
  Typography,
  Input,
} from 'antd';
import {
  UploadOutlined,
  DeleteOutlined,
  EyeOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { datasetApi } from '../services/api';
import type { DatasetSummary, DatasetDetail, TestCase } from '../types';

const { TextArea } = Input;

const { Title } = Typography;

const DatasetList: React.FC = () => {
  // ── 状态 ──
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [detailModalOpen, setDetailModalOpen] = useState(false);
  const [selectedDataset, setSelectedDataset] = useState<DatasetDetail | null>(null);
  const [jsonText, setJsonText] = useState('');

  // ── 加载数据集列表 ──
  const loadDatasets = useCallback(async () => {
    setLoading(true);
    try {
      const data = await datasetApi.list();
      setDatasets(data);
    } catch (err) {
      message.error('加载数据集失败: ' + (err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadDatasets();
  }, [loadDatasets]);

  // ── 上传数据集 ──
  const handleUpload = async () => {
    if (!jsonText.trim()) {
      message.warning('请输入JSON数据');
      return;
    }
    try {
      const parsed = JSON.parse(jsonText);
      // 兼容两种格式：{name, description, cases} 或纯cases数组
      const body =
        parsed.cases !== undefined
          ? parsed
          : { name: '导入数据集', description: '', cases: parsed };
      await datasetApi.create(body);
      message.success('数据集上传成功');
      setUploadModalOpen(false);
      setJsonText('');
      loadDatasets();
    } catch (err) {
      if (err instanceof SyntaxError) {
        message.error('JSON格式无效，请检查语法');
      } else {
        message.error('上传失败: ' + (err as Error).message);
      }
    }
  };

  // ── 查看数据集详情 ──
  const handleViewDetail = async (id: string) => {
    try {
      const detail = await datasetApi.get(id);
      setSelectedDataset(detail);
      setDetailModalOpen(true);
    } catch (err) {
      message.error('获取数据集详情失败: ' + (err as Error).message);
    }
  };

  // ── 删除数据集 ──
  const handleDelete = async (id: string) => {
    try {
      await datasetApi.delete(id);
      message.success('数据集已删除');
      loadDatasets();
    } catch (err) {
      message.error('删除失败: ' + (err as Error).message);
    }
  };

  // ── 文件上传处理 ──
  const handleFileUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      const text = e.target?.result as string;
      setJsonText(text);
      // 校验JSON合法性
      try {
        JSON.parse(text);
        message.success('JSON格式校验通过');
      } catch {
        message.warning('JSON格式无效，请检查文件内容');
      }
    };
    reader.readAsText(file);
    return false; // 阻止自动上传
  };

  // ── 难度级别标签颜色 ──
  const difficultyColor: Record<string, string> = {
    easy: 'green',
    medium: 'orange',
    hard: 'red',
  };

  // ── 表格列定义 ──
  const columns: ColumnsType<DatasetSummary> = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
      render: (text: string) => text || '-',
    },
    {
      title: '用例数',
      dataIndex: 'case_count',
      key: 'case_count',
      width: 100,
      align: 'center',
      render: (count: number) => <Tag color="blue">{count}</Tag>,
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString('zh-CN'),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space>
          <Button
            type="link"
            icon={<EyeOutlined />}
            onClick={() => handleViewDetail(record.id)}
          >
            查看
          </Button>
          <Popconfirm
            title="确定删除此数据集？"
            description="删除后不可恢复"
            onConfirm={() => handleDelete(record.id)}
            okText="确定"
            cancelText="取消"
          >
            <Button type="link" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      {/* ── 顶部操作栏 ── */}
      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Title level={4} style={{ margin: 0 }}>
            数据集管理
          </Title>
          <Space>
            <Button icon={<ReloadOutlined />} onClick={loadDatasets}>
              刷新
            </Button>
            <Button
              type="primary"
              icon={<UploadOutlined />}
              onClick={() => setUploadModalOpen(true)}
            >
              上传数据集
            </Button>
          </Space>
        </div>
      </Card>

      {/* ── 数据集表格 ── */}
      <Table
        columns={columns}
        dataSource={datasets}
        rowKey="id"
        loading={loading}
        locale={{
          emptyText: (
            <div style={{ padding: 40 }}>
              <p style={{ fontSize: 16, color: '#999' }}>暂无数据集</p>
              <p style={{ color: '#bbb' }}>点击"上传数据集"按钮导入JSON格式的测试用例</p>
            </div>
          ),
        }}
      />

      {/* ── 上传数据集弹窗 ── */}
      <Modal
        title="上传数据集"
        open={uploadModalOpen}
        onOk={handleUpload}
        onCancel={() => {
          setUploadModalOpen(false);
          setJsonText('');
        }}
        okText="上传"
        cancelText="取消"
        width={700}
      >
        <div style={{ marginBottom: 16 }}>
          <Upload
            accept=".json"
            showUploadList={false}
            beforeUpload={handleFileUpload}
          >
            <Button icon={<UploadOutlined />}>选择JSON文件</Button>
          </Upload>
          <span style={{ marginLeft: 12, color: '#999' }}>
            或直接在下方编辑器中粘贴JSON
          </span>
        </div>
        <TextArea
          rows={12}
          value={jsonText}
          onChange={(e) => setJsonText(e.target.value)}
          placeholder={`支持两种JSON格式：

1. 完整格式：
{
  "name": "数据集名称",
  "description": "描述",
  "cases": [
    {
      "id": "case_01",
      "input": "旅行需求描述...",
      "expected_constraints": {"destination": "北京", "days": 3},
      "expected_tool_sequence": ["search_attractions", "query_weather"],
      "difficulty": "easy"
    }
  ]
}

2. 纯用例数组（名称自动生成）：
[{"id": "case_01", "input": "...", ...}]`}
        />
      </Modal>

      {/* ── 数据集详情弹窗 ── */}
      <Modal
        title="数据集详情"
        open={detailModalOpen}
        onCancel={() => {
          setDetailModalOpen(false);
          setSelectedDataset(null);
        }}
        footer={<Button onClick={() => setDetailModalOpen(false)}>关闭</Button>}
        width={900}
      >
        {selectedDataset && (
          <>
            <Descriptions bordered size="small" column={2} style={{ marginBottom: 16 }}>
              <Descriptions.Item label="名称">{selectedDataset.name}</Descriptions.Item>
              <Descriptions.Item label="用例数">
                <Tag color="blue">{selectedDataset.case_count}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="描述" span={2}>
                {selectedDataset.description || '-'}
              </Descriptions.Item>
              <Descriptions.Item label="创建时间">
                {new Date(selectedDataset.created_at).toLocaleString('zh-CN')}
              </Descriptions.Item>
            </Descriptions>

            <Title level={5}>测试用例列表 ({selectedDataset.cases.length})</Title>
            {selectedDataset.cases.map((tc: TestCase) => (
              <Card
                key={tc.id}
                size="small"
                style={{ marginBottom: 8 }}
                title={
                  <Space>
                    <span>{tc.id}</span>
                    <Tag color={difficultyColor[tc.difficulty || 'medium']}>
                      {tc.difficulty || 'medium'}
                    </Tag>
                  </Space>
                }
              >
                <p><strong>输入：</strong>{tc.input}</p>
                {tc.expected_constraints && (
                  <p>
                    <strong>约束条件：</strong>
                    目的地={tc.expected_constraints.destination || '-'}，
                    天数={tc.expected_constraints.days || '-'}，
                    预算={tc.expected_constraints.budget_limit ?? '不限'}
                    {tc.expected_constraints.must_include_keywords &&
                      `，关键词：[${tc.expected_constraints.must_include_keywords.join(', ')}]`}
                  </p>
                )}
                {tc.expected_tool_sequence && (
                  <p>
                    <strong>工具序列：</strong>
                    {tc.expected_tool_sequence.map((t, i) => (
                      <Tag key={i} style={{ marginRight: 4 }}>
                        {t}
                      </Tag>
                    ))}
                  </p>
                )}
              </Card>
            ))}
          </>
        )}
      </Modal>
    </div>
  );
};

export default DatasetList;

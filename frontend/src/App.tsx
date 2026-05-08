import React from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { ConfigProvider, Layout, Menu } from 'antd';
import {
  DatabaseOutlined,
  ExperimentOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import zhCN from 'antd/locale/zh_CN';
import TaskList from './pages/TaskList';
import CreateTask from './pages/CreateTask';
import TaskDetail from './pages/TaskDetail';
import CompareView from './pages/CompareView';
import DatasetList from './pages/DatasetList';

const { Header, Content } = Layout;

/**
 * 应用根组件 (T015)
 * 提供React Router路由、Ant Design中文配置、全局布局。
 * 路由：
 *   /              → TaskList（任务列表首页）
 *   /datasets      → DatasetList（数据集管理）
 *   /tasks/new     → CreateTask（创建新任务）
 *   /tasks/:id     → TaskDetail（任务详情）
 *   /compare       → CompareView（多任务对比）
 */

const navItems = [
  { key: '/', icon: <ExperimentOutlined />, label: <Link to="/">任务列表</Link> },
  { key: '/datasets', icon: <DatabaseOutlined />, label: <Link to="/datasets">数据集</Link> },
  { key: '/tasks/new', icon: <DatabaseOutlined />, label: <Link to="/tasks/new">创建任务</Link> },
  { key: '/compare', icon: <BarChartOutlined />, label: <Link to="/compare">任务对比</Link> },
];

const App: React.FC = () => {
  return (
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <Layout style={{ minHeight: '100vh' }}>
          <Header style={{ display: 'flex', alignItems: 'center' }}>
            <div
              style={{
                color: '#fff',
                fontSize: 18,
                fontWeight: 'bold',
                marginRight: 40,
                whiteSpace: 'nowrap',
              }}
            >
              Agent 评估平台
            </div>
            <Menu
              theme="dark"
              mode="horizontal"
              defaultSelectedKeys={['/']}
              items={navItems}
              style={{ flex: 1 }}
            />
          </Header>
          <Content style={{ padding: '24px', maxWidth: 1400, margin: '0 auto', width: '100%' }}>
            <Routes>
              <Route path="/" element={<TaskList />} />
              <Route path="/datasets" element={<DatasetList />} />
              <Route path="/tasks/new" element={<CreateTask />} />
              <Route path="/tasks/:id" element={<TaskDetail />} />
              <Route path="/compare" element={<CompareView />} />
            </Routes>
          </Content>
        </Layout>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;

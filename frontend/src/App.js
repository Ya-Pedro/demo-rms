import React, { useState, useEffect, useRef, useCallback } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { ConfigProvider, App as AntApp, Layout, Menu, Button, Dropdown, Space, Avatar, message, Modal } from 'antd';
import {
  TableOutlined,
  UserOutlined,
  SettingOutlined,
  LogoutOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  KeyOutlined,
  FileTextOutlined,
  SafetyCertificateOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import ruRU from 'antd/locale/ru_RU';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import axios from 'axios';
import { tokenStorage } from './tokenStorage';

import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import DictionaryPage from './pages/DictionaryPage';
import UsersPage from './pages/UsersPage';
import ReportsPage from './pages/ReportsPage';
import DashboardsPage from './pages/DashboardsPage';
import ChangePasswordModal from './pages/ChangePasswordModal';
import TwoFactorSettings from './components/TwoFactorSettings';

import './App.css';

dayjs.locale('ru');

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const IDLE_TIMEOUT_MS = (Number(process.env.REACT_APP_IDLE_TIMEOUT_MINUTES) || 15) * 60 * 1000;

const api = axios.create({
  baseURL: BACKEND_URL ? `${BACKEND_URL}/api` : '/api',
});

api.interceptors.request.use((config) => {
  const token = tokenStorage.getAccess();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let isRefreshing = false;
let failedQueue = [];

const processQueue = (error, token = null) => {
  failedQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  failedQueue = [];
};

const forceLogout = () => {
  tokenStorage.clear();
  window.location.href = '/login';
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const isLoginPage = window.location.pathname === '/login';
    const isRefreshEndpoint = originalRequest?.url?.includes('/auth/refresh');

    const isTokenError = error.response?.status === 401 ||
      (error.response?.status === 403 && !isLoginPage);

    if (!isTokenError || isLoginPage || isRefreshEndpoint) {
      return Promise.reject(error);
    }

    if (originalRequest._retry) {
      return Promise.reject(error);
    }

    if (isRefreshing) {

      return new Promise((resolve, reject) => {
        failedQueue.push({ resolve, reject });
      })
        .then((newToken) => {
          originalRequest.headers.Authorization = `Bearer ${newToken}`;
          return api(originalRequest);
        })
        .catch((err) => Promise.reject(err));
    }

    originalRequest._retry = true;
    isRefreshing = true;

    const refreshToken = tokenStorage.getRefresh();

    if (!refreshToken) {

      processQueue(error, null);
      isRefreshing = false;
      forceLogout();
      return Promise.reject(error);
    }

    try {
      const { data } = await axios.post(
        `${api.defaults.baseURL}/auth/refresh`,
        { refresh_token: refreshToken }
      );

      const newToken = data.access_token;
      tokenStorage.setAccess(newToken);

      if (data.refresh_token) {
        tokenStorage.setRefresh(data.refresh_token);
      }

      api.defaults.headers.common.Authorization = `Bearer ${newToken}`;

      processQueue(null, newToken);

      originalRequest.headers.Authorization = `Bearer ${newToken}`;
      return api(originalRequest);

    } catch (refreshError) {

      processQueue(refreshError, null);
      forceLogout();
      return Promise.reject(refreshError);

    } finally {
      isRefreshing = false;
    }
  }
);

export { api };

const { Header, Sider, Content } = Layout;

const themeConfig = {
  token: {
    colorPrimary: '#0050B3',
    colorInfo: '#0050B3',
    colorSuccess: '#389E0D',
    colorWarning: '#FAAD14',
    colorError: '#F5222D',
    colorTextBase: '#1F1F1F',
    colorBgBase: '#FFFFFF',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    borderRadius: 2,
    wireframe: true,
  },
  components: {
    Table: {
      cellPaddingBlock: 4,
      cellPaddingInline: 8,
      headerBg: '#F5F5F5',
      headerColor: '#000000',
      borderColor: '#D9D9D9',
      rowHoverBg: '#E6F7FF',
    },
    Button: {
      borderRadius: 2,
      controlHeight: 32,
      fontWeight: 500,
    },
    Input: {
      borderRadius: 2,
      controlHeight: 32,
    },
    Card: {
      borderRadius: 0,
    },
  },
};

const MainLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [user, setUser] = useState(null);
  const [changePasswordOpen, setChangePasswordOpen] = useState(false);
  const [twoFactorOpen, setTwoFactorOpen] = useState(false);

  const refreshUser = async () => {
    try {
      const resp = await api.get('/auth/me');
      const updated = resp.data;
      setUser(updated);
      tokenStorage.setUser(updated);
    } catch (e) {

    }
  };

  useEffect(() => {
    const storedUser = tokenStorage.getAccess() ? tokenStorage.getUser() : null;
    if (storedUser) {

      setUser(storedUser);
    }
  }, []);

  const getSelectedKey = () => {
    const path = location.pathname;
    if (path === '/dictionary') return 'dictionary';
    if (path === '/users') return 'users';
    if (path === '/reports') return 'reports';
    if (path === '/dashboards') return 'dashboards';
    return 'dashboard';
  };

  const handleLogout = useCallback(() => {
    tokenStorage.clear();
    navigate('/login');
  }, [navigate]);

  const idleTimerRef = useRef(null);

  const resetIdleTimer = useCallback(() => {
    if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    idleTimerRef.current = setTimeout(() => {
      handleLogout();
    }, IDLE_TIMEOUT_MS);
  }, [handleLogout]);

  useEffect(() => {
    const events = ['mousemove', 'mousedown', 'keydown', 'touchstart', 'scroll', 'click'];
    events.forEach(e => window.addEventListener(e, resetIdleTimer, { passive: true }));
    resetIdleTimer();

    return () => {
      events.forEach(e => window.removeEventListener(e, resetIdleTimer));
      if (idleTimerRef.current) clearTimeout(idleTimerRef.current);
    };
  }, [resetIdleTimer]);

  const isAdmin = user?.role === 'admin' || user?.role === 'superadmin';

  const menuItems = [
    {
      key: 'dashboard',
      icon: <TableOutlined />,
      label: 'Вакансии',
      onClick: () => navigate('/'),
    },
  ];

  menuItems.push({
    key: 'reports',
    icon: <FileTextOutlined />,
    label: 'Отчеты',
    onClick: () => navigate('/reports'),
  });

  if (isAdmin) {
    menuItems.push({
      key: 'dashboards',
      icon: <BarChartOutlined />,
      label: 'Дашборды',
      onClick: () => navigate('/dashboards'),
    });
  }

  if (isAdmin) {
    menuItems.push({
      key: 'dictionary',
      icon: <SettingOutlined />,
      label: 'Справочники',
      onClick: () => navigate('/dictionary'),
    });
  }

  if (isAdmin) {
    menuItems.push({
      key: 'users',
      icon: <UserOutlined />,
      label: 'Пользователи',
      onClick: () => navigate('/users'),
    });
  }

  const userMenuItems = [
    {
      key: 'profile',
      label: (
        <Space direction="vertical" size={0}>
          <span style={{ fontWeight: 500 }}>{user?.full_name}</span>
          <span style={{ fontSize: 12, color: '#888' }}>{user?.email}</span>
          <span style={{ fontSize: 11, color: '#0050B3' }}>
            {user?.role === 'superadmin' ? 'Суперадмин' : user?.role === 'admin' ? 'Админ' : 'Рекрутер'}
          </span>
        </Space>
      ),
      disabled: true,
    },
    { type: 'divider' },
    {
      key: 'change-password',
      icon: <KeyOutlined />,
      label: 'Сменить пароль',
      onClick: () => setChangePasswordOpen(true),
    },
    {
      key: '2fa',
      icon: <SafetyCertificateOutlined />,
      label: user?.is_2fa_enabled ? '2FA: включена' : '2FA: настроить',
      onClick: () => setTwoFactorOpen(true),
    },
    {
      key: 'logout',
      icon: <LogoutOutlined />,
      label: 'Выйти',
      onClick: handleLogout,
    },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider 
        trigger={null} 
        collapsible 
        collapsed={collapsed}
        width={220}
        style={{ 
          background: '#fff',
          borderRight: '1px solid #D9D9D9',
        }}
      >
        <div style={{ 
          height: 64, 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: collapsed ? 'center' : 'flex-start',
          padding: collapsed ? 0 : '0 24px',
          borderBottom: '1px solid #D9D9D9',
        }}>
          <span style={{ 
            fontSize: collapsed ? 18 : 24, 
            fontWeight: 700, 
            color: '#0050B3',
            letterSpacing: '-0.5px',
          }}>
            {collapsed ? 'R' : 'RMS'}
          </span>
        </div>
        <Menu
          mode="inline"
          selectedKeys={[getSelectedKey()]}
          items={menuItems}
          style={{ borderRight: 0 }}
        />
      </Sider>
      <Layout>
        <Header style={{ 
          padding: '0 16px', 
          background: '#fff', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          borderBottom: '1px solid #D9D9D9',
        }}>
          <Button
            type="text"
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setCollapsed(!collapsed)}
            data-testid="sidebar-toggle"
          />
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }} data-testid="user-menu">
              <Avatar 
                style={{ backgroundColor: '#0050B3' }} 
                icon={<UserOutlined />} 
              />
              {!collapsed && <span>{user?.full_name}</span>}
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ 
          margin: 8, 
          padding: 12, 
          background: '#fff',
          minHeight: 280,
          overflow: 'auto',
        }}>
          {children}
        </Content>
      </Layout>
      <ChangePasswordModal
        open={changePasswordOpen}
        onSuccess={() => setChangePasswordOpen(false)}
        forced={false}
      />
      <Modal
        open={twoFactorOpen}
        onCancel={() => setTwoFactorOpen(false)}
        footer={null}
        title="Двухфакторная аутентификация"
        width={560}
        destroyOnClose
      >
        <TwoFactorSettings
          user={user}
          onUpdate={() => {
            refreshUser();
          }}
        />
      </Modal>
    </Layout>
  );
};

const ProtectedRoute = ({ children }) => {
  const token = tokenStorage.getAccess();
  
  if (!token) {
    return <Navigate to="/login" replace />;
  }
  
  return <MainLayout>{children}</MainLayout>;
};

function App() {
  return (
    <ConfigProvider locale={ruRU} theme={themeConfig}>
      <AntApp>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboard"
              element={
                <ProtectedRoute>
                  <DashboardPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dictionary"
              element={
                <ProtectedRoute>
                  <DictionaryPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/users"
              element={
                <ProtectedRoute>
                  <UsersPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/reports"
              element={
                <ProtectedRoute>
                  <ReportsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/dashboards"
              element={
                <ProtectedRoute>
                  <DashboardsPage />
                </ProtectedRoute>
              }
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AntApp>
    </ConfigProvider>
  );
}

export default App;
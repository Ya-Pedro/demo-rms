import React, { useState, useEffect, useRef, useCallback, createContext, useMemo } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp, Layout, Menu, Button, Dropdown, Space, Avatar, message, Modal, Drawer, theme } from 'antd';
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
  CloseOutlined,
  BulbOutlined,
} from '@ant-design/icons';

export const ThemeContext = createContext({
  isDarkMode: false,
  toggleTheme: () => {},
});
import ruRU from 'antd/locale/ru_RU';
import { useIsMobile } from './hooks/useIsMobile';
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
import ErrorBoundary from './components/ErrorBoundary';

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

const getThemeConfig = (isDark) => ({
  algorithm: isDark ? theme.darkAlgorithm : theme.defaultAlgorithm,
  token: isDark ? {
    colorPrimary: '#58a6ff',
    colorInfo: '#58a6ff',
    colorSuccess: '#238636',
    colorWarning: '#e3b341',
    colorError: '#da3633',
    colorTextBase: '#c9d1d9',
    colorTextPlaceholder: 'rgba(255, 255, 255, 0.45)',
    colorBgBase: '#0d1117',
    colorBgLayout: '#0d1117',
    colorBgContainer: '#161b22',
    colorBgElevated: '#161b22',
    colorBorder: '#30363d',
    colorBorderSecondary: '#21262d',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    borderRadius: 8,
    boxShadow: '0 8px 24px rgba(1,4,9,1)',
  } : {
    colorPrimary: '#6366f1',
    colorInfo: '#3b82f6',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorTextBase: '#1e293b',
    colorBgBase: '#ffffff',
    colorBgLayout: '#f4f7fe',
    colorBorder: '#e2e8f0',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    borderRadius: 12,
    wireframe: false,
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05)',
  },
  components: isDark ? {
    Layout: {
      siderBg: '#161b22',
      headerBg: '#161b22',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(88,166,255,0.15)',
      itemSelectedColor: '#58a6ff',
      itemHoverBg: 'rgba(177,186,196,0.12)',
    },
    Table: {
      headerBg: '#161b22',
      headerColor: '#c9d1d9',
      rowHoverBg: 'rgba(177,186,196,0.12)',
      borderColor: '#30363d',
    },
    Card: {
      colorBgContainer: '#161b22',
      colorBorderSecondary: '#30363d',
    }
  } : {
    Layout: {
      siderBg: '#ffffff',
      headerBg: 'rgba(255, 255, 255, 0.8)',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#e0e7ff',
      itemSelectedColor: '#4f46e5',
      itemBorderRadius: 8,
      itemMarginInline: 12,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#64748b',
      rowHoverBg: '#f1f5f9',
      cellPaddingBlock: 16,
      borderColor: '#f1f5f9',
    },
    Card: {
      borderRadius: 16,
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
    },
    Button: {
      borderRadius: 8,
      controlHeight: 40,
      fontWeight: 500,
    },
    Input: {
      borderRadius: 8,
      controlHeight: 40,
      hoverBorderColor: '#6366f1',
      activeBorderColor: '#6366f1',
    },
    Select: {
      borderRadius: 8,
      controlHeight: 40,
    }
  }
});

const MainLayout = ({ children }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const isMobile = useIsMobile();
  const { isDarkMode, toggleTheme } = React.useContext(ThemeContext);
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
          <span style={{ fontWeight: 500, color: isDarkMode ? '#ffffff' : '#0f172a' }}>{user?.full_name}</span>
          <span style={{ fontSize: 12, color: isDarkMode ? '#a3a3a3' : '#475569' }}>{user?.email}</span>
          <span style={{ fontSize: 11, color: isDarkMode ? '#58a6ff' : '#0050B3', fontWeight: 600 }}>
            {user?.role === 'superadmin' ? 'Суперадмин' : user?.role === 'admin' ? 'Админ' : 'Рекрутер'}
          </span>
        </Space>
      ),
      disabled: true,
    },
    { type: 'divider' },
    {
      key: 'theme',
      icon: <BulbOutlined />,
      label: isDarkMode ? 'Светлая тема' : 'Темная тема',
      onClick: toggleTheme,
    },
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
    <Layout style={{ minHeight: '100vh', background: 'var(--layout-bg)' }}>
      <Header style={{ 
        position: 'sticky',
        top: 0,
        zIndex: 1000,
        width: '100%',
        padding: isMobile ? '0 16px' : '0 48px', 
        background: 'var(--header-bg)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--border-color)',
        boxShadow: '0 4px 20px var(--shadow-color)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile && (
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={() => setMobileMenuOpen(true)}
                data-testid="sidebar-toggle"
              />
            )}
            <span style={{ 
              fontSize: 28, 
              fontWeight: 800, 
              background: 'linear-gradient(135deg, #4f46e5 0%, #ec4899 100%)',
              WebkitBackgroundClip: 'text',
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-1px',
              marginRight: 24
            }}>
              RMS
            </span>
          </div>
          
          {!isMobile && (
            <Menu
              mode="horizontal"
              selectedKeys={[getSelectedKey()]}
              items={menuItems}
              style={{ 
                background: 'transparent', 
                borderBottom: 0, 
                flex: 1,
                minWidth: 0,
                lineHeight: '70px',
                fontSize: 15,
                fontWeight: 500
              }}
            />
          )}
        </div>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer', paddingLeft: 16 }} data-testid="user-menu">
            <Avatar 
              size={40}
              style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #ec4899 100%)', boxShadow: '0 4px 10px rgba(79, 70, 229, 0.3)' }} 
              icon={<UserOutlined />} 
            />
            {!isMobile && <span style={{ fontWeight: 600, color: 'var(--text-color)' }}>{user?.full_name}</span>}
          </Space>
        </Dropdown>
      </Header>

      {isMobile && (
        <Drawer
          placement="left"
          width={280}
          onClose={() => setMobileMenuOpen(false)}
          open={mobileMenuOpen}
          styles={{ body: { padding: 0 }, header: { padding: '16px 24px', borderBottom: 'none' } }}
          title={
            <span style={{ fontSize: 28, fontWeight: 800, background: 'linear-gradient(135deg, #4f46e5 0%, #ec4899 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-1px' }}>
              RMS
            </span>
          }
          closeIcon={<CloseOutlined style={{ fontSize: 18 }}/>}
        >
          <Menu
            mode="inline"
            selectedKeys={[getSelectedKey()]}
            items={menuItems}
            style={{ borderRight: 0, fontSize: 16, fontWeight: 500 }}
            onClick={() => setMobileMenuOpen(false)}
          />
        </Drawer>
      )}

      <Content style={{ 
        padding: isMobile ? '16px' : '24px', 
        width: '100%',
        maxWidth: '100%',
        margin: '0 auto',
        minHeight: 280,
      }}>
        {children}
      </Content>
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

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

function App() {
  const [isDarkMode, setIsDarkMode] = useState(() => localStorage.getItem('theme') === 'dark');

  const toggleTheme = useCallback(() => {
    setIsDarkMode(prev => {
      const next = !prev;
      localStorage.setItem('theme', next ? 'dark' : 'light');
      return next;
    });
  }, []);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  const currentTheme = useMemo(() => getThemeConfig(isDarkMode), [isDarkMode]);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <ThemeContext.Provider value={{ isDarkMode, toggleTheme }}>
          <ConfigProvider locale={ruRU} theme={currentTheme}>
          <AntApp>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={
                <ConfigProvider theme={getThemeConfig(false)} locale={ruRU}>
                  <LoginPage />
                </ConfigProvider>
              } />
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
        </ThemeContext.Provider>
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
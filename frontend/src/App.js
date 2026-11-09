import React, { useState, useEffect, useRef, useCallback, createContext, useMemo } from 'react';
import { BrowserRouter, Routes, Route, Navigate, useNavigate, useLocation } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntApp, Layout, Menu, Button, Dropdown, Space, Avatar, message, Modal, Drawer, theme, Badge } from 'antd';
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
  EditOutlined,
  ApiOutlined,
  MailOutlined,
  SendOutlined,
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
import NotesPage from './pages/NotesPage';
import IntegrationsPage from './pages/IntegrationsPage';
import ChangePasswordModal from './pages/ChangePasswordModal';
import TwoFactorSettings from './components/TwoFactorSettings';
import SmtpSettingsModal from './components/SmtpSettingsModal';
import ErrorBoundary from './components/ErrorBoundary';

import './App.css';

dayjs.locale('ru');

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

const IDLE_TIMEOUT_MS = (Number(process.env.REACT_APP_IDLE_TIMEOUT_MINUTES) || 12 * 60) * 60 * 1000;

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

const rawVersion = process.env.REACT_APP_VERSION || 'v0.3.0';
export const APP_VERSION = rawVersion.startsWith('v') ? rawVersion : `v${rawVersion}`;

const forceLogout = () => {
  if (window.location.pathname === '/login') return;
  tokenStorage.clear();
  window.location.href = '/login';
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    const isLoginPage = window.location.pathname === '/login';
    const isRefreshEndpoint = originalRequest?.url?.includes('/auth/refresh');

    const isTokenError = error.response?.status === 401;

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
    colorWarning: '#d29922',
    colorError: '#f85149',
    colorTextBase: '#e6edf3',
    colorTextSecondary: '#8b949e',
    colorTextPlaceholder: 'rgba(255, 255, 255, 0.45)',
    colorBgBase: '#0d1117',
    colorBgLayout: '#0d1117',
    colorBgContainer: '#161b22',
    colorBgElevated: '#161b22',
    colorBorder: 'rgba(240, 246, 252, 0.1)',
    colorBorderSecondary: 'rgba(240, 246, 252, 0.06)',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    borderRadius: 6,
    boxShadow: 'none',
    boxShadowSecondary: '0 2px 8px rgba(0, 0, 0, 0.3)',
  } : {
    colorPrimary: '#4f46e5',
    colorInfo: '#3b82f6',
    colorSuccess: '#16a34a',
    colorWarning: '#d97706',
    colorError: '#dc2626',
    colorTextBase: '#0f172a',
    colorTextSecondary: '#475569',
    colorBgBase: '#ffffff',
    colorBgLayout: '#f8fafc',
    colorBorder: 'rgba(15, 23, 42, 0.08)',
    colorBorderSecondary: 'rgba(15, 23, 42, 0.04)',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    borderRadius: 6,
    wireframe: false,
    boxShadow: 'none',
    boxShadowSecondary: '0 2px 8px rgba(15, 23, 42, 0.04)',
  },
  components: isDark ? {
    Layout: {
      siderBg: '#161b22',
      headerBg: '#161b22',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(88, 166, 255, 0.12)',
      itemSelectedColor: '#58a6ff',
      itemHoverBg: 'rgba(240, 246, 252, 0.06)',
      itemBorderRadius: 6,
    },
    Table: {
      headerBg: '#161b22',
      headerColor: '#e6edf3',
      rowHoverBg: 'rgba(240, 246, 252, 0.04)',
      borderColor: 'rgba(240, 246, 252, 0.1)',
      headerBorderRadius: 6,
    },
    Card: {
      colorBgContainer: '#161b22',
      colorBorderSecondary: 'rgba(240, 246, 252, 0.1)',
      borderRadiusLG: 10,
    },
    Button: {
      borderRadius: 6,
      controlHeight: 36,
      fontWeight: 500,
    },
    Input: {
      borderRadius: 6,
      controlHeight: 36,
    },
    Select: {
      borderRadius: 6,
      controlHeight: 36,
    }
  } : {
    Layout: {
      siderBg: '#ffffff',
      headerBg: '#ffffff',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: 'rgba(79, 70, 229, 0.08)',
      itemSelectedColor: '#4f46e5',
      itemBorderRadius: 6,
      itemMarginInline: 8,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#475569',
      rowHoverBg: '#f1f5f9',
      cellPaddingBlock: 12,
      borderColor: 'rgba(15, 23, 42, 0.08)',
      headerBorderRadius: 6,
    },
    Card: {
      borderRadiusLG: 10,
      boxShadow: 'none',
      colorBorderSecondary: 'rgba(15, 23, 42, 0.08)',
    },
    Button: {
      borderRadius: 6,
      controlHeight: 36,
      fontWeight: 500,
    },
    Input: {
      borderRadius: 6,
      controlHeight: 36,
      hoverBorderColor: '#4f46e5',
      activeBorderColor: '#4f46e5',
    },
    Select: {
      borderRadius: 6,
      controlHeight: 36,
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
  const [smtpModalOpen, setSmtpModalOpen] = useState(false);
  const [smtpConnected, setSmtpConnected] = useState(null);
  const [smtpStatusLoading, setSmtpStatusLoading] = useState(false);
  const [smtpSendingTest, setSendingTest] = useState(false);

  const isSmtpManager = useMemo(() => {
    const email = (user?.email || '').trim().toLowerCase();
    return email === 'yuliya.e.novikova@rt.ru' || user?.role === 'superadmin';
  }, [user]);

  const checkSmtpStatus = useCallback(async () => {
    if (!isSmtpManager) return;
    setSmtpStatusLoading(true);
    try {
      const res = await api.get('/notifications/smtp-settings');
      setSmtpConnected(Boolean(res.data?.connected));
    } catch (err) {
      setSmtpConnected(false);
    } finally {
      setSmtpStatusLoading(false);
    }
  }, [isSmtpManager]);

  useEffect(() => {
    if (isSmtpManager) {
      checkSmtpStatus();
    }
  }, [isSmtpManager, checkSmtpStatus]);

  const handleSendQuickTestEmail = async () => {
    setSendingTest(true);
    try {
      const res = await api.post('/notifications/smtp-send-test');
      message.success(res.data?.message || 'Тестовое письмо успешно отправлено на вашу почту!');
      setSmtpConnected(true);
    } catch (err) {
      const errMsg = err?.response?.data?.detail || 'Не удалось отправить тестовое письмо';
      message.error(errMsg);
      setSmtpConnected(false);
    } finally {
      setSendingTest(false);
    }
  };

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
    if (path === '/notes') return 'notes';
    if (path === '/dashboards') return 'dashboards';
    if (path === '/integrations') return 'integrations';
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
    window.addEventListener('focus', resetIdleTimer);
    const handleVisibility = () => {
      if (document.visibilityState === 'visible') {
        resetIdleTimer();
      }
    };
    document.addEventListener('visibilitychange', handleVisibility);
    resetIdleTimer();

    return () => {
      events.forEach(e => window.removeEventListener(e, resetIdleTimer));
      window.removeEventListener('focus', resetIdleTimer);
      document.removeEventListener('visibilitychange', handleVisibility);
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

  menuItems.push({
    key: 'notes',
    icon: <EditOutlined />,
    label: 'Заметки',
    onClick: () => navigate('/notes'),
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

  if (isAdmin) {
    menuItems.push({
      key: 'integrations',
      icon: <ApiOutlined />,
      label: 'Интеграции API',
      onClick: () => navigate('/integrations'),
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
    ...(isSmtpManager ? [
      { type: 'divider' },
      {
        key: 'smtp-settings',
        icon: <MailOutlined />,
        label: (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
            <span>Пароль почты</span>
            {smtpStatusLoading ? (
              <Badge status="processing" text={<span style={{ fontSize: 11, color: isDarkMode ? '#8b949e' : '#64748b' }}>проверка</span>} />
            ) : smtpConnected === true ? (
              <Badge status="success" text={<span style={{ fontSize: 11, color: '#16a34a', fontWeight: 500 }}>Связь есть</span>} />
            ) : smtpConnected === false ? (
              <Badge status="error" text={<span style={{ fontSize: 11, color: '#dc2626', fontWeight: 500 }}>Нет связи</span>} />
            ) : null}
          </div>
        ),
        onClick: () => setSmtpModalOpen(true),
      },
      {
        key: 'smtp-test-email',
        icon: <SendOutlined />,
        label: smtpSendingTest ? 'Отправка теста...' : 'Тестовое письмо на почту',
        disabled: smtpSendingTest,
        onClick: handleSendQuickTestEmail,
      },
    ] : []),
    {
      key: 'version',
      label: <span style={{ fontSize: 12, color: isDarkMode ? '#8b949e' : '#64748b' }}>Версия {APP_VERSION}</span>,
      disabled: true,
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
        height: 56,
        padding: isMobile ? '0 16px' : '0 32px', 
        background: 'var(--header-bg)', 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        borderBottom: '1px solid var(--border-color)',
        boxShadow: 'none',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 28, flex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {isMobile && (
              <Button
                type="text"
                icon={<MenuUnfoldOutlined />}
                onClick={() => setMobileMenuOpen(true)}
                data-testid="sidebar-toggle"
              />
            )}
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginRight: 20 }}>
              <span style={{ 
                fontSize: 24, 
                fontWeight: 700, 
                background: 'linear-gradient(135deg, #4f46e5 0%, #ec4899 100%)',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '-0.5px'
              }}>
                RMS
              </span>
              <span style={{
                fontSize: 11,
                fontWeight: 500,
                color: isDarkMode ? '#8b949e' : '#64748b',
                background: isDarkMode ? 'rgba(255, 255, 255, 0.06)' : 'rgba(15, 23, 42, 0.05)',
                padding: '2px 6px',
                borderRadius: 4,
                lineHeight: 1.2
              }}>
                {APP_VERSION}
              </span>
            </div>
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
                lineHeight: '54px',
                fontSize: 14,
                fontWeight: 500
              }}
            />
          )}
        </div>

        <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
          <Space style={{ cursor: 'pointer', paddingLeft: 16 }} data-testid="user-menu">
            <Avatar 
              size={36}
              style={{ background: 'linear-gradient(135deg, #4f46e5 0%, #ec4899 100%)' }} 
              icon={<UserOutlined />} 
            />
            {!isMobile && <span style={{ fontWeight: 500, color: 'var(--text-color)', fontSize: 14 }}>{user?.full_name}</span>}
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
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
              <span style={{ fontSize: 24, fontWeight: 700, background: 'linear-gradient(135deg, #4f46e5 0%, #ec4899 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', letterSpacing: '-0.5px' }}>
                RMS
              </span>
              <span style={{ fontSize: 12, fontWeight: 600, color: isDarkMode ? '#8b949e' : '#64748b' }}>
                {APP_VERSION}
              </span>
            </div>
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
      {isSmtpManager && (
        <SmtpSettingsModal
          open={smtpModalOpen}
          onClose={() => setSmtpModalOpen(false)}
          user={user}
          onStatusChange={(data) => setSmtpConnected(Boolean(data?.connected))}
        />
      )}
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
                path="/notes"
                element={
                  <ProtectedRoute>
                    <NotesPage />
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
              <Route
                path="/integrations"
                element={
                  <ProtectedRoute>
                    <IntegrationsPage />
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
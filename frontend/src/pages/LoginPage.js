import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, message, Spin, Modal, Alert } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, SafetyCertificateOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { api, APP_VERSION } from '../App';
import { tokenStorage } from '../tokenStorage';
import ChangePasswordModal from './ChangePasswordModal';

const LoginPage = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [forceChangeOpen, setForceChangeOpen] = useState(false);
  const [loginError, setLoginError] = useState('');

  const [requires2fa, setRequires2fa] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [twoFaLoading, setTwoFaLoading] = useState(false);

  React.useEffect(() => {
    document.documentElement.setAttribute('data-theme', 'light');
    document.documentElement.classList.remove('dark');
    return () => {
      const userTheme = localStorage.getItem('theme') === 'dark' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', userTheme);
      if (userTheme === 'dark') {
        document.documentElement.classList.add('dark');
      } else {
        document.documentElement.classList.remove('dark');
      }
    };
  }, []);

  const onFinish = async (values) => {
    setLoading(true);
    setLoginError('');
    try {
      const loginResponse = await api.post('/auth/login', {
        email: values.email,
        password: values.password,
      });

      const data = loginResponse.data;

      if (data.requires_2fa) {
        setTempToken(data.temp_token);
        setRequires2fa(true);
        setLoading(false);
        return;
      }

      await _finalizeLogin(data);
    } catch (error) {
      handleLoginError(error);
    } finally {
      setLoading(false);
    }
  };

  const handleTwoFaSubmit = async () => {
    if (!totpCode || totpCode.length !== 6) {
      setLoginError('Введите 6-значный код из приложения-аутентификатора');
      return;
    }
    setTwoFaLoading(true);
    setLoginError('');
    try {
      const resp = await api.post('/auth/2fa/verify', {
        temp_token: tempToken,
        code: totpCode,
      });
      await _finalizeLogin(resp.data);
    } catch (error) {
      handleLoginError(error);
    } finally {
      setTwoFaLoading(false);
    }
  };

  const _finalizeLogin = async (data) => {
    const { access_token, refresh_token, is_temporary_password, user } = data;
    tokenStorage.setAccess(access_token);
    if (refresh_token) {
      tokenStorage.setRefresh(refresh_token);
    }

    if (user) {
      tokenStorage.setUser(user);
    }

    try {
      let userResponse = null;
      for (let attempt = 0; attempt < 3; attempt++) {
        try {
          userResponse = await api.get('/auth/me');
          break;
        } catch (err) {
          if (attempt < 2 && !user) {
            await new Promise(r => setTimeout(r, 200 * (attempt + 1)));
          } else if (!user) {
            throw err;
          }
        }
      }
      if (userResponse?.data) {
        tokenStorage.setUser(userResponse.data);
      }
    } catch (err) {
      if (!user) {
        throw err;
      }
    }

    if (is_temporary_password) {
      setForceChangeOpen(true);
    } else {
      message.success('Добро пожаловать!');
      navigate('/');
    }
  };

  const handleLoginError = (error) => {
    if (error.response?.status === 401) {
      const detail = error.response?.data?.detail || 'Неверный логин или пароль';
      setLoginError(detail);
    } else if (error.response?.status === 429) {
      setLoginError('Слишком много попыток. Подождите несколько минут.');
    } else if (error.response?.status === 422) {
      setLoginError('Проверьте правильность введённых данных');
    } else {
      const errorMsg = error.response?.data?.detail || 'Ошибка авторизации';
      setLoginError(typeof errorMsg === 'string' ? errorMsg : 'Ошибка авторизации');
    }
  };

  const handleForceChangeSuccess = async () => {
    setForceChangeOpen(false);

    try {
      const userResponse = await api.get('/auth/me');
      tokenStorage.setUser(userResponse.data);
    } catch {

    }
    message.success('Пароль создан. Добро пожаловать!');
    navigate('/');
  };

  return (
    <div className="login-container">
      <div className="login-card">
        <div className="login-logo">
          <h1>RMS</h1>
        </div>

        {}
        {loginError && (
          <Alert
            message="Ошибка входа"
            description={loginError}
            type="error"
            showIcon
            icon={<CloseCircleOutlined />}
            style={{ marginBottom: 16 }}
            data-testid="login-error-alert"
          />
        )}

        {}
        {!requires2fa && !forgotModalOpen && (
          <Spin spinning={loading}>
            <Form
              form={form}
              name="login"
              onFinish={onFinish}
              layout="vertical"
              size="large"
              preserve={true}
            >
              <Form.Item
                name="email"
                rules={[
                  { required: true, message: 'Введите email' },
                  { type: 'email', message: 'Неверный формат email' },
                ]}
              >
                <Input
                  prefix={<UserOutlined />}
                  placeholder="Email"
                  data-testid="login-email"
                />
              </Form.Item>

              <Form.Item
                name="password"
                rules={[{ required: true, message: 'Введите пароль' }]}
              >
                <Input.Password
                  prefix={<LockOutlined />}
                  placeholder="Пароль"
                  data-testid="login-password"
                />
              </Form.Item>

              <Form.Item>
                <Button
                  type="primary"
                  htmlType="submit"
                  block
                  data-testid="login-submit"
                >
                  Войти
                </Button>
              </Form.Item>
            </Form>
          </Spin>
        )}

        {}
        {requires2fa && (
          <div>
            <Alert
              message="Двухфакторная аутентификация"
              description="Введите 6-значный код из приложения-аутентификатора (Aladdin TOTP, Google Authenticator и др.)"
              type="info"
              showIcon
              icon={<SafetyCertificateOutlined />}
              style={{ marginBottom: 16 }}
            />
            <Input
              prefix={<SafetyCertificateOutlined />}
              placeholder="000000"
              maxLength={6}
              size="large"
              value={totpCode}
              onChange={(e) => setTotpCode(e.target.value.replace(/\D/g, ''))}
              onPressEnter={handleTwoFaSubmit}
              style={{ marginBottom: 12, letterSpacing: 8, textAlign: 'center', fontSize: 20 }}
              data-testid="totp-code-input"
            />
            <Button
              type="primary"
              block
              size="large"
              loading={twoFaLoading}
              onClick={handleTwoFaSubmit}
              data-testid="totp-submit"
            >
              Подтвердить
            </Button>
            <Button
              type="link"
              block
              style={{ marginTop: 8 }}
              onClick={() => { setRequires2fa(false); setTotpCode(''); setLoginError(''); }}
            >
              ← Назад
            </Button>
          </div>
        )}

        {!requires2fa && !forgotModalOpen && (
          <div style={{ textAlign: 'center' }}>
            <Button
              type="link"
              onClick={() => { setForgotModalOpen(true); setLoginError(''); }}
              style={{ padding: 0, fontSize: 13 }}
              data-testid="forgot-password-link"
            >
              Забыли пароль?
            </Button>
          </div>
        )}

        {forgotModalOpen && (
          <div>
            <div style={{ textAlign: 'center', padding: '20px 0' }}>
              <SafetyCertificateOutlined style={{ fontSize: 48, color: '#1890ff', marginBottom: 16 }} />
              <h3 style={{ marginBottom: 16 }}>Восстановление пароля</h3>
              <p style={{ color: '#595959', fontSize: 14 }}>
                В целях безопасности автоматический сброс пароля отключен. 
                <br /><br />
                Пожалуйста, обратитесь к <strong>Главному администратору</strong> вашей системы для получения нового временного пароля.
              </p>
            </div>
            <Button
              type="primary"
              block
              size="large"
              style={{ marginTop: 16 }}
              onClick={() => { setForgotModalOpen(false); }}
            >
              Понятно, вернуться к входу
            </Button>
          </div>
        )}
      </div>

      {}
      <ChangePasswordModal
        open={forceChangeOpen}
        onSuccess={handleForceChangeSuccess}
        forced={true}
        loginContext={true}
      />

      <div style={{
        position: 'fixed',
        bottom: 12,
        right: 16,
        fontSize: 12,
        color: '#64748b',
        fontWeight: 500,
        background: 'rgba(255, 255, 255, 0.85)',
        padding: '3px 8px',
        borderRadius: 4,
        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
      }}>
        RMS v{APP_VERSION}
      </div>
    </div>
  );
};

export default LoginPage;
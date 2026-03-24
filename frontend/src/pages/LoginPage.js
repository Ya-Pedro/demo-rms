import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Form, Input, Button, message, Spin, Modal, Alert } from 'antd';
import { UserOutlined, LockOutlined, MailOutlined, SafetyCertificateOutlined, CloseCircleOutlined } from '@ant-design/icons';
import { api } from '../App';
import { tokenStorage } from '../tokenStorage';
import ChangePasswordModal from './ChangePasswordModal';

const LoginPage = () => {
  const navigate = useNavigate();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [forgotModalOpen, setForgotModalOpen] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotForm] = Form.useForm();
  const [forceChangeOpen, setForceChangeOpen] = useState(false);
  const [loginError, setLoginError] = useState('');

  const [requires2fa, setRequires2fa] = useState(false);
  const [tempToken, setTempToken] = useState('');
  const [totpCode, setTotpCode] = useState('');
  const [twoFaLoading, setTwoFaLoading] = useState(false);

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
    const { access_token, refresh_token, is_temporary_password } = data;
    tokenStorage.setAccess(access_token);
    if (refresh_token) {
      tokenStorage.setRefresh(refresh_token);
    }
    const userResponse = await api.get('/auth/me');
    tokenStorage.setUser(userResponse.data);

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

  const handleForgotPassword = async () => {
    try {
      const values = await forgotForm.validateFields();
      setForgotLoading(true);
      await api.post('/auth/forgot-password', { email: values.forgot_email });
      message.success('Если email зарегистрирован, новый пароль отправлен на почту');
      setForgotModalOpen(false);
      forgotForm.resetFields();
    } catch (error) {
      if (error.response?.status === 429) {
        message.error('Слишком много запросов. Подождите 15 минут.');
      } else {
        const msg = error.response?.data?.detail || 'Ошибка отправки';
        message.error(msg);
      }
    } finally {
      setForgotLoading(false);
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
          <p>Recruitment Management System</p>
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
        {!requires2fa && (
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

        {!requires2fa && (
          <div style={{ textAlign: 'center' }}>
            <Button
              type="link"
              onClick={() => setForgotModalOpen(true)}
              style={{ padding: 0, fontSize: 13 }}
              data-testid="forgot-password-link"
            >
              Забыли пароль?
            </Button>
          </div>
        )}

        <div style={{ textAlign: 'center', marginTop: 16, color: '#8c8c8c', fontSize: 12 }}>
          Внутренняя система управления вакансиями
        </div>
      </div>

      {}
      <Modal
        title="Восстановление пароля"
        open={forgotModalOpen}
        onCancel={() => { setForgotModalOpen(false); forgotForm.resetFields(); }}
        onOk={handleForgotPassword}
        okText="Отправить"
        cancelText="Отмена"
        confirmLoading={forgotLoading}
        width={420}
      >
        <p style={{ marginBottom: 16, color: '#595959', fontSize: 13 }}>
          Введите email вашей учётной записи. Новый временный пароль будет отправлен на указанный адрес.
        </p>
        <Form form={forgotForm} layout="vertical">
          <Form.Item
            name="forgot_email"
            rules={[
              { required: true, message: 'Введите email' },
              { type: 'email', message: 'Неверный формат email' },
            ]}
          >
            <Input
              prefix={<MailOutlined />}
              placeholder="Email"
              data-testid="forgot-email-input"
            />
          </Form.Item>
        </Form>
      </Modal>

      {}
      <ChangePasswordModal
        open={forceChangeOpen}
        onSuccess={handleForceChangeSuccess}
        forced={true}
      />
    </div>
  );
};

export default LoginPage;
import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Alert,
  Space,
  Typography,
  Divider,
  Tag,
  message,
  notification,
  Spin,
} from 'antd';
import {
  MailOutlined,
  KeyOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SendOutlined,
  ReloadOutlined,
  SettingOutlined,
  LockOutlined,
} from '@ant-design/icons';
import { api } from '../App';

const { Text } = Typography;

const SmtpSettingsModal = ({ open, onClose, user, onStatusChange }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [sendingTest, setSendingTest] = useState(false);
  const [smtpInfo, setSmtpInfo] = useState(null);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const fetchSettings = async () => {
    setLoading(true);
    try {
      const res = await api.get('/notifications/smtp-settings');
      setSmtpInfo(res.data);
      form.setFieldsValue({
        username: res.data.smtp_username || '',
        from_email: res.data.smtp_from || '',
        server: res.data.smtp_server || 'smtp.yandex.ru',
        port: res.data.smtp_port || 465,
        password: '',
      });
      if (onStatusChange) {
        onStatusChange(res.data);
      }
    } catch (err) {
      console.error('Failed to load SMTP settings:', err);
      message.error('Не удалось загрузить настройки почтового сервиса');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) {
      fetchSettings();
    } else {
      form.resetFields();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handleTestConnection = async () => {
    setTesting(true);
    try {
      const values = form.getFieldsValue();
      const res = await api.post('/notifications/smtp-test-connection', {
        password: values.password || undefined,
        username: values.username || undefined,
        server: values.server || undefined,
        port: values.port ? Number(values.port) : undefined,
      });

      if (res.data.connected) {
        message.success(res.data.message || 'Связь с почтовым сервером успешно установлена!');
      } else {
        message.error(res.data.message || 'Не удалось связаться с почтовым сервером');
      }

      setSmtpInfo((prev) => ({
        ...prev,
        connected: res.data.connected,
        connection_message: res.data.message,
      }));
      if (onStatusChange) {
        onStatusChange({
          ...smtpInfo,
          connected: res.data.connected,
          connection_message: res.data.message,
        });
      }
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      message.error(`Ошибка при проверке связи: ${detail}`);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (!values.password || !values.password.trim()) {
        message.warning('Пожалуйста, введите новый пароль для почты');
        return;
      }

      setSaving(true);
      const res = await api.post('/notifications/smtp-settings', {
        password: values.password.trim(),
        username: values.username ? values.username.trim() : undefined,
        from_email: values.from_email ? values.from_email.trim() : undefined,
        server: values.server ? values.server.trim() : undefined,
        port: values.port ? Number(values.port) : undefined,
      });

      if (res.data.connected) {
        notification.success({
          message: 'Пароль почты успешно сохранен',
          description: 'Связь с почтовым сервером установлена. Почтовые уведомления готовы к отправке.',
          placement: 'topRight',
        });
      } else {
        notification.warning({
          message: 'Пароль сохранен в системе',
          description: res.data.message,
          placement: 'topRight',
          duration: 8,
        });
      }

      form.setFieldsValue({ password: '' });
      await fetchSettings();
      onClose();
    } catch (err) {
      if (err.errorFields) return;
      const detail = err.response?.data?.detail || err.message;
      message.error(`Ошибка сохранения: ${detail}`);
    } finally {
      setSaving(false);
    }
  };

  const handleSendTestEmail = async () => {
    setSendingTest(true);
    try {
      const res = await api.post('/notifications/smtp-send-test', {
        template: 'reminder',
      });

      const recipient = res.data.recipient;
      notification.success({
        message: 'Тестовое письмо отправлено',
        description: `Тестовое уведомление успешно отправлено на адрес ${recipient}. Пожалуйста, проверьте папку «Входящие».`,
        placement: 'topRight',
        duration: 7,
      });
    } catch (err) {
      const detail = err.response?.data?.detail || err.message;
      notification.error({
        message: 'Ошибка отправки тестового письма',
        description: String(detail),
        placement: 'topRight',
        duration: 8,
      });
    } finally {
      setSendingTest(false);
    }
  };

  const isConnected = smtpInfo?.connected;

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <MailOutlined style={{ color: '#1677ff', fontSize: 18 }} />
          <span>Настройки пароля почтового сервиса (SMTP)</span>
        </div>
      }
      footer={[
        <Button key="cancel" onClick={onClose}>
          Закрыть
        </Button>,
        <Button
          key="test"
          icon={<ReloadOutlined />}
          onClick={handleTestConnection}
          loading={testing}
        >
          Проверить связь
        </Button>,
        <Button
          key="save"
          type="primary"
          icon={<CheckCircleOutlined />}
          onClick={handleSave}
          loading={saving}
        >
          Сохранить пароль
        </Button>,
      ]}
      width={560}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '36px 0' }}>
          <Spin tip="Загрузка настроек почты..." />
        </div>
      ) : (
        <div style={{ paddingTop: 8 }}>
          {/* Статус связи */}
          <div style={{ marginBottom: 16 }}>
            {isConnected ? (
              <Alert
                type="success"
                showIcon
                icon={<CheckCircleOutlined style={{ fontSize: 18 }} />}
                message={
                  <div style={{ fontWeight: 600 }}>
                    Связь с почтовым сервером установлена
                  </div>
                }
                description={
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    Авторизация под текущим паролем работает корректно. Рассылки и уведомления отправляются штатно.
                  </div>
                }
              />
            ) : (
              <Alert
                type="error"
                showIcon
                icon={<CloseCircleOutlined style={{ fontSize: 18 }} />}
                message={
                  <div style={{ fontWeight: 600 }}>
                    Требуется обновить пароль к почте
                  </div>
                }
                description={
                  <div style={{ fontSize: 12, marginTop: 4 }}>
                    {smtpInfo?.connection_message || 'Нет связи с сервером. Введите актуальный пароль ниже.'}
                  </div>
                }
              />
            )}
          </div>

          <div
            style={{
              background: 'var(--table-header-bg, #f8fafc)',
              border: '1px solid var(--border-color, #e2e8f0)',
              borderRadius: 8,
              padding: '12px 16px',
              marginBottom: 16,
              fontSize: 12,
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <Text type="secondary">Ответственный за почту:</Text>
              <Text strong>{smtpInfo?.manager_email || user?.email}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
              <Text type="secondary">Почтовый сервер:</Text>
              <Text code>{smtpInfo?.smtp_server}:{smtpInfo?.smtp_port}</Text>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <Text type="secondary">Логин / Отправитель:</Text>
              <Text strong>{smtpInfo?.smtp_username || smtpInfo?.smtp_from || 'Не указан'}</Text>
            </div>
          </div>

          <Form form={form} layout="vertical">
            <Form.Item
              name="password"
              label={
                <span style={{ fontWeight: 600 }}>
                  Новый пароль от почты <Text type="secondary" style={{ fontWeight: 400 }}>(обновляется раз в 3 мес.)</Text>
                </span>
              }
              rules={[{ required: true, message: 'Пожалуйста, укажите новый пароль' }]}
              extra="Введите новый корпоративный пароль (или пароль приложения почты) и нажмите «Сохранить пароль»."
            >
              <Input.Password
                prefix={<KeyOutlined style={{ color: '#94a3b8' }} />}
                placeholder="Введите новый пароль..."
                size="large"
                autoComplete="new-password"
              />
            </Form.Item>

            {/* Быстрая отправка теста прямо из модалки */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '10px 14px',
                background: '#f0fdf4',
                border: '1px solid #bbf7d0',
                borderRadius: 6,
                marginBottom: 16,
              }}
            >
              <div>
                <div style={{ fontWeight: 600, fontSize: 13, color: '#166534' }}>
                  Проверка доставки
                </div>
                <div style={{ fontSize: 11, color: '#15803d' }}>
                  Отправить тестовое письмо на {user?.email}
                </div>
              </div>
              <Button
                type="primary"
                size="small"
                icon={<SendOutlined />}
                style={{ background: '#16a34a', borderColor: '#16a34a' }}
                loading={sendingTest}
                onClick={handleSendTestEmail}
              >
                Отправить тест
              </Button>
            </div>

            <div style={{ textAlign: 'right', marginBottom: 8 }}>
              <Button
                type="link"
                size="small"
                icon={<SettingOutlined />}
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{ padding: 0, fontSize: 12 }}
              >
                {showAdvanced ? 'Скрыть доп. параметры' : 'Дополнительные параметры сервера'}
              </Button>
            </div>

            {showAdvanced && (
              <div
                style={{
                  border: '1px dashed var(--border-color, #cbd5e1)',
                  borderRadius: 6,
                  padding: 12,
                  marginBottom: 8,
                }}
              >
                <Form.Item name="username" label="Логин SMTP (Email)" style={{ marginBottom: 12 }}>
                  <Input placeholder="user@company.ru" />
                </Form.Item>
                <Form.Item name="from_email" label="Адрес отправителя (From)" style={{ marginBottom: 12 }}>
                  <Input placeholder="user@company.ru" />
                </Form.Item>
                <div style={{ display: 'flex', gap: 12 }}>
                  <Form.Item name="server" label="Сервер" style={{ flex: 1, marginBottom: 0 }}>
                    <Input placeholder="smtp.yandex.ru" />
                  </Form.Item>
                  <Form.Item name="port" label="Порт" style={{ width: 100, marginBottom: 0 }}>
                    <Input placeholder="465" />
                  </Form.Item>
                </div>
              </div>
            )}
          </Form>
        </div>
      )}
    </Modal>
  );
};

export default SmtpSettingsModal;

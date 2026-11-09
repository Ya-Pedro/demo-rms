import React, { useState, useEffect } from 'react';
import {
  Modal,
  Form,
  Input,
  Button,
  Space,
  Typography,
  Badge,
  message,
  notification,
  Spin,
} from 'antd';
import { api } from '../App';

const { Text } = Typography;

const extractErrorMessage = (err, fallback = 'Произошла ошибка') => {
  if (!err) return fallback;
  const detail = err.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (typeof d === 'string' ? d : d?.msg || d?.type || JSON.stringify(d)))
      .join('; ');
  }
  if (detail && typeof detail === 'object') {
    return detail.msg || detail.message || JSON.stringify(detail);
  }
  if (typeof err.message === 'string') return err.message;
  return fallback;
};

const SmtpSettingsModal = ({ open, onClose, user }) => {
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
      setShowAdvanced(false);
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
        message.success(res.data.message || 'Связь с почтовым сервером успешно установлена');
      } else {
        message.error(res.data.message || 'Не удалось связаться с почтовым сервером');
      }

      setSmtpInfo((prev) => ({
        ...prev,
        connected: res.data.connected,
        connection_message: res.data.message,
      }));
    } catch (err) {
      const errorText = extractErrorMessage(err, 'Ошибка при проверке связи');
      message.error(errorText);
    } finally {
      setTesting(false);
    }
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (!values.password || !values.password.trim()) {
        message.warning('Пожалуйста, введите новый пароль');
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
          message: 'Пароль сохранен',
          description: 'Связь с почтовым сервером установлена.',
          placement: 'topRight',
        });
      } else {
        notification.warning({
          message: 'Пароль сохранен',
          description: res.data.message || 'Проверьте связь с почтовым сервером',
          placement: 'topRight',
          duration: 6,
        });
      }

      form.setFieldsValue({ password: '' });
      await fetchSettings();
      onClose();
    } catch (err) {
      if (err.errorFields) return;
      const errorText = extractErrorMessage(err, 'Ошибка сохранения');
      message.error(errorText);
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

      const recipient = res.data?.recipient || user?.email;
      notification.success({
        message: 'Тестовое письмо отправлено',
        description: `Письмо отправлено на адрес ${recipient}. Пожалуйста, проверьте папку «Входящие».`,
        placement: 'topRight',
        duration: 6,
      });
    } catch (err) {
      const errorText = extractErrorMessage(err, 'Ошибка отправки тестового письма');
      notification.error({
        message: 'Ошибка отправки тестового письма',
        description: errorText,
        placement: 'topRight',
        duration: 7,
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
      title="Пароль почтового сервиса"
      footer={
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
          <Button
            onClick={handleSendTestEmail}
            loading={sendingTest}
            disabled={loading}
          >
            Отправить тестовое письмо
          </Button>
          <Space>
            <Button onClick={onClose}>
              Отмена
            </Button>
            <Button
              type="primary"
              onClick={handleSave}
              loading={saving}
              disabled={loading}
            >
              Сохранить
            </Button>
          </Space>
        </div>
      }
      width={480}
      destroyOnClose
    >
      {loading ? (
        <div style={{ textAlign: 'center', padding: '32px 0' }}>
          <Spin />
        </div>
      ) : (
        <div style={{ paddingTop: 12 }}>
          {/* Минималистичный показ связи */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 14px',
              background: 'var(--table-header-bg, #f8fafc)',
              border: '1px solid var(--border-color, #e2e8f0)',
              borderRadius: 6,
              marginBottom: isConnected || !smtpInfo?.connection_message ? 20 : 8,
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ fontSize: 13, color: 'var(--text-secondary, #64748b)' }}>
                Связь с сервером:
              </span>
              {testing ? (
                <Badge status="processing" text={<span style={{ fontSize: 13 }}>проверка...</span>} />
              ) : isConnected ? (
                <Badge status="success" text={<span style={{ fontSize: 13, fontWeight: 500 }}>Подключено</span>} />
              ) : (
                <Badge status="error" text={<span style={{ fontSize: 13, fontWeight: 500 }}>Нет связи</span>} />
              )}
            </div>
            <Button
              type="link"
              size="small"
              onClick={handleTestConnection}
              loading={testing}
              style={{ padding: 0, fontSize: 12 }}
            >
              Проверить связь
            </Button>
          </div>

          {!isConnected && smtpInfo?.connection_message && (
            <div style={{ marginBottom: 18, paddingLeft: 2 }}>
              <Text type="secondary" style={{ fontSize: 12 }}>
                {smtpInfo.connection_message}
              </Text>
            </div>
          )}

          <Form form={form} layout="vertical">
            <Form.Item
              name="password"
              label="Новый пароль"
              rules={[{ required: true, message: 'Пожалуйста, укажите новый пароль' }]}
              style={{ marginBottom: 16 }}
            >
              <Input.Password
                placeholder="Введите новый пароль"
                autoComplete="new-password"
              />
            </Form.Item>

            <div style={{ textAlign: 'right', marginTop: -4, marginBottom: 8 }}>
              <Button
                type="link"
                size="small"
                onClick={() => setShowAdvanced(!showAdvanced)}
                style={{ padding: 0, fontSize: 12, color: 'var(--text-secondary, #64748b)' }}
              >
                {showAdvanced ? 'Скрыть параметры сервера' : 'Параметры сервера'}
              </Button>
            </div>

            {showAdvanced && (
              <div
                style={{
                  border: '1px solid var(--border-color, #e2e8f0)',
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
                  <Form.Item name="port" label="Порт" style={{ width: 90, marginBottom: 0 }}>
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

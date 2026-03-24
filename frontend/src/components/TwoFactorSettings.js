
import React, { useState } from 'react';
import { Button, Input, Alert, Spin, Steps, Typography, Space, Divider } from 'antd';
import { SafetyCertificateOutlined, CheckCircleOutlined, LockOutlined } from '@ant-design/icons';
import { api } from '../App';

const { Title, Text, Paragraph } = Typography;

const TwoFactorSettings = ({ user, onUpdate }) => {
  const [step, setStep] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [setupData, setSetupData] = useState(null);
  const [code, setCode] = useState('');

  const [disableMode, setDisableMode] = useState(false);
  const [disableCode, setDisableCode] = useState('');

  const handleSetup = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await api.get('/auth/2fa/setup');
      setSetupData(resp.data);
      setStep(1);
    } catch (e) {
      setError('Ошибка при инициализации 2FA');
    } finally {
      setLoading(false);
    }
  };

  const handleActivate = async () => {
    if (!code || code.length !== 6) {
      setError('Введите 6-значный код из приложения');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.post('/auth/2fa/activate', {
        setup_id: setupData.setup_id || '',
        secret: setupData.secret || '',
        code,
      });
      setStep(2);
      onUpdate && onUpdate();
    } catch (e) {
      setError(e.response?.data?.detail || 'Неверный код. Попробуйте ещё раз.');
    } finally {
      setLoading(false);
    }
  };

  const handleDisable = async () => {
    if (!disableCode || disableCode.length !== 6) {
      setError('Введите 6-значный код из приложения');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.post('/auth/2fa/disable', { code: disableCode });
      setDisableMode(false);
      setDisableCode('');
      onUpdate && onUpdate();
    } catch (e) {
      setError(e.response?.data?.detail || 'Неверный код');
    } finally {
      setLoading(false);
    }
  };

  if (user?.is_2fa_enabled && !disableMode && step !== 2) {
    return (
      <div style={{ maxWidth: 480 }}>
        <Alert
          message="Двухфакторная аутентификация активирована"
          description="При каждом входе потребуется код из приложения-аутентификатора."
          type="success"
          showIcon
          icon={<CheckCircleOutlined />}
          style={{ marginBottom: 16 }}
        />
        <Button danger onClick={() => { setDisableMode(true); setError(''); }}>
          Отключить 2FA
        </Button>
      </div>
    );
  }

  if (disableMode) {
    return (
      <div style={{ maxWidth: 400 }}>
        <Title level={5}>Отключение 2FA</Title>
        <Paragraph type="secondary">
          Введите текущий 6-значный код из приложения-аутентификатора для подтверждения.
        </Paragraph>
        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 12 }} />}
        <Input
          prefix={<LockOutlined />}
          placeholder="000000"
          maxLength={6}
          size="large"
          value={disableCode}
          onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, ''))}
          onPressEnter={handleDisable}
          style={{ marginBottom: 12, letterSpacing: 6 }}
        />
        <Space>
          <Button danger loading={loading} onClick={handleDisable}>Отключить</Button>
          <Button onClick={() => { setDisableMode(false); setError(''); }}>Отмена</Button>
        </Space>
      </div>
    );
  }

  if (step === 2) {
    return (
      <Alert
        message="2FA успешно активирована!"
        description="Теперь при каждом входе будет запрашиваться код из аутентификатора."
        type="success"
        showIcon
        icon={<CheckCircleOutlined />}
      />
    );
  }

  if (step === 1 && setupData) {
    return (
      <div style={{ maxWidth: 500 }}>
        <Steps
          current={1}
          size="small"
          style={{ marginBottom: 24 }}
          items={[
            { title: 'Сканировать QR' },
            { title: 'Ввести код' },
            { title: 'Готово' },
          ]}
        />
        <Title level={5}>1. Откройте приложение-аутентификатор</Title>
        <Paragraph type="secondary">
          Поддерживаются: <strong>Aladdin TOTP</strong>, Google Authenticator,
          Microsoft Authenticator, Яндекс.Ключ и любой другой RFC 6238 совместимый аутентификатор.
        </Paragraph>
        <Title level={5}>2. Отсканируйте QR-код</Title>
        <div
          style={{ background: '#fff', display: 'inline-block', padding: 12, border: '1px solid #d9d9d9', borderRadius: 8, marginBottom: 16 }}
          dangerouslySetInnerHTML={{ __html: setupData.qr_svg }}
        />
        <Divider />
        <Title level={5}>Или введите ключ вручную:</Title>
        {setupData.secret
          ? <Text code copyable style={{ fontSize: 14 }}>{setupData.secret}</Text>
          : <Text type="secondary" style={{ fontSize: 13 }}>Ключ скрыт в целях безопасности. Используйте QR-код выше.</Text>
        }
        <Divider />
        <Title level={5}>3. Введите 6-значный код для подтверждения</Title>
        {error && <Alert message={error} type="error" showIcon style={{ marginBottom: 12 }} />}
        <Input
          prefix={<SafetyCertificateOutlined />}
          placeholder="000000"
          maxLength={6}
          size="large"
          value={code}
          onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
          onPressEnter={handleActivate}
          style={{ marginBottom: 12, letterSpacing: 6 }}
        />
        <Space>
          <Button type="primary" loading={loading} onClick={handleActivate}>
            Активировать 2FA
          </Button>
          <Button onClick={() => { setStep(0); setCode(''); setSetupData(null); setError(''); }}>
            Отмена
          </Button>
        </Space>
      </div>
    );
  }

  return (
    <div style={{ maxWidth: 480 }}>
      <Alert
        message="Двухфакторная аутентификация не активирована"
        description="Защитите аккаунт: при входе будет дополнительно запрашиваться одноразовый код из аутентификатора."
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
      />
      <Spin spinning={loading}>
        <Button
          type="primary"
          icon={<SafetyCertificateOutlined />}
          onClick={handleSetup}
        >
          Настроить 2FA
        </Button>
      </Spin>
    </div>
  );
};

export default TwoFactorSettings;
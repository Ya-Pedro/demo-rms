import React, { useState } from 'react';
import { Modal, Form, Input, message } from 'antd';
import { LockOutlined } from '@ant-design/icons';
import { api } from '../App';

const ChangePasswordModal = ({ open, onSuccess, forced }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      if (forced) {
        await api.post('/auth/change-password', {
          new_password: values.new_password,
          confirm_password: values.confirm_password,
        });
      } else {
        await api.post('/auth/change-own-password', {
          current_password: values.current_password,
          new_password: values.new_password,
          confirm_password: values.confirm_password,
        });
      }

      message.success('Пароль успешно изменён');
      form.resetFields();
      onSuccess();
    } catch (error) {
      const msg = error.response?.data?.detail || 'Ошибка смены пароля';
      message.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Modal
      title={forced ? 'Создание нового пароля' : 'Смена пароля'}
      open={open}
      onOk={handleSubmit}
      okText="Сохранить"
      cancelText={forced ? undefined : 'Отмена'}
      onCancel={forced ? undefined : onSuccess}
      closable={!forced}
      maskClosable={false}
      keyboard={false}
      confirmLoading={loading}
      cancelButtonProps={forced ? { style: { display: 'none' } } : undefined}
      data-testid="change-password-modal"
    >
      {forced && (
        <div style={{
          marginBottom: 16,
          padding: 12,
          background: 'var(--layout-bg)',
          border: '1px solid var(--border-color)',
          color: 'var(--text-color)',
          borderRadius: 4,
          fontSize: 13,
        }}>
          Вы вошли с временным паролем. Для продолжения работы необходимо создать новый пароль.
        </div>
      )}

      <Form form={form} layout="vertical">
        {!forced && (
          <Form.Item
            name="current_password"
            label="Текущий пароль"
            rules={[{ required: true, message: 'Введите текущий пароль' }]}
          >
            <Input.Password
              prefix={<LockOutlined />}
              placeholder="Текущий пароль"
              data-testid="current-password-input"
            />
          </Form.Item>
        )}

        <Form.Item
          name="new_password"
          label="Новый пароль"
          rules={[
            { required: true, message: 'Введите новый пароль' },
            { min: 8, message: 'Минимум 8 символов' },
            {
              pattern: /^(?=.*[A-ZА-ЯЁ])/,
              message: 'Пароль должен содержать хотя бы одну заглавную букву',
            },
            {
              pattern: /[!@#$%^&*()\-_=+\[\]{}|;:'",.<>?/\\`~]/,
              message: 'Пароль должен содержать хотя бы один спецсимвол (!@#$% и др.)',
            },
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Минимум 8 символов, заглавная буква и спецсимвол"
            data-testid="new-password-input"
          />
        </Form.Item>

        <Form.Item
          name="confirm_password"
          label="Повторите пароль"
          dependencies={['new_password']}
          rules={[
            { required: true, message: 'Повторите пароль' },
            ({ getFieldValue }) => ({
              validator(_, value) {
                if (!value || getFieldValue('new_password') === value) {
                  return Promise.resolve();
                }
                return Promise.reject(new Error('Пароли не совпадают'));
              },
            }),
          ]}
        >
          <Input.Password
            prefix={<LockOutlined />}
            placeholder="Повторите новый пароль"
            data-testid="confirm-password-input"
          />
        </Form.Item>

        <div style={{
          padding: '8px 12px',
          background: 'var(--layout-bg)',
          border: '1px solid var(--border-color)',
          color: 'var(--text-color)',
          borderRadius: 4,
          fontSize: 12,
          lineHeight: 1.8,
        }}>
          <strong>Требования к паролю:</strong><br />
          • Минимум 8 символов<br />
          • Хотя бы одна заглавная буква (A–Z)<br />
          • Хотя бы один спецсимвол (!@#$%^&* и др.)
        </div>
      </Form>
    </Modal>
  );
};

export default ChangePasswordModal;
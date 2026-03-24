

import React, { useState, useEffect, useMemo } from 'react';
import {
  Modal, Form, Select, DatePicker, Button, Space, Alert,
  Tag, Divider, Popconfirm, Typography, message,
} from 'antd';
import { UserSwitchOutlined, CloseCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { api } from '../App';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const DelegationModal = ({ open, vacancy, users, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [revoking, setRevoking] = useState(false);

  const activeDelegation = vacancy?.delegation;

  useEffect(() => {
    if (open) form.resetFields();
  }, [open, form]);

  const recruiterOptions = useMemo(() => {
    if (!users || !vacancy) return [];
    return users
      .filter(
        (u) =>
          u.is_active &&
          u.id !== vacancy.recruiter_id &&
          (u.role === 'recruiter' || u.role === 'admin' || u.role === 'superadmin'),
      )
      .map((u) => ({
        value: u.id,
        label: `${u.full_name} (${u.email})`,
      }));
  }, [users, vacancy]);

  const handleSubmit = async () => {
    let values;
    try {
      values = await form.validateFields();
    } catch {
      return;
    }

    const [startDate, endDate] = values.period;

    setLoading(true);
    try {
      await api.post(`/vacancies/${vacancy.id}/delegations`, {
        delegated_to_id: values.delegated_to_id,
        start_date: startDate.format('YYYY-MM-DD'),
        end_date: endDate.format('YYYY-MM-DD'),
      });
      message.success('Делегирование создано');
      form.resetFields();
      onSuccess?.();
      onClose();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Ошибка при создании делегирования';
      message.error(detail);
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async () => {
    if (!activeDelegation) return;
    setRevoking(true);
    try {
      await api.delete(`/delegations/${activeDelegation.id}`);
      message.success('Делегирование досрочно завершено');
      onSuccess?.();
      onClose();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Ошибка при отзыве делегирования';
      message.error(detail);
    } finally {
      setRevoking(false);
    }
  };

  return (
    <Modal
      title={
        <Space>
          <UserSwitchOutlined style={{ color: '#1677ff' }} />
          <span>Делегировать вакансию</span>
        </Space>
      }
      open={open}
      onCancel={onClose}
      footer={null}
      width={480}
      destroyOnClose
    >
      {vacancy && (
        <Text type="secondary" style={{ display: 'block', marginBottom: 16 }}>
          Вакансия:{' '}
          <Text strong>
            {vacancy.position_name}
            {vacancy.vacancy_id ? ` (${vacancy.vacancy_id})` : ''}
          </Text>
        </Text>
      )}

      {}
      {activeDelegation && (
        <>
          <Alert
            type="warning"
            showIcon
            style={{ marginBottom: 16 }}
            message="Активное делегирование"
            description={
              <Space direction="vertical" size={2}>
                <span>
                  Временный рекрутер:{' '}
                  <Text strong>
                    {activeDelegation.delegated_to?.full_name || `ID ${activeDelegation.delegated_to_id}`}
                  </Text>
                </span>
                <span>
                  Период:{' '}
                  <Text code>
                    {dayjs(activeDelegation.start_date).format('DD.MM.YYYY')} –{' '}
                    {dayjs(activeDelegation.end_date).format('DD.MM.YYYY')}
                  </Text>
                </span>
              </Space>
            }
            action={
              <Space direction="vertical" size={4}>
                <Popconfirm
                  title="Рекрутер вернулся?"
                  description="Досрочно завершить делегирование в связи с возвратом рекрутера?"
                  okText="Да, вернулся"
                  cancelText="Отмена"
                  onConfirm={handleRevoke}
                >
                  <Button size="small" icon={<CloseCircleOutlined />} loading={revoking}>
                    Вернулся из отпуска
                  </Button>
                </Popconfirm>
                <Popconfirm
                  title="Отозвать делегирование?"
                  description="Временный рекрутер потеряет доступ немедленно."
                  okText="Отозвать"
                  cancelText="Отмена"
                  okButtonProps={{ danger: true }}
                  onConfirm={handleRevoke}
                >
                  <Button size="small" danger icon={<CloseCircleOutlined />} loading={revoking}>
                    Отозвать доступ
                  </Button>
                </Popconfirm>
              </Space>
            }
          />
          <Divider orientation="left" plain style={{ fontSize: 12 }}>
            Создать новое делегирование (заменит текущее)
          </Divider>
        </>
      )}

      <Form form={form} layout="vertical">
        <Form.Item
          name="delegated_to_id"
          label="Временный рекрутер"
          rules={[{ required: true, message: 'Выберите рекрутера' }]}
        >
          <Select
            placeholder="Выберите рекрутера..."
            options={recruiterOptions}
            showSearch
            filterOption={(input, opt) =>
              (opt?.label ?? '').toLowerCase().includes(input.toLowerCase())
            }
            getPopupContainer={() => document.body}
          />
        </Form.Item>

        <Form.Item
          name="period"
          label="Период делегирования"
          rules={[{ required: true, message: 'Укажите период' }]}
        >
          <RangePicker
            style={{ width: '100%' }}
            format="DD.MM.YYYY"
            disabledDate={(d) => d && d < dayjs().startOf('day')}
            getPopupContainer={() => document.body}
          />
        </Form.Item>

        <Form.Item style={{ marginBottom: 0 }}>
          <Space style={{ width: '100%', justifyContent: 'flex-end' }}>
            <Button onClick={onClose}>Отмена</Button>
            <Button
              type="primary"
              icon={<UserSwitchOutlined />}
              loading={loading}
              onClick={handleSubmit}
            >
              Делегировать
            </Button>
          </Space>
        </Form.Item>
      </Form>
    </Modal>
  );
};

export default DelegationModal;
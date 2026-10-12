

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  Modal, Form, Select, DatePicker, Button, Space, Alert,
  Tag, Divider, Popconfirm, Typography, message, Table,
} from 'antd';
import { UserSwitchOutlined, CloseCircleOutlined, HistoryOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { api } from '../App';

const { RangePicker } = DatePicker;
const { Text } = Typography;

const DelegationModal = ({ open, vacancy, users, onClose, onSuccess }) => {
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);
  const [revoking, setRevoking] = useState(false);
  const [historyList, setHistoryList] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  const activeDelegation = vacancy?.delegation;

  const loadHistory = useCallback(async () => {
    if (!vacancy?.id) return;
    setHistoryLoading(true);
    try {
      const res = await api.get(`/vacancies/${vacancy.id}/delegations`);
      setHistoryList(res.data || []);
    } catch (err) {
      console.error('Failed to load delegation history', err);
    } finally {
      setHistoryLoading(false);
    }
  }, [vacancy?.id]);

  useEffect(() => {
    if (open) {
      form.resetFields();
      loadHistory();
    } else {
      setHistoryList([]);
    }
  }, [open, form, loadHistory]);

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
      await loadHistory();
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
      await loadHistory();
      onSuccess?.();
      onClose();
    } catch (err) {
      const detail = err.response?.data?.detail || 'Ошибка при отзыве делегирования';
      message.error(detail);
    } finally {
      setRevoking(false);
    }
  };

  const historyColumns = [
    {
      title: 'Временный рекрутер',
      key: 'delegated_to',
      render: (_, r) => r.delegated_to?.full_name || `ID ${r.delegated_to_id}`,
    },
    {
      title: 'Период',
      key: 'period',
      render: (_, r) => (
        <span style={{ fontSize: 12 }}>
          {dayjs(r.start_date).format('DD.MM.YYYY')} – {dayjs(r.end_date).format('DD.MM.YYYY')}
        </span>
      ),
    },
    {
      title: 'Статус',
      key: 'is_active',
      align: 'center',
      width: 100,
      render: (_, r) =>
        r.is_active ? (
          <Tag color="success">Активно</Tag>
        ) : (
          <Tag color="default">Завершено</Tag>
        ),
    },
  ];

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
      width={560}
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

      <Divider orientation="left" plain style={{ fontSize: 13, marginTop: 24, marginBottom: 12 }}>
        <Space size={4}>
          <HistoryOutlined />
          <span>История делегирований</span>
        </Space>
      </Divider>
      <Table
        size="small"
        rowKey="id"
        columns={historyColumns}
        dataSource={historyList}
        loading={historyLoading}
        pagination={false}
        locale={{ emptyText: 'Нет истории делегирований' }}
      />
    </Modal>
  );
};

export default DelegationModal;
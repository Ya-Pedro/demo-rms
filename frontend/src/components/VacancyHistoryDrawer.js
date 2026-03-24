

import React, { useState, useEffect, useCallback } from 'react';
import {
  Drawer, Tag, Space, DatePicker, Spin,
  Empty, Typography, Button, Tooltip, Collapse,
} from 'antd';
import {
  EditOutlined, PlusCircleOutlined, DeleteOutlined,
  UserOutlined, ClockCircleOutlined, ReloadOutlined,
  UserSwitchOutlined, FileTextOutlined, UserDeleteOutlined,
  RightOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import { api } from '../App';

dayjs.locale('ru');

const { RangePicker } = DatePicker;
const { Text } = Typography;
const { Panel } = Collapse;

const ACTION_CONFIG = {
  CREATE:     { color: '#52c41a', icon: <PlusCircleOutlined />,  label: 'Создание',           tagColor: 'success'    },
  UPDATE:     { color: '#1677ff', icon: <EditOutlined />,         label: 'Изменение',          tagColor: 'processing' },
  DELETE:     { color: '#ff4d4f', icon: <DeleteOutlined />,       label: 'Удаление',           tagColor: 'error'      },
  DELEGATE:   { color: '#fa8c16', icon: <UserSwitchOutlined />,   label: 'Делегирование',      tagColor: 'warning'    },
  UNDELEGATE: { color: '#722ed1', icon: <UserDeleteOutlined />,   label: 'Отзыв делегирования',tagColor: 'purple'     },
  REPORT:     { color: '#13c2c2', icon: <FileTextOutlined />,     label: 'Отчёт',              tagColor: 'cyan'       },
};
const getCfg = (t) => ACTION_CONFIG[t] || ACTION_CONFIG.UPDATE;

const DiffRow = ({ fieldName, change }) => {
  const empty = (v) => !v || v === '—';
  return (
    <div style={{
      display: 'flex', alignItems: 'baseline', gap: 6,
      padding: '3px 0', borderBottom: '1px solid #f5f5f5', fontSize: 12,
    }}>
      <Text type="secondary" style={{ minWidth: 150, flexShrink: 0, fontSize: 11 }}>
        {fieldName}
      </Text>
      {empty(change.old)
        ? <Text type="secondary" style={{ fontStyle: 'italic', fontSize: 11 }}>пусто</Text>
        : <span style={{ background: '#fff1f0', color: '#cf1322', padding: '0 5px', borderRadius: 3, textDecoration: 'line-through' }}>{change.old}</span>
      }
      <Text type="secondary">→</Text>
      {empty(change.new)
        ? <Text type="secondary" style={{ fontStyle: 'italic', fontSize: 11 }}>очищено</Text>
        : <span style={{ background: '#f6ffed', color: '#389e0d', padding: '0 5px', borderRadius: 3 }}>{change.new}</span>
      }
    </div>
  );
};

const HistoryItem = ({ record }) => {
  const cfg = getCfg(record.action_type);
  const entries = Object.entries(record.changes || {});
  const user = record.user;
  const userName = user?.full_name || 'Система';
  const roleLabel = user?.role_label ? ` (${user.role_label})` : '';
  const time = dayjs(record.created_at).format('DD.MM.YYYY HH:mm');

  const header = (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      width: '100%', minWidth: 0, lineHeight: '20px',
    }}>
      <Tag
        color={cfg.tagColor}
        style={{ margin: 0, flexShrink: 0, fontSize: 11, padding: '0 5px', lineHeight: '18px' }}
      >
        {cfg.icon}&nbsp;{cfg.label}
      </Tag>

      <Text style={{ fontSize: 12, flexShrink: 0 }}>
        <UserOutlined style={{ marginRight: 3, color: '#8c8c8c' }} />
        {userName}<Text type="secondary">{roleLabel}</Text>
      </Text>

      <div style={{ flex: 1 }} />

      <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
        <ClockCircleOutlined style={{ marginRight: 3 }} />{time}
      </Text>

      {entries.length > 0 && (
        <Text type="secondary" style={{ fontSize: 11, flexShrink: 0 }}>
          {entries.length} {entries.length === 1 ? 'поле' : entries.length < 5 ? 'поля' : 'полей'}
        </Text>
      )}
    </div>
  );

  if (entries.length === 0) {
    return (
      <div style={{
        padding: '5px 8px',
        borderLeft: `3px solid ${cfg.color}`,
        borderRadius: 4,
        background: '#fafafa',
        marginBottom: 2,
      }}>
        {header}
      </div>
    );
  }

  return (
    <Collapse
      ghost
      size="small"
      expandIcon={({ isActive }) => (
        <RightOutlined style={{ fontSize: 10, color: '#8c8c8c', transform: isActive ? 'rotate(90deg)' : 'none', transition: 'transform .2s' }} />
      )}
      style={{ marginBottom: 2 }}
    >
      <Panel
        key="1"
        header={header}
        style={{
          borderLeft: `3px solid ${cfg.color}`,
          borderRadius: '4px !important',
          background: '#fafafa',
          padding: 0,
        }}
      >
        <div style={{ padding: '4px 0 0 0' }}>
          {}
          {['UPDATE', 'CREATE'].includes(record.action_type) && (
            <div style={{ display: 'flex', gap: 6, marginBottom: 3, fontSize: 10, color: '#8c8c8c', fontWeight: 600 }}>
              <span style={{ minWidth: 150 }}>Поле</span>
              <span style={{ flex: 1 }}>Было</span>
              <span style={{ width: 14 }} />
              <span style={{ flex: 1 }}>Стало</span>
            </div>
          )}
          {entries.map(([field, change]) => (
            <DiffRow key={field} fieldName={field} change={change} />
          ))}
        </div>
      </Panel>
    </Collapse>
  );
};

const VacancyHistoryDrawer = ({ open, vacancy, onClose }) => {
  const [records, setRecords]     = useState([]);
  const [loading, setLoading]     = useState(false);
  const [dateRange, setDateRange] = useState(null);

  const fetchHistory = useCallback(async (range) => {
    if (!vacancy?.id) return;
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (range?.[0]) params.append('start_date', range[0].format('YYYY-MM-DD'));
      if (range?.[1]) params.append('end_date',   range[1].format('YYYY-MM-DD'));
      const res = await api.get(`/vacancies/${vacancy.id}/history?${params}`);
      setRecords(res.data || []);
    } catch (e) {
      console.error('History fetch error', e);
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }, [vacancy?.id]);

  useEffect(() => {
    if (open && vacancy?.id) { setDateRange(null); fetchHistory(null); }
    if (!open) setRecords([]);
  }, [open, vacancy?.id]);

  const handleRange = (range) => { setDateRange(range); fetchHistory(range); };

  const grouped = records.reduce((acc, r) => {
    const day = dayjs(r.created_at).format('D MMMM YYYY');
    (acc[day] = acc[day] || []).push(r);
    return acc;
  }, {});

  return (
    <Drawer
      title={
        <Space>
          <ClockCircleOutlined style={{ color: '#1677ff' }} />
          <span>История изменений</span>
          {vacancy && (
            <Text type="secondary" style={{ fontSize: 13, fontWeight: 400 }}>
              — {vacancy.position_name}{vacancy.vacancy_id ? ` (${vacancy.vacancy_id})` : ''}
            </Text>
          )}
        </Space>
      }
      open={open}
      onClose={onClose}
      width={620}
      destroyOnClose
      extra={
        <Tooltip title="Обновить">
          <Button icon={<ReloadOutlined />} size="small" loading={loading}
            onClick={() => fetchHistory(dateRange)} />
        </Tooltip>
      }
    >
      {}
      <div style={{
        marginBottom: 14, padding: '8px 12px',
        background: '#fafafa', borderRadius: 6, border: '1px solid #f0f0f0',
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <Text type="secondary" style={{ fontSize: 12 }}>Период:</Text>
        <RangePicker
          value={dateRange} onChange={handleRange}
          format="DD.MM.YYYY" placeholder={['Начало', 'Конец']}
          getPopupContainer={() => document.body} allowClear size="small"
        />
        {dateRange && <Button size="small" onClick={() => handleRange(null)}>Сбросить</Button>}
        {!loading && records.length > 0 && (
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
            {records.length} {records.length === 1 ? 'запись' : records.length < 5 ? 'записи' : 'записей'}
          </Text>
        )}
      </div>

      {}
      {!loading && records.length > 0 && (
        <div style={{ marginBottom: 10, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
          {Object.entries(records.reduce((a, r) => { a[r.action_type] = (a[r.action_type] || 0) + 1; return a; }, {}))
            .map(([type, cnt]) => {
              const cfg = getCfg(type);
              return (
                <Tag key={type} color={cfg.tagColor} style={{ margin: 0, fontSize: 11 }}>
                  {cfg.icon}&nbsp;{cfg.label}: {cnt}
                </Tag>
              );
            })}
        </div>
      )}

      {}
      <Spin spinning={loading}>
        {!loading && records.length === 0 ? (
          <Empty
            description={dateRange ? 'Нет событий за период' : 'История пуста'}
            style={{ marginTop: 40 }}
          />
        ) : (
          <div>
            {Object.entries(grouped).map(([day, items]) => (
              <div key={day}>
                <div style={{
                  fontSize: 11, fontWeight: 600, color: '#8c8c8c',
                  padding: '6px 0 4px', letterSpacing: 0.3,
                  borderBottom: '1px solid #f0f0f0', marginBottom: 4,
                }}>
                  {day}
                </div>
                {items.map((r) => <HistoryItem key={r.id} record={r} />)}
              </div>
            ))}
          </div>
        )}
      </Spin>
    </Drawer>
  );
};

export default VacancyHistoryDrawer;
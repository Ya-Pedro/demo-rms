

import React, { useState, useEffect, useCallback } from 'react';
import {
  Drawer, Tag, Space, DatePicker, Spin,
  Empty, Typography, Button, Tooltip, Collapse, theme, Tabs, Badge,
} from 'antd';
import {
  EditOutlined, PlusCircleOutlined, DeleteOutlined,
  UserOutlined, ClockCircleOutlined, ReloadOutlined,
  UserSwitchOutlined, FileTextOutlined, UserDeleteOutlined,
  RightOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import 'dayjs/locale/ru';
import { api } from '../App';
import useIsMobile from '../hooks/useIsMobile';

dayjs.extend(isoWeek);
dayjs.locale('ru');

const { RangePicker } = DatePicker;
const { Text } = Typography;
const { Panel } = Collapse;

const ACTION_CONFIG = {
  CREATE:          { color: '#52c41a', icon: <PlusCircleOutlined />,   label: 'Создание',                  tagColor: 'success'    },
  UPDATE:          { color: '#1677ff', icon: <EditOutlined />,          label: 'Изменение',                 tagColor: 'processing' },
  DELETE:          { color: '#ff4d4f', icon: <DeleteOutlined />,        label: 'Удаление',                  tagColor: 'error'      },
  DELEGATE:        { color: '#fa8c16', icon: <UserSwitchOutlined />,    label: 'Делегирование',             tagColor: 'warning'    },
  UNDELEGATE:      { color: '#722ed1', icon: <UserDeleteOutlined />,    label: 'Отзыв делегирования',       tagColor: 'purple'     },
  REPORT:          { color: '#13c2c2', icon: <FileTextOutlined />,      label: 'Отчёт',                     tagColor: 'cyan'       },
  OFFER_REJECTION: { color: '#fa541c', icon: <CloseCircleOutlined />,  label: 'Причина отказа от оффера',  tagColor: 'volcano'    },
};
const getCfg = (t) => ACTION_CONFIG[t] || ACTION_CONFIG.UPDATE;

const DiffRow = ({ fieldName, change, isMobile }) => {
  const { token } = theme.useToken();
  const empty = (v) => !v || v === '—';
  const gridCols = isMobile ? '120px minmax(0, 1fr) 24px minmax(0, 1fr)' : '190px minmax(0, 1fr) 32px minmax(0, 1fr)';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: gridCols,
      gap: 12,
      alignItems: 'flex-start',
      padding: '6px 0',
      borderBottom: `1px solid ${token.colorBorderSecondary}`,
      fontSize: 13,
    }}>
      <Text type="secondary" style={{ fontSize: 13, paddingTop: 1, wordBreak: 'break-word', color: token.colorTextSecondary }}>
        {fieldName}
      </Text>
      <div style={{ minWidth: 0, wordBreak: 'break-word', fontSize: 13 }}>
        {empty(change.old)
          ? <Text type="secondary" style={{ fontStyle: 'italic', fontSize: 13 }}>пусто</Text>
          : <span style={{ background: token.colorErrorBg, color: token.colorError, padding: '2px 7px', borderRadius: 4, textDecoration: 'line-through', wordBreak: 'break-word', whiteSpace: 'pre-wrap', display: 'inline-block', fontSize: 13 }}>{change.old}</span>
        }
      </div>
      <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'flex-start', paddingTop: 1, color: token.colorTextSecondary, fontSize: 15, userSelect: 'none' }}>
        →
      </div>
      <div style={{ minWidth: 0, wordBreak: 'break-word', fontSize: 13 }}>
        {empty(change.new)
          ? <Text type="secondary" style={{ fontStyle: 'italic', fontSize: 13 }}>очищено</Text>
          : <span style={{ background: token.colorSuccessBg, color: token.colorSuccess, padding: '2px 7px', borderRadius: 4, wordBreak: 'break-word', whiteSpace: 'pre-wrap', display: 'inline-block', fontSize: 13 }}>{change.new}</span>
        }
      </div>
    </div>
  );
};

const HistoryItem = ({ record }) => {
  const { token } = theme.useToken();
  const isMobile = useIsMobile();
  const cfg = getCfg(record.action_type);
  const entries = Object.entries(record.changes || {});
  const user = record.user;
  const userName = user?.full_name || 'Система';
  const roleLabel = user?.role_label ? ` (${user.role_label})` : '';
  const createdDate = dayjs(record.created_at);
  const time = createdDate.format('DD.MM.YYYY HH:mm');
  const weekNum = createdDate.isoWeek();
  const gridCols = isMobile ? '120px minmax(0, 1fr) 24px minmax(0, 1fr)' : '190px minmax(0, 1fr) 32px minmax(0, 1fr)';

  const header = (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      width: '100%', minWidth: 0, lineHeight: '22px',
    }}>
      <Tag
        color={cfg.tagColor}
        style={{ margin: 0, flexShrink: 0, fontSize: 12, padding: '1px 6px', lineHeight: '20px' }}
      >
        {cfg.icon}&nbsp;{cfg.label}
      </Tag>

      <Text style={{ fontSize: 13, flexShrink: 0, fontWeight: 500 }}>
        <UserOutlined style={{ marginRight: 4, color: token.colorTextSecondary }} />
        {userName}<Text type="secondary" style={{ fontSize: 12 }}>{roleLabel}</Text>
      </Text>

      <div style={{ flex: 1 }} />

      <Tag
        color="default"
        style={{ margin: 0, flexShrink: 0, fontSize: 12, padding: '1px 6px', lineHeight: '20px' }}
      >
        Неделя {weekNum}
      </Tag>

      <Text type="secondary" style={{ fontSize: 12, flexShrink: 0 }}>
        <ClockCircleOutlined style={{ marginRight: 4 }} />{time}
      </Text>

      {entries.length > 0 && (
        <Text type="secondary" style={{ fontSize: 12, flexShrink: 0 }}>
          {entries.length} {entries.length === 1 ? 'поле' : entries.length < 5 ? 'поля' : 'полей'}
        </Text>
      )}
    </div>
  );

  if (entries.length === 0) {
    return (
      <div style={{
        padding: '6px 10px',
        borderLeft: `3px solid ${cfg.color}`,
        borderRadius: 4,
        background: token.colorFillAlter,
        marginBottom: 3,
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
        <RightOutlined style={{ fontSize: 11, color: token.colorTextSecondary, transform: isActive ? 'rotate(90deg)' : 'none', transition: 'transform .2s' }} />
      )}
      style={{ marginBottom: 3 }}
    >
      <Panel
        key="1"
        header={header}
        style={{
          borderLeft: `3px solid ${cfg.color}`,
          borderRadius: '4px !important',
          background: token.colorFillAlter,
          padding: 0,
        }}
      >
        <div style={{ padding: '4px 8px 6px 8px' }}>
          {entries.length > 0 && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: gridCols,
              gap: 12,
              alignItems: 'center',
              padding: '6px 0',
              marginBottom: 4,
              borderBottom: `1px solid ${token.colorBorderSecondary}`,
              fontSize: 12,
              color: token.colorTextSecondary,
              fontWeight: 600,
            }}>
              <span>Поле</span>
              <span>Было</span>
              <span style={{ textAlign: 'center', userSelect: 'none' }}>→</span>
              <span>Стало</span>
            </div>
          )}
          {entries.map(([field, change]) => (
            <DiffRow key={field} fieldName={field} change={change} isMobile={isMobile} />
          ))}
        </div>
      </Panel>
    </Collapse>
  );
};

const VacancyHistoryDrawer = ({ vacancy, open, onClose }) => {
  const { token } = theme.useToken();
  const isMobile = useIsMobile();
  const [records, setRecords] = useState([]);
  const [loading, setLoading] = useState(false);
  const [dateRange, setDateRange] = useState(null);

  const fetchHistory = useCallback(async (range) => {
    if (!vacancy?.id) return;
    setLoading(true);
    try {
      const sp = new URLSearchParams();
      if (range && range[0] && range[1]) {
        sp.append('start_date', range[0].format('YYYY-MM-DD'));
        sp.append('end_date', range[1].format('YYYY-MM-DD'));
      }
      const res = await api.get(`/vacancies/${vacancy.id}/history?${sp.toString()}`);
      setRecords(res.data || []);
    } catch (error) {
      console.error('Failed to load history', error);
      setRecords([]);
    } finally {
      setLoading(false);
    }
  }, [vacancy?.id]);

  useEffect(() => {
    if (open && vacancy?.id) { setDateRange(null); fetchHistory(null); }
    if (!open) {
      setRecords([]);
      setActiveTab('ALL');
    }
  }, [open, vacancy?.id, fetchHistory]);

  const handleRange = (range) => { setDateRange(range); fetchHistory(range); };

  const [activeTab, setActiveTab] = useState('ALL');

  const isOfferRejectionRecord = (r) => {
    if (r.action_type === 'OFFER_REJECTION') return true;
    if (r.changes) {
      const keys = Object.keys(r.changes);
      return keys.some(k => k.toLowerCase().includes('причина отказа') || k.toLowerCase().includes('rejection'));
    }
    return false;
  };

  const getFilteredRecords = (tab) => {
    if (tab === 'ALL') return records;
    if (tab === 'OFFER_REJECTION') return records.filter(isOfferRejectionRecord);
    if (tab === 'UPDATE') return records.filter(r => r.action_type === 'UPDATE' && !isOfferRejectionRecord(r));
    if (tab === 'REPORT') return records.filter(r => r.action_type === 'REPORT');
    if (tab === 'CREATE') return records.filter(r => r.action_type === 'CREATE');
    return records.filter(r => r.action_type === tab);
  };

  const filteredRecords = getFilteredRecords(activeTab);

  const countAll = records.length;
  const countUpdate = records.filter(r => r.action_type === 'UPDATE' && !isOfferRejectionRecord(r)).length;
  const countReport = records.filter(r => r.action_type === 'REPORT').length;
  const countCreate = records.filter(r => r.action_type === 'CREATE').length;
  const countRejection = records.filter(isOfferRejectionRecord).length;

  const tabItems = [
    {
      key: 'ALL',
      label: (
        <span>Все {countAll > 0 && <Tag style={{ marginLeft: 4, borderRadius: 10, fontSize: 11 }}>{countAll}</Tag>}</span>
      ),
    },
    {
      key: 'UPDATE',
      label: (
        <span><EditOutlined /> Изменение {countUpdate > 0 && <Tag color="processing" style={{ marginLeft: 4, borderRadius: 10, fontSize: 11 }}>{countUpdate}</Tag>}</span>
      ),
    },
    {
      key: 'REPORT',
      label: (
        <span><FileTextOutlined /> Отчёт {countReport > 0 && <Tag color="cyan" style={{ marginLeft: 4, borderRadius: 10, fontSize: 11 }}>{countReport}</Tag>}</span>
      ),
    },
    {
      key: 'CREATE',
      label: (
        <span><PlusCircleOutlined /> Создание {countCreate > 0 && <Tag color="success" style={{ marginLeft: 4, borderRadius: 10, fontSize: 11 }}>{countCreate}</Tag>}</span>
      ),
    },
    {
      key: 'OFFER_REJECTION',
      label: (
        <span><CloseCircleOutlined /> Причина отказа от оффера {countRejection > 0 && <Tag color="volcano" style={{ marginLeft: 4, borderRadius: 10, fontSize: 11 }}>{countRejection}</Tag>}</span>
      ),
    },
  ];

  const grouped = filteredRecords.reduce((acc, r) => {
    const day = dayjs(r.created_at).format('D MMMM YYYY');
    (acc[day] = acc[day] || []).push(r);
    return acc;
  }, {});

  const getEmptyDesc = () => {
    if (dateRange) return 'Нет событий за выбранный период';
    if (activeTab === 'OFFER_REJECTION') return 'Причины отказа от оффера не зафиксированы';
    if (activeTab === 'REPORT') return 'Отчётов по вакансии пока нет';
    if (activeTab === 'UPDATE') return 'Изменений вакансии пока нет';
    if (activeTab === 'CREATE') return 'Событие создания не найдено';
    return 'История пуста';
  };

  return (
    <Drawer
      title={
        <Space>
          <ClockCircleOutlined style={{ color: token.colorPrimary }} />
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
      width={isMobile ? '100%' : 900}
      destroyOnClose
      extra={
        <Tooltip title="Обновить">
          <Button icon={<ReloadOutlined />} size="small" loading={loading}
            onClick={() => fetchHistory(dateRange)} />
        </Tooltip>
      }
    >
      <div style={{
        marginBottom: 12, padding: '8px 12px',
        background: token.colorFillAlter, borderRadius: 6, border: `1px solid ${token.colorBorderSecondary}`,
        display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      }}>
        <Text type="secondary" style={{ fontSize: 12 }}>Период:</Text>
        <RangePicker
          value={dateRange} onChange={handleRange}
          format="DD.MM.YYYY" placeholder={['Начало', 'Конец']}
          getPopupContainer={() => document.body} allowClear size="small"
        />
        {dateRange && <Button size="small" onClick={() => handleRange(null)}>Сбросить</Button>}
        {!loading && filteredRecords.length > 0 && (
          <Text type="secondary" style={{ fontSize: 12, marginLeft: 'auto' }}>
            {filteredRecords.length} {filteredRecords.length === 1 ? 'запись' : filteredRecords.length < 5 ? 'записи' : 'записей'}
          </Text>
        )}
      </div>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={tabItems}
        size="small"
        style={{ marginBottom: 12 }}
      />

      <Spin spinning={loading}>
        {!loading && filteredRecords.length === 0 ? (
          <Empty
            description={getEmptyDesc()}
            style={{ marginTop: 40 }}
          />
        ) : (
          <div>
            {Object.entries(grouped).map(([day, items]) => (
              <div key={day}>
                <div style={{
                  fontSize: 13, fontWeight: 600, color: token.colorTextSecondary,
                  padding: '8px 0 4px', letterSpacing: 0.3,
                  borderBottom: `1px solid ${token.colorBorderSecondary}`, marginBottom: 6,
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
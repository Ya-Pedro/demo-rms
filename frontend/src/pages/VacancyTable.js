/**
 * VacancyTable.js — оптимизированная версия v2 (патч 3 багов)
 *
 * ─── ИСПРАВЛЕНИЯ ОТНОСИТЕЛЬНО ОПТИМИЗИРОВАННОЙ ВЕРСИИ ────────────────────────
 *
 * БАГ 1 (columns useMemo): hideInSetting-колонки (№, Действия) не входили
 *   в columnOrder → при непустом columnOrder попадали в fallback-хвост → теряли
 *   позицию (больше не первые) и fixed:'left'.
 *   FIX: hideInSetting-колонки всегда вставляются ПЕРВЫМИ, до обхода columnOrder.
 *
 * БАГ 2 (openColumnSettings): читал fixed из rawColumns (не обновляется при
 *   изменении настроек) → шестерёнка показывала устаревший fixed, при повторном
 *   применении закрепление сбрасывалось.
 *   FIX: читаем из columns (уже с применёнными настройками).
 *
 * БАГ 3 (rawColumns useMemo deps): curPage и pageSize используются в рендере
 *   ячейки №, но отсутствовали в deps → нумерация не обновлялась при смене страницы.
 *   FIX: добавлены в deps.
 */

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import RecruiterTour from '../components/RecruiterTour';
import VacancyHistoryDrawer from '../components/VacancyHistoryDrawer';
import {
  Table, Button, Space, Tag, Tooltip,
  Input, message, Upload, Modal, Checkbox,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ClearOutlined, FileTextOutlined, DownloadOutlined, UploadOutlined,
  SettingOutlined, ArrowUpOutlined, ArrowDownOutlined, PushpinOutlined,
  ReloadOutlined, QuestionCircleOutlined, UserSwitchOutlined, HistoryOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { api } from '../App';

dayjs.extend(isoWeek);

import DelegationModal from '../components/DelegationModal';
import './VacancyTable.css';

const STORAGE_KEY_PREFIX = 'rms_table_settings_';
const DEFAULT_PAGE_SIZE  = 25;

const getStorageKey = (uid) => `${STORAGE_KEY_PREFIX}${uid || 'anonymous'}`;

const loadTableSettings = (uid) => {
  try {
    const s = localStorage.getItem(getStorageKey(uid));
    return s ? JSON.parse(s) : null;
  } catch { return null; }
};

const saveTableSettings = (uid, settings) => {
  try { localStorage.setItem(getStorageKey(uid), JSON.stringify(settings)); } catch {}
};

const getPopupContainer = () => document.body;

// Маппинг статуса вакансии → CSS-класс строки таблицы.
// Цвета применяются ко всей строке <tr> через rowClassName.
const STATUS_ROW_CLASS = {
  'Открыта':                  'vt-row--open',
  'Согласование фин условий': 'vt-row--beige',
  'Проверка СБ':              'vt-row--beige',
  'Проверка сб':              'vt-row--beige', // fallback на случай разного регистра
  'Оффер':                    'vt-row--light-green',
  'Подготовка документов':    'vt-row--light-green',
  'Выход':                    'vt-row--light-green',
  'Закрыта':                  'vt-row--green',
  'Hold':                     'vt-row--blue',
  'Отмена':                   'vt-row--red',
};

const getRowClassName = (record) =>
  STATUS_ROW_CLASS[record.status_name || record.status?.value] || '';

const WH = (text) => (
  <div style={{ whiteSpace: 'normal', lineHeight: '1.2', textAlign: 'center' }}>{text}</div>
);

const TEXT_FILTER_DROPDOWN = {
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <Input
        autoFocus
        placeholder="Поиск..."
        value={selectedKeys[0]}
        onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={() => confirm()}
        style={{ width: 188, marginBottom: 8, display: 'block' }}
      />
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: 90 }}>Найти</Button>
        <Button onClick={() => { clearFilters(); confirm(); }} size="small" style={{ width: 90 }}>Сброс</Button>
      </Space>
    </div>
  ),
  filterDropdownProps: { getPopupContainer },
};

const DATE_FILTER_DROPDOWN = {
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <Input
        autoFocus
        placeholder="дд.мм.гг"
        value={selectedKeys[0]}
        onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={() => confirm()}
        style={{ width: 150, marginBottom: 8, display: 'block' }}
      />
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: 70 }}>Найти</Button>
        <Button onClick={() => { clearFilters(); confirm(); }} size="small" style={{ width: 70 }}>Сброс</Button>
      </Space>
    </div>
  ),
  filterDropdownProps: { getPopupContainer },
};

const NUMBER_FILTER_DROPDOWN = {
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <Input
        autoFocus
        placeholder="Точное значение..."
        value={selectedKeys[0]}
        onChange={e => setSelectedKeys(e.target.value ? [e.target.value] : [])}
        onPressEnter={() => confirm()}
        style={{ width: 140, marginBottom: 8, display: 'block' }}
      />
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: 65 }}>Найти</Button>
        <Button onClick={() => { clearFilters(); confirm(); }} size="small" style={{ width: 65 }}>Сброс</Button>
      </Space>
    </div>
  ),
  filterDropdownProps: { getPopupContainer },
};

const TEXT_FILTER_KEYS = new Set([
  'vacancy_id', 'position_name', 'team_lead_text', 'city_text',
  'candidate_name', 'candidate_company', 'ex_employee_name', 'unit_id',
]);
const NUMBER_FILTER_KEYS = new Set([
  'quantity', 'resume_at_customer', 'resume_approved', 
  'interviews_fact', 'interviews_plan', 'offer_made', 
  'work_duration_days', 'salary_gross'
]);
const DATE_FILTER_KEYS = new Set(['open_date', 'close_date', 'status_changed_at']);

const PIN_LABEL = { left: 'Слева', none: 'Нет' };
const PIN_COLOR = { left: '#1890FF', none: undefined };


const ResizableHeaderCell = (props) => {
  const { onResize, width, ...restProps } = props;
  const [hovered, setHovered] = React.useState(false);

  if (!width) {
    return <th {...restProps} />;
  }

  const isSticky = restProps.style?.position === 'sticky' || (restProps.className && restProps.className.includes('ant-table-cell-fix-'));
  const cellStyle = {
    ...restProps.style,
  };
  if (!isSticky) {
    cellStyle.position = 'relative';
  }

  return (
    <th
      {...restProps}
      style={cellStyle}
    >
      {restProps.children}
      <div
        style={{
          position: 'absolute',
          right: 0,
          top: 0,
          width: 8,
          height: '100%',
          cursor: 'col-resize',
          zIndex: 10,
          transition: 'background 0.2s',
          background: hovered ? 'rgba(0, 80, 179, 0.3)' : 'transparent',
        }}
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={(e) => {
          e.stopPropagation();
        }}
        onMouseDown={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const startX = e.clientX;
          const startWidth = width;

          const handleMouseMove = (moveEvent) => {
            const newWidth = Math.min(800, Math.max(80, startWidth + (moveEvent.clientX - startX)));
            onResize(newWidth);
          };

          const handleMouseUp = () => {
            document.removeEventListener('mousemove', handleMouseMove);
            document.removeEventListener('mouseup', handleMouseUp);
          };

          document.addEventListener('mousemove', handleMouseMove);
          document.addEventListener('mouseup', handleMouseUp);
        }}
      />
    </th>
  );
};

const ColumnSettingsModal = React.memo(({ visible, onClose, onApply, localOrder, setLocalOrder, showReorder }) => {
  const moveUp = useCallback((idx) => {
    if (idx <= 0) return;
    setLocalOrder(prev => {
      const next = [...prev];
      [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
      return next;
    });
  }, [setLocalOrder]);

  const moveDown = useCallback((idx) => {
    setLocalOrder(prev => {
      if (idx >= prev.length - 1) return prev;
      const next = [...prev];
      [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
      return next;
    });
  }, [setLocalOrder]);

  const toggleShow = useCallback((idx) => {
    setLocalOrder(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], show: !next[idx].show };
      return next;
    });
  }, [setLocalOrder]);

  const cyclePin = useCallback((idx) => {
    setLocalOrder(prev => {
      const next = [...prev];
      const cur = next[idx].fixed || 'none';
      const pins = ['none', 'left'];
      next[idx] = { ...next[idx], fixed: pins[(pins.indexOf(cur) + 1) % pins.length] };
      return next;
    });
  }, [setLocalOrder]);

  return (
    <Modal
      title="Настройка столбцов"
      open={visible}
      onCancel={onClose}
      onOk={onApply}
      okText="Применить"
      cancelText="Отмена"
      width={480}
      data-testid="columns-settings-modal"
      destroyOnClose
    >
      <div style={{ maxHeight: 450, overflowY: 'auto' }}>
        {localOrder.map((item, idx) => {
          const pinned = item.fixed && item.fixed !== 'none';
          return (
            <div
              key={item.key}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 4px', borderBottom: '1px solid #f0f0f0',
                background: pinned ? '#f6ffed' : undefined,
              }}
            >
              <Checkbox checked={item.show !== false} onChange={() => toggleShow(idx)} />
              <span style={{
                flex: 1, whiteSpace: 'normal', lineHeight: '1.2', fontSize: 13,
                fontWeight: pinned ? 500 : 400,
                color: pinned ? PIN_COLOR[item.fixed] : undefined,
              }}>
                {item.label}
              </span>
              {showReorder && (
                <>
                  <Tooltip title="Вверх">
                    <Button type="text" size="small" icon={<ArrowUpOutlined />}
                      disabled={idx === 0} onClick={() => moveUp(idx)} />
                  </Tooltip>
                  <Tooltip title="Вниз">
                    <Button type="text" size="small" icon={<ArrowDownOutlined />}
                      disabled={idx === localOrder.length - 1} onClick={() => moveDown(idx)} />
                  </Tooltip>
                </>
              )}
              <Tooltip title={`Закрепить (${PIN_LABEL[item.fixed || 'none']})`}>
                <Button type="text" size="small" icon={<PushpinOutlined />}
                  onClick={() => cyclePin(idx)}
                  style={{ color: PIN_COLOR[item.fixed || 'none'], fontWeight: pinned ? 700 : 400 }} />
              </Tooltip>
              {pinned && (
                <Tag color={item.fixed === 'left' ? 'blue' : 'orange'} style={{ fontSize: 10, margin: 0 }}>
                  {PIN_LABEL[item.fixed]}
                </Tag>
              )}
            </div>
          );
        })}
      </div>
    </Modal>
  );
});


const VacancyTable = ({
  actionRef,
  tableKey,
  dictionaries,
  users,
  user,
  onEdit,
  onDelete,
  onCreate,
  onReportClick,
  onExportClick,
  onTableStateChange,
  onResetRequest,
  onTourComplete,
  excludeStatusIds = [],
}) => {
  const userId       = user?.id;
  const isSuperAdmin = user?.role === 'superadmin';
  const isAdmin      = user?.role === 'admin' || user?.role === 'superadmin';

  // Делегирование вакансий
  const [delegationModal, setDelegationModal] = useState({ open: false, vacancy: null });
  const openDelegationModal = useCallback((record) => setDelegationModal({ open: true, vacancy: record }), []);
  const closeDelegationModal = useCallback(() => setDelegationModal({ open: false, vacancy: null }), []);

  const [data,         setData]         = useState([]);
  const [total,        setTotal]        = useState(0);
  const [loading,      setLoading]      = useState(false);
  const [curPage,      setCurPage]      = useState(1);

  // Lazy initial state — читаем localStorage синхронно при первом рендере.
  // Устраняет «прыжок»: таблица сразу стартует с сохранёнными настройками
  // и делает только один правильный запрос, а не два (дефолт → сохранённый).
  const [pageSize, setPageSize] = useState(() => {
    const saved = loadTableSettings(userId);
    return saved?.pageSize || DEFAULT_PAGE_SIZE;
  });
  const [sortedInfo, setSortedInfo] = useState(() => {
    const saved = loadTableSettings(userId);
    return saved?.sortedInfo || {};
  });
  const [columnsStateMap, setColumnsStateMap] = useState(() => {
    const saved = loadTableSettings(userId);
    return saved?.columnsStateMap || {};
  });
  const [columnOrder, setColumnOrder] = useState(() => {
    const saved = loadTableSettings(userId);
    return saved?.columnOrder || null;
  });

  const [filteredInfo, setFilteredInfo] = useState({});

  // Инициализируем ref тем же значением, что и sortedInfo,
  // чтобы первый fetchData сразу получил правильную сортировку.
  const sortedInfoRef = useRef((() => {
    const saved = loadTableSettings(userId);
    return saved?.sortedInfo || {};
  })());

  const [colModalVisible,    setColModalVisible]    = useState(false);
  const [colModalLocalOrder, setColModalLocalOrder] = useState([]);
  const tourRef = useRef();
  const [historyDrawer, setHistoryDrawer] = useState({ open: false, vacancy: null });
  const openHistoryDrawer  = useCallback((record) => setHistoryDrawer({ open: true,  vacancy: record }), []);
  const closeHistoryDrawer = useCallback(() => setHistoryDrawer({ open: false, vacancy: null }), []);

  const [importOpen,    setImportOpen]    = useState(false);
  const [importFile,    setImportFile]    = useState(null);
  const [importLoading, setImportLoading] = useState(false);
  const [importResult,  setImportResult]  = useState(null);

  const saveTimeoutRef  = useRef(null);
  const containerRef    = useRef(null);

  const debouncedSave = useCallback((settings) => {
    if (saveTimeoutRef.current) clearTimeout(saveTimeoutRef.current);
    saveTimeoutRef.current = setTimeout(() => {
      if (userId) saveTableSettings(userId, settings);
    }, 500);
  }, [userId]);

  useEffect(() => {
    if (userId)
      debouncedSave({ columnsStateMap, sortedInfo, pageSize, columnOrder });
  }, [columnsStateMap, sortedInfo, pageSize, columnOrder, debouncedSave, userId]);

  useEffect(() => {
    if (onTableStateChange) onTableStateChange({ filters: filteredInfo, sorter: sortedInfo });
  }, [filteredInfo, sortedInfo, onTableStateChange]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    let off = () => {};
    const timer = setTimeout(() => {
      const body = el.querySelector('.ant-table-body');
      if (!body) return;
      const close = () => document.body.dispatchEvent(new MouseEvent('mousedown', { bubbles: true }));
      body.addEventListener('scroll', close);
      off = () => body.removeEventListener('scroll', close);
    }, 100);
    return () => { clearTimeout(timer); off(); };
  }, [tableKey]);

  const fetchData = useCallback(async ({
    page   = curPage,
    ps     = pageSize,
    si     = sortedInfoRef.current,
    filter = filteredInfo,
  } = {}) => {
    console.log("DEBUG VacancyTable fetchData:", {
      excludeStatusIds,
      excludeStatusIds_len: excludeStatusIds ? excludeStatusIds.length : 0
    });
    setLoading(true);
    try {
      const sp = new URLSearchParams();
      sp.append('skip',  String((page - 1) * ps));
      sp.append('limit', String(ps));

      const sorters = Array.isArray(si) ? si : (si?.field || si?.columnKey ? [si] : []);
      const sf = sorters.map(s => s.field || s.columnKey).filter(Boolean);
      const so = sorters.map(s => s.order === 'ascend' ? 'asc' : 'desc');
      if (sf.length > 0) {
        sp.append('sort_field', sf.join(','));
        sp.append('sort_order', so.join(','));
      }

      sp.append('week_number', String(dayjs().isoWeek()));
      sp.append('year',        String(dayjs().year()));

      if (excludeStatusIds && excludeStatusIds.length > 0) {
        excludeStatusIds.forEach(id => sp.append('exclude_status_id', String(id)));
      }

      for (const [key, values] of Object.entries(filter || {})) {
        if (!values || values.length === 0) continue;
        if (TEXT_FILTER_KEYS.has(key) || DATE_FILTER_KEYS.has(key) || NUMBER_FILTER_KEYS.has(key)) {
          const val = Array.isArray(values) ? values[0] : values;
          if (val != null && val !== '') sp.append(`search_${key}`, String(val));
        } else {
          if (!Array.isArray(values)) continue;
          values.forEach(v => sp.append(key, String(v)));
        }
      }

      const res = await api.get(`/vacancies?${sp.toString()}`);
      setData(res.data.items  || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      console.error('Failed to fetch vacancies:', err);
      message.error('Ошибка загрузки данных');
    } finally {
      setLoading(false);
    }
  }, [curPage, pageSize, filteredInfo, (excludeStatusIds || []).join(',')]);

  useEffect(() => {
    fetchData();
  }, [tableKey, (excludeStatusIds || []).join(',')]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (actionRef && typeof actionRef === 'object') {
      actionRef.current = { reload: () => fetchData() };
    }
  }, [actionRef, fetchData]);

  const handleTableChange = useCallback((pagination, filters, sorter) => {
    const newPage = pagination.current  || 1;
    const newPs   = pagination.pageSize || pageSize;
    
    let newSi = sorter;

    sortedInfoRef.current = newSi;
    setSortedInfo(newSi);
    setFilteredInfo(filters || {});
    setCurPage(newPage);
    if (newPs !== pageSize) setPageSize(newPs);

    fetchData({ page: newPage, ps: newPs, si: newSi, filter: filters });
  }, [pageSize, fetchData]);

  const handleResetFilters = useCallback(() => {
    sortedInfoRef.current = [];
    setSortedInfo([]);
    setFilteredInfo({});
    setCurPage(1);
    if (onResetRequest) {
      onResetRequest();
    } else {
      fetchData({ page: 1, si: [], filter: {} });
    }
    message.success('Фильтры и сортировка сброшены');
  }, [onResetRequest, fetchData]);

  const handleImportClose = useCallback(() => {
    if (importLoading) return;
    setImportOpen(false); setImportFile(null); setImportResult(null);
  }, [importLoading]);

  const handleImportSelect = useCallback((file) => {
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      message.error('Поддерживаются только .xlsx / .xls файлы');
      return Upload.LIST_IGNORE;
    }
    setImportFile(file);
    setImportResult(null);
    return false;
  }, []);

  const handleImportSubmit = useCallback(async () => {
    if (!importFile) return;
    setImportLoading(true);
    try {
      const fd = new FormData();
      fd.append('file', importFile);
      const { data: res } = await api.post('/vacancies/import', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportResult(res);
      if (!res.errors?.length)
        message.success(`Импорт завершён: создано ${res.created}, обновлено ${res.updated}`);
      else
        message.warning(`Создано ${res.created}, обновлено ${res.updated} (есть предупреждения)`);
      fetchData();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Ошибка импорта');
    } finally {
      setImportLoading(false);
    }
  }, [importFile, fetchData]);

  const mkSort = (field) => {
    let order = null;
    if (Array.isArray(sortedInfo)) {
      const match = sortedInfo.find(s => s.field === field || s.columnKey === field);
      order = match ? match.order : null;
    } else {
      order = (sortedInfo?.field === field || sortedInfo?.columnKey === field) ? sortedInfo.order : null;
    }
    return {
      sorter: { multiple: 1 },
      sortOrder: order,
    };
  };

  // [БАГ 3 FIX] curPage и pageSize добавлены в deps
  const rawColumns = useMemo(() => {
    const dictFilter = (items, excludeIds) => ({
      filters: [
        ...(items || [])
          .filter(d => !(excludeIds && excludeIds.length > 0 && excludeIds.includes(d.id)))
          .map(d => ({ text: d.value, value: d.id })),
        { text: 'Без указания', value: 0 }
      ],
      filterSearch: true,
      filterDropdownProps: { getPopupContainer },
    });
    const si = sortedInfo;
    const fi = filteredInfo;
    return [
      {
        title: '№', dataIndex: '_rowIndex', key: '_rowIndex',
        width: 50, fixed: 'left', align: 'center',
        hideInSetting: true,
        render: (_, __, index) => (
          <span style={{ color: '#8c8c8c' }}>{(curPage - 1) * pageSize + index + 1}</span>
        ),
      },
      {
        title: 'Действия', dataIndex: '_actions', key: '_actions',
        width: 200, fixed: 'left', hideInSetting: true,
        render: (_, record) => (
          <Space size="small">
            <Tooltip title="Добавить отчет">
              <Button type="text" size="small" icon={<FileTextOutlined />}
                onClick={() => onReportClick?.(record)} data-tour="report-btn" />
            </Tooltip>
            <Tooltip title="История изменений">
              <Button type="text" size="small" icon={<HistoryOutlined />}
                style={{ color: '#722ed1' }}
                onClick={() => openHistoryDrawer(record)} data-tour="history-btn" />
            </Tooltip>
            <Tooltip title="Делегировать">
              <Button type="text" size="small" icon={<UserSwitchOutlined />}
                style={{ color: record.delegation ? '#fa8c16' : undefined }}
                onClick={() => openDelegationModal(record)} data-tour="delegate-btn" />
            </Tooltip>
            <Tooltip title="Редактировать">
              <Button type="text" size="small" icon={<EditOutlined />}
                onClick={() => onEdit(record)} data-tour="edit-btn" />
            </Tooltip>
            {isAdmin && (
              <Tooltip title="Удалить">
                <Button type="text" size="small" danger icon={<DeleteOutlined />}
                  onClick={() => onDelete(record.id)} data-tour="delete-btn" />
              </Tooltip>
            )}
          </Space>
        ),
      },
      {
        title: 'ID вакансии', dataIndex: 'vacancy_id', key: 'vacancy_id', ...mkSort('vacancy_id'),
        width: 120, ...(isAdmin ? { fixed: 'left' } : {}),
        filteredValue: fi.vacancy_id || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Дата открытия', dataIndex: 'open_date', key: 'open_date', ...mkSort('open_date'),
        width: 110,
        render: (d) => d ? dayjs(d).format('DD.MM.YY') : '-',
         filteredValue: fi.open_date || null,
        ...DATE_FILTER_DROPDOWN,
      },
      {
        title: WH('Количество'), dataIndex: 'quantity', key: 'quantity', ...mkSort('quantity'),
        width: 100, align: 'center',
        filteredValue: fi.quantity || null,
        ...NUMBER_FILTER_DROPDOWN,
      },
      {
        title: 'Уровень специалиста', dataIndex: 'level_id', key: 'level_id', width: 120,
        render: (_, r) => r.level_name || r.level?.value || '-',
        filteredValue: fi.level_id || null,
        ...dictFilter(dictionaries.specialist_level),
      },
      {
        title: 'Вакансия', dataIndex: 'position_name', key: 'position_name', width: 160, ellipsis: true,
        filteredValue: fi.position_name || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Статус вакансии', dataIndex: 'status_id', key: 'status_id', width: 140, ellipsis: true,
        render: (_, r) => {
          const s = r.status_name || r.status?.value;
          return s ? <span style={{ fontSize: 11 }}>{s}</span> : '-';
        },
        filteredValue: fi.status_id || null,
        ...dictFilter(dictionaries.vacancy_status, excludeStatusIds),
      },
      {
        title: 'ИТ роль', dataIndex: 'it_role_id', key: 'it_role_id', width: 130, ellipsis: true,
        render: (_, r) => r.it_role_name || r.it_role?.value || '-',
        filteredValue: fi.it_role_id || null,
        ...dictFilter(dictionaries.it_role),
      },
      {
        title: 'Адм. руководитель', dataIndex: 'admin_manager_id', key: 'admin_manager_id', width: 170, ellipsis: true,
        render: (_, r) => r.admin_manager_name || r.admin_manager?.value || '-',
        filteredValue: fi.admin_manager_id || null,
        ...dictFilter(dictionaries.admin_manager),
      },
      {
        title: 'Тимлид', dataIndex: 'team_lead_text', key: 'team_lead_text', width: 150, ellipsis: true,
        render: (_, r) => r.team_lead_text || r.team_lead_name || r.team_lead?.value || '-',
        filteredValue: fi.team_lead_text || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Проект', dataIndex: 'project_id', key: 'project_id', width: 150,
        render: (_, r) => r.project_name || r.project?.value || '-',
        filteredValue: fi.project_id || null,
        ...dictFilter(dictionaries.project),
      },
      {
        title: WH('Передано заказчику'), dataIndex: 'resume_at_customer', key: 'resume_at_customer', ...mkSort('resume_at_customer'),
        width: 110, align: 'center',
        filteredValue: fi.resume_at_customer || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => <span style={{ fontWeight: 500, color: '#1890FF' }}>{v || 0}</span>,
      },
      {
        title: WH('Резюме одобрено'), dataIndex: 'resume_approved', key: 'resume_approved', ...mkSort('resume_approved'),
        width: 110, align: 'center',
        filteredValue: fi.resume_approved || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => <span style={{ fontWeight: 500, color: '#52C41A' }}>{v || 0}</span>,
      },
      {
        title: WH('Собеседования факт'), dataIndex: 'interviews_fact', key: 'interviews_fact', ...mkSort('interviews_fact'),
        width: 110, align: 'center',
        filteredValue: fi.interviews_fact || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => <span style={{ fontWeight: 500, color: '#722ED1' }}>{v || 0}</span>,
      },
      {
        title: WH('Собеседования план'), dataIndex: 'interviews_plan', key: 'interviews_plan', ...mkSort('interviews_plan'),
        width: 110, align: 'center',
        filteredValue: fi.interviews_plan || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => <span style={{ fontWeight: 500, color: '#FA8C16' }}>{v || 0}</span>,
      },
      {
        title: WH('Оффер сделан'), dataIndex: 'offer_made', key: 'offer_made', ...mkSort('offer_made'),
        width: 100, align: 'center',
        filteredValue: fi.offer_made || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => <span style={{ fontWeight: 500, color: '#EB2F96' }}>{v || 0}</span>,
      },
      {
        title: 'Город', dataIndex: 'city_text', key: 'city_text', width: 110,
        render: (_, r) => r.city_text || r.city_name || r.city?.value || '-',
        filteredValue: fi.city_text || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Источник найма', dataIndex: 'source_id', key: 'source_id', width: 120,
        render: (_, r) => r.source_name || r.source?.value || '-',
        filteredValue: fi.source_id || null,
        ...dictFilter(dictionaries.source),
      },
      {
        title: 'Внутренний перевод', dataIndex: 'internal_transfer_id', key: 'internal_transfer_id', width: 120,
        render: (_, r) => r.internal_transfer_name || r.internal_transfer?.value || '-',
        filteredValue: fi.internal_transfer_id || null,
        ...dictFilter(dictionaries.internal_transfer),
      },
      {
        title: 'Дата изм. статуса', dataIndex: 'status_changed_at', key: 'status_changed_at', ...mkSort('status_changed_at'),
        width: 120,
        render: (d) => d ? dayjs(d).format('DD.MM.YY') : '-',
        filteredValue: fi.status_changed_at || null,
        ...DATE_FILTER_DROPDOWN,
      },
      {
        title: 'Дата закрытия', dataIndex: 'close_date', key: 'close_date', ...mkSort('close_date'),
        width: 110,
        render: (d) => d ? dayjs(d).format('DD.MM.YY') : '-',
        filteredValue: fi.close_date || null,
        ...DATE_FILTER_DROPDOWN,
      },
      {
        title: 'ФИО кандидата', dataIndex: 'candidate_name', key: 'candidate_name', width: 160, ellipsis: true,
        filteredValue: fi.candidate_name || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Компания кандидата', dataIndex: 'candidate_company', key: 'candidate_company', width: 140, ellipsis: true,
        filteredValue: fi.candidate_company || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Новая / Замена', dataIndex: 'replacement_type_id', key: 'replacement_type_id', width: 110,
        render: (_, r) => r.replacement_type_name || r.replacement_type?.value || '-',
        filteredValue: fi.replacement_type_id || null,
        ...dictFilter(dictionaries.replacement_type),
      },
      {
        title: 'ФИО бывшего сотр.', dataIndex: 'ex_employee_name', key: 'ex_employee_name', width: 160, ellipsis: true,
        filteredValue: fi.ex_employee_name || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'ID ШЕ', dataIndex: 'unit_id', key: 'unit_id', width: 110,
        filteredValue: fi.unit_id || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Вид занятости', dataIndex: 'employment_type_id', key: 'employment_type_id', width: 160,
        render: (_, r) => r.employment_type_name || r.employment_type?.value || '-',
        filteredValue: fi.employment_type_id || null,
        ...dictFilter(dictionaries.employment_type),
      },
      {
        title: 'ТЭО проекта', dataIndex: 'feasibility_id', key: 'feasibility_id', width: 140,
        render: (_, r) => r.feasibility_name || r.feasibility?.value || '-',
        filteredValue: fi.feasibility_id || null,
        ...dictFilter(dictionaries.feasibility),
      },
      {
        title: 'Ссылка IQHR', dataIndex: 'iqhr_link', key: 'iqhr_link', width: 90,
        render: (link) => link
          ? <a href={link} target="_blank" rel="noopener noreferrer">Открыть</a>
          : '-',
      },
      {
        title: 'Рекрутер', dataIndex: 'recruiter_id', key: 'recruiter_id', width: 185, ellipsis: true,
        render: (_, r) => {
          const ownerName = r.recruiter?.full_name || r.recruiter_name || '-';
          const deleg = r.delegation;
          if (!deleg || !isAdmin) return ownerName;
          const tempName = deleg.delegated_to?.full_name || `ID ${deleg.delegated_to_id}`;
          const shortTemp = tempName.split(' ').slice(0, 2).join(' ');
          return (
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              {ownerName}
              <Tag color="orange" style={{ margin: 0, fontSize: 11, padding: '0 4px', lineHeight: '18px' }}>
                врем. {shortTemp}
              </Tag>
            </span>
          );
        },
        filters: [
          ...(users || []).map(u => ({ text: u.full_name, value: u.id })),
          { text: 'Без указания', value: 0 }
        ],
        filterSearch: true,
        filterDropdownProps: { getPopupContainer },
        filteredValue: fi.recruiter_id || null,
      },
      {
        title: 'Блок', dataIndex: 'block_id', key: 'block_id', width: 130, ellipsis: true,
        render: (_, r) => r.block_name || r.block?.value || '-',
        filteredValue: fi.block_id || null,
        ...dictFilter(dictionaries.block),
      },
      {
        title: WH('Срок работы (дней)'), dataIndex: 'work_duration_days', key: 'work_duration_days',
        width: 100, align: 'center',
        render: (v) => v != null ? v : '-',
      },
      {
        title: WH('Зарплата кандидатов Gross'), dataIndex: 'salary_gross', key: 'salary_gross', ...mkSort('salary_gross'),
        width: 140, align: 'center',
        filteredValue: fi.salary_gross || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => v != null ? Number(v).toLocaleString('ru-RU') : '-',
      },
    ];
  }, [
    filteredInfo, sortedInfo, dictionaries, users,
    onReportClick, onEdit, onDelete, isAdmin,
    curPage, pageSize, openDelegationModal, openHistoryDrawer, // [БАГ 3 FIX]
    excludeStatusIds,
  ]);

  const handleResize = useCallback((key, width) => {
    setColumnsStateMap(prev => {
      const next = { ...prev };
      next[key] = {
        ...next[key],
        width,
      };
      return next;
    });
  }, []);

  const rawColMap = useMemo(() => {
    const m = {};
    rawColumns.forEach(c => { if (c.key) m[c.key] = c; });
    return m;
  }, [rawColumns]);

  // [БАГ 1 FIX] hideInSetting-колонки (№, Действия) всегда идут ПЕРВЫМИ.
  // Раньше при непустом columnOrder они попадали в fallback-хвост и теряли
  // позицию и fixed:'left', так как не входят в columnOrder.
  const columns = useMemo(() => {
    const pinned   = rawColumns.filter(c => c.hideInSetting);
    const settable = rawColumns.filter(c => !c.hideInSetting);

    let list = [];
    if (!columnOrder || columnOrder.length === 0) {
      const visible = settable.filter(c => {
        const s = columnsStateMap[c.key];
        return !s || s.show !== false;
      }).map(c => {
        const savedWidth = columnsStateMap[c.key]?.width;
        const widthVal = savedWidth ? Math.min(800, Math.max(80, savedWidth)) : (c.width ? Math.min(800, Math.max(80, c.width)) : 80);
        return {
          ...c,
          width: widthVal
        };
      });
      list = [...pinned, ...visible];
    } else {
      const ordered = [];
      const used    = new Set();

      columnOrder.forEach(item => {
        if (item.show === false) { used.add(item.key); return; }
        const col = rawColMap[item.key];
        if (!col) return;
        used.add(item.key);
        const fixedVal = item.fixed === 'left' ? 'left' : undefined;
        const savedWidth = columnsStateMap[col.key]?.width;
        const widthVal = savedWidth ? Math.min(800, Math.max(80, savedWidth)) : (col.width ? Math.min(800, Math.max(80, col.width)) : 80);
        ordered.push({ 
          ...col, 
          fixed: fixedVal, 
          width: widthVal 
        });
      });

      settable.forEach(c => { if (!used.has(c.key)) ordered.push(c); });
      list = [...pinned, ...ordered];
    }

    return list.map(col => {
      if (!col.key || col.hideInSetting) return col;
      return {
        ...col,
        onHeaderCell: (c) => ({
          width: c.width,
          onResize: (width) => handleResize(col.key, width),
        }),
      };
    });
  }, [rawColumns, rawColMap, columnOrder, columnsStateMap, handleResize]);

  const tableWidth = useMemo(() => {
    return columns.reduce((acc, col) => acc + (col.width || 100), 0);
  }, [columns]);

  // [БАГ 2 FIX] Читаем fixed из `columns`, а не из `rawColumns`.
  // rawColumns содержит исходный fixed из пропсов и не обновляется при
  // изменении настроек. columns уже содержит applied fixed из columnOrder.
  const openColumnSettings = useCallback(() => {
    const settable = columns.filter(c => !c.hideInSetting && c.key);
    setColModalLocalOrder(settable.map(col => {
      const label = typeof col.title === 'string'
        ? col.title
        : React.isValidElement(col.title)
          ? col.title.props?.children
          : String(col.key);
      return {
        key:   col.key,
        label,
        show:  columnsStateMap[col.key]?.show !== false,
        fixed: col.fixed || 'none',
      };
    }));
    setColModalVisible(true);
  }, [columns, columnsStateMap]); // зависит от columns, не rawColumns

  const applyColumnSettings = useCallback(() => {
    const newState = {};
    colModalLocalOrder.forEach((item, idx) => {
      const currentWidth = columnsStateMap[item.key]?.width;
      newState[item.key] = {
        show:  item.show,
        order: idx,
        fixed: item.fixed !== 'none' ? item.fixed : undefined,
        ...(currentWidth ? { width: currentWidth } : {}),
      };
    });
    setColumnsStateMap(newState);
    setColumnOrder(colModalLocalOrder.map(item => ({
      key: item.key, show: item.show, fixed: item.fixed || 'none',
    })));
    setColModalVisible(false);
  }, [colModalLocalOrder, columnsStateMap]);

  const activeFiltersCount = Object.values(filteredInfo).filter(v => v && v.length > 0).length;
  const activeSortsCount = Array.isArray(sortedInfo) ? sortedInfo.length : (sortedInfo?.columnKey ? 1 : 0);
  const totalActiveCount = activeFiltersCount + activeSortsCount;

  return (
    <>
    <div ref={containerRef} className="vacancy-table-container"
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      <div style={{
        display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8,
        padding: '8px 12px', background: '#fff',
        borderBottom: '1px solid #f0f0f0', flexShrink: 0,
      }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: '#262626' }}>Вакансии</span>
        <div style={{ flex: 1 }} />
        {isSuperAdmin && (
          <Button icon={<UploadOutlined />} size="small"
            onClick={() => setImportOpen(true)} data-testid="import-button">
            Импорт
          </Button>
        )}
        <Button
          icon={<ClearOutlined />} size="small"
          disabled={totalActiveCount === 0}
          onClick={handleResetFilters}
          data-testid="reset-filters-button" data-tour="reset-filters-btn"
        >
          {totalActiveCount > 0 ? `Активных фильтров по столбцам: ${totalActiveCount} Сбросить фильтры` : 'Сбросить фильтры'}
        </Button>
        <Button icon={<ReloadOutlined />} size="small"
          onClick={() => fetchData()} title="Обновить" data-tour="reload-btn" />
        <Button icon={<DownloadOutlined />} size="small"
          onClick={onExportClick} data-testid="export-button" data-tour="export-btn">
          Экспорт
        </Button>
        {user?.role === 'recruiter' && (
          <Tooltip title="Обучение по работе с системой">
            <Button
              icon={<QuestionCircleOutlined />}
              size="small"
              onClick={() => tourRef.current?.start()}
              data-testid="tour-button"
              data-tour="tour-btn"
            />
          </Tooltip>
        )}
        <Button type="primary" icon={<PlusOutlined />} size="small"
          onClick={onCreate} data-testid="create-vacancy-button" data-tour="create-btn">
          Создать
        </Button>
        {(isAdmin || user?.role === 'recruiter') && (
          <Tooltip title="Настройка столбцов">
            <Button icon={<SettingOutlined />} size="small"
              onClick={openColumnSettings} data-testid="column-settings-button" />
          </Tooltip>
        )}
      </div>

      <div style={{ flex: 1, overflow: 'hidden' }}>
        <Table
          components={{
            header: {
              cell: ResizableHeaderCell,
            },
          }}
          dataSource={data}
          columns={columns}
          rowKey="id"
          size="small"
          bordered
          loading={loading}
          rowClassName={getRowClassName}
          scroll={{ x: tableWidth, y: 'calc(100vh - 235px)' }}
          pagination={{
            current:         curPage,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['25', '50', '100'],
            showTotal:       (t, r) => `${r[0]}-${r[1]} из ${t}`,
          }}
          onChange={handleTableChange}
        />
      </div>

      <ColumnSettingsModal
        visible={colModalVisible}
        onClose={() => setColModalVisible(false)}
        onApply={applyColumnSettings}
        localOrder={colModalLocalOrder}
        setLocalOrder={setColModalLocalOrder}
        showReorder={isAdmin}
      />

      <Modal
        open={importOpen}
        onCancel={handleImportClose}
        title="Импорт вакансий из Excel"
        width={520}
        maskClosable={!importLoading}
        footer={[
          <Button key="cancel" onClick={handleImportClose} disabled={importLoading}>
            Отмена
          </Button>,
          <Button
            key="submit" type="primary" icon={<UploadOutlined />}
            loading={importLoading}
            disabled={!importFile || !!importResult}
            onClick={handleImportSubmit}
          >
            Загрузить
          </Button>,
        ]}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%' }} size={16}>
          <Upload.Dragger
            accept=".xlsx,.xls"
            showUploadList={false}
            beforeUpload={handleImportSelect}
            disabled={importLoading || !!importResult}
          >
            <p style={{ fontSize: 28, margin: '8px 0' }}>📂</p>
            <p style={{ fontWeight: 500 }}>Перетащите файл или нажмите для выбора</p>
            <p style={{ color: '#8c8c8c', fontSize: 12 }}>Поддерживаются .xlsx и .xls</p>
          </Upload.Dragger>

          {importFile && !importResult && (
            <div style={{ background: '#f6ffed', border: '1px solid #b7eb8f', borderRadius: 6, padding: '10px 14px' }}>
              <Space>
                <span style={{ fontSize: 20 }}>📄</span>
                <div>
                  <div style={{ fontWeight: 500 }}>{importFile.name}</div>
                  <div style={{ color: '#8c8c8c', fontSize: 12 }}>
                    {(importFile.size / 1024).toFixed(1)} КБ · готов к загрузке
                  </div>
                </div>
              </Space>
            </div>
          )}

          {importResult && (
            <div style={{ background: '#fafafa', border: '1px solid #d9d9d9', borderRadius: 6, padding: '12px 16px' }}>
              <div style={{ fontWeight: 600, marginBottom: 10 }}>Результат импорта:</div>
              <Space size={20}>
                <span style={{ color: '#52c41a' }}>✅ Создано: <strong>{importResult.created}</strong></span>
                <span style={{ color: '#1890ff' }}>🔄 Обновлено: <strong>{importResult.updated}</strong></span>
                <span style={{ color: '#8c8c8c' }}>📋 Строк: <strong>{importResult.total_rows}</strong></span>
              </Space>
              {importResult.errors?.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <div style={{ color: '#ff4d4f', fontWeight: 500, marginBottom: 4 }}>
                    ⚠️ Предупреждения ({importResult.errors.length}):
                  </div>
                  <div style={{
                    maxHeight: 130, overflowY: 'auto', background: '#fff2f0',
                    border: '1px solid #ffccc7', borderRadius: 4,
                    padding: '6px 10px', fontSize: 12, fontFamily: 'monospace',
                  }}>
                    {importResult.errors.map((e, i) => (
                      <div key={i} style={{ color: '#cf1322', marginBottom: 2 }}>{e}</div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!importFile && (
            <div style={{
              background: '#fffbe6', border: '1px solid #ffe58f',
              borderRadius: 6, padding: '8px 12px', fontSize: 12, color: '#614700',
            }}>
              ⚠️ <strong>Важно:</strong> импорт обновляет существующие вакансии по полю «ID вакансии»
              и создаёт новые. Операция необратима. Доступна только суперадмину.
            </div>
          )}
        </Space>
      </Modal>

    </div>
      <DelegationModal
        open={delegationModal.open}
        vacancy={delegationModal.vacancy}
        users={users || []}
        onClose={closeDelegationModal}
        onSuccess={() => { if (actionRef?.current?.reload) actionRef.current.reload(); }}
      />
      <VacancyHistoryDrawer
        open={historyDrawer.open}
        vacancy={historyDrawer.vacancy}
        onClose={closeHistoryDrawer}
      />
      <RecruiterTour ref={tourRef} user={user} onComplete={onTourComplete} />
    </>
  );
};

export default VacancyTable;

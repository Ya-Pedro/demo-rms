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
  Input, message, Upload, Modal, Checkbox, DatePicker, App, Select,
  Radio, Alert, Spin, Divider,
} from 'antd';
import {
  PlusOutlined, EditOutlined, DeleteOutlined,
  ClearOutlined, FileTextOutlined, DownloadOutlined, UploadOutlined,
  SettingOutlined, ArrowUpOutlined, ArrowDownOutlined, PushpinOutlined,
  ReloadOutlined, QuestionCircleOutlined, UserSwitchOutlined, HistoryOutlined,
  CommentOutlined, CheckCircleOutlined, ExclamationCircleOutlined,
  CloseCircleOutlined, InfoCircleOutlined, CheckOutlined,
  InboxOutlined, FileExcelOutlined, SyncOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { api } from '../App';

dayjs.extend(isoWeek);

import DelegationModal from '../components/DelegationModal';
import { OFFER_REJECTION_REASONS } from './DashboardPage';
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

const DateRangeFilterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
  const containerRef = React.useRef(null);
  const parseRange = (keys) => {
    if (!keys || keys.length === 0) return [null, null];
    const [from, to] = (keys[0] || '').split('|');
    const d1 = from && dayjs(from, 'DD.MM.YY', true).isValid() ? dayjs(from, 'DD.MM.YY') : null;
    const d2 = to && dayjs(to, 'DD.MM.YY', true).isValid() ? dayjs(to, 'DD.MM.YY') : null;
    return [d1, d2];
  };
  return (
    <div ref={containerRef} style={{ padding: '12px 16px' }}>
      <div style={{ marginBottom: 8, fontWeight: 500, fontSize: 13, color: 'var(--text-color)' }}>Выберите период</div>
      <DatePicker.RangePicker
        format="DD.MM.YYYY"
        placeholder={['Дата от', 'Дата до']}
        value={parseRange(selectedKeys)}
        getPopupContainer={() => document.body}
        style={{ width: 280, marginBottom: 10 }}
        onChange={(dates) => {
          if (dates && dates[0] && dates[1]) {
            setSelectedKeys([`${dates[0].format('DD.MM.YY')}|${dates[1].format('DD.MM.YY')}`]);
          } else {
            setSelectedKeys([]);
          }
        }}
        allowClear
      />
      <br />
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: 80 }}>Найти</Button>
        <Button onClick={() => { clearFilters(); confirm(); }} size="small" style={{ width: 80 }}>Сброс</Button>
      </Space>
    </div>
  );
};

const DATE_FILTER_DROPDOWN = {
  filterDropdown: (props) => <DateRangeFilterDropdown {...props} />,
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
  'comment', 'offer_rejection_reason', 'iqhr_link',
]);

const VACANCY_FILTERS_KEY = 'rms_vacancy_filters';
const loadSavedVacancyFilters = () => {
  try {
    const s = sessionStorage.getItem(VACANCY_FILTERS_KEY);
    return s ? JSON.parse(s) : {};
  } catch { return {}; }
};
const saveSavedVacancyFilters = (filters) => {
  try {
    if (!filters || Object.keys(filters).length === 0) {
      sessionStorage.removeItem(VACANCY_FILTERS_KEY);
    } else {
      sessionStorage.setItem(VACANCY_FILTERS_KEY, JSON.stringify(filters));
    }
  } catch {}
};
const NUMBER_FILTER_KEYS = new Set([
  'quantity', 'resume_at_customer', 'resume_approved', 
  'interviews_fact', 'interviews_plan', 'offer_made', 'offer_accepted',
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
    position: isSticky ? (restProps.style?.position || 'sticky') : 'relative',
  };

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
    if (!showReorder) return;
    setLocalOrder(prev => {
      const next = [...prev];
      next[idx] = { ...next[idx], show: !next[idx].show };
      return next;
    });
  }, [setLocalOrder, showReorder]);

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
              <Tooltip title={!showReorder ? "Скрытие колонок доступно только администраторам" : undefined}>
                <Checkbox
                  checked={showReorder ? (item.show !== false) : true}
                  disabled={!showReorder}
                  onChange={() => toggleShow(idx)}
                />
              </Tooltip>
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


const EditableCommentCell = ({ record, onSaveComment }) => {
  const [isEditing, setIsEditing] = useState(false);
  const [value, setValue] = useState(record.comment || '');

  useEffect(() => {
    setValue(record.comment || '');
  }, [record.comment]);

  const handleBlur = async () => {
    setIsEditing(false);
    if (value !== (record.comment || '')) {
      await onSaveComment(record.id, value);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleBlur();
    } else if (e.key === 'Escape') {
      setValue(record.comment || '');
      setIsEditing(false);
    }
  };

  if (isEditing) {
    return (
      <Input.TextArea
        autoFocus
        autoSize={{ minRows: 1, maxRows: 3 }}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onBlur={handleBlur}
        onKeyDown={handleKeyDown}
        style={{ padding: '2px 4px', fontSize: 13 }}
      />
    );
  }

  return (
    <div
      onDoubleClick={() => setIsEditing(true)}
      title="Двойной клик для редактирования комментария"
      style={{
        cursor: 'pointer',
        minHeight: 22,
        borderRadius: 4,
        padding: '2px 4px',
        wordBreak: 'break-word',
        whiteSpace: 'pre-wrap',
      }}
      className="editable-comment-cell"
    >
      {value ? (
        <span>{value}</span>
      ) : (
        <span style={{ color: '#bfbfbf', fontStyle: 'italic', fontSize: 12 }}>
          (клик x2)
        </span>
      )}
    </div>
  );
};

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
  const { modal } = App.useApp();
  const userId       = user?.id;
  const isSuperAdmin = user?.role === 'superadmin';
  const isAdmin      = user?.role === 'admin' || user?.role === 'superadmin';

  // Делегирование вакансий
  const [delegationModal, setDelegationModal] = useState({ open: false, vacancy: null });
  const openDelegationModal = useCallback((record) => setDelegationModal({ open: true, vacancy: record }), []);
  const closeDelegationModal = useCallback(() => setDelegationModal({ open: false, vacancy: null }), []);

  // Комментарий (модалка и инлайн)
  const [commentModal, setCommentModal] = useState({ open: false, record: null, text: '' });
  const openCommentModal = useCallback((record) => {
    setCommentModal({ open: true, record, text: record.comment || '' });
  }, []);

  // Массовое назначение рекрутера
  const [bulkAssignModalOpen, setBulkAssignModalOpen] = useState(false);
  const [bulkRecruiterId, setBulkRecruiterId] = useState(null);
  const [bulkAssignLoading, setBulkAssignLoading] = useState(false);

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

  const [filteredInfo, setFilteredInfo] = useState(loadSavedVacancyFilters);

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

  const [importOpen,                 setImportOpen]                 = useState(false);
  const [importFile,                 setImportFile]                 = useState(null);
  const [importLoading,              setImportLoading]              = useState(false);
  const [importPreviewLoading,       setImportPreviewLoading]       = useState(false);
  const [importPreview,              setImportPreview]              = useState(null);
  const [selectedDicts,              setSelectedDicts]              = useState(new Set());
  const [recruitersAction,           setRecruitersAction]           = useState('leave_empty');
  const [recruiterEmails,            setRecruiterEmails]            = useState({});
  const [autoFillMissingPositions,   setAutoFillMissingPositions]   = useState(true);
  const [importResult,               setImportResult]               = useState(null);
  const [importError,                setImportError]                = useState(null);

  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [selectAllSystem, setSelectAllSystem] = useState(false);
  const containerRef    = useRef(null);

  const saveTimeoutRef  = useRef(null);

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

      const rawSorters = Array.isArray(si) ? si : (si && (si.field || si.columnKey) ? [si] : []);
      const validSorters = rawSorters.filter(s => s && s.order && (s.field || s.columnKey));
      if (validSorters.length > 0) {
        const sf = validSorters.map(s => s.field || s.columnKey);
        const so = validSorters.map(s => s.order === 'ascend' ? 'asc' : 'desc');
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
        if (DATE_FILTER_KEYS.has(key)) {
          const val = Array.isArray(values) ? values[0] : values;
          if (val != null && val !== '') {
            // Date range filter: value is stored as "DD.MM.YY|DD.MM.YY"
            const parts = String(val).split('|');
            if (parts.length === 2) {
              const [from, to] = parts;
              // Convert DD.MM.YY to YYYY-MM-DD for backend
              const parseDate = (s) => {
                const d = dayjs(s, 'DD.MM.YY', true);
                return d.isValid() ? d.format('YYYY-MM-DD') : s;
              };
              if (from) sp.append(`search_${key}_from`, parseDate(from));
              if (to)   sp.append(`search_${key}_to`,   parseDate(to));
            } else {
              sp.append(`search_${key}`, String(val));
            }
          }
        } else if (TEXT_FILTER_KEYS.has(key) || NUMBER_FILTER_KEYS.has(key)) {
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

  useEffect(() => {
    document.body.classList.add('no-page-scroll');
    return () => document.body.classList.remove('no-page-scroll');
  }, []);

  const handleTableChange = useCallback((pagination, filters, sorter) => {
    const newPage = pagination.current  || 1;
    const newPs   = pagination.pageSize || pageSize;
    
    let newSi = sorter;
    if (Array.isArray(newSi)) {
      newSi = newSi.filter(s => s && s.order);
      if (newSi.length === 0) newSi = null;
    } else if (newSi && !newSi.order) {
      newSi = null;
    }

    sortedInfoRef.current = newSi;
    setSortedInfo(newSi);
    setFilteredInfo(filters || {});
    saveSavedVacancyFilters(filters || {});
    setCurPage(newPage);
    if (newPs !== pageSize) setPageSize(newPs);

    fetchData({ page: newPage, ps: newPs, si: newSi, filter: filters });
  }, [pageSize, fetchData]);

  const handleResetFilters = useCallback(() => {
    sortedInfoRef.current = null;
    setSortedInfo(null);
    setFilteredInfo({});
    saveSavedVacancyFilters({});
    setCurPage(1);
    if (onResetRequest) {
      onResetRequest();
    } else {
      fetchData({ page: 1, si: null, filter: {} });
    }
    message.success('Фильтры и сортировка сброшены');
  }, [onResetRequest, fetchData]);

  const handleImportClose = useCallback(() => {
    if (importLoading || importPreviewLoading) return;
    setImportOpen(false);
    setImportFile(null);
    setImportResult(null);
    setImportError(null);
    setImportPreview(null);
    setSelectedDicts(new Set());
    setRecruitersAction('leave_empty');
    setRecruiterEmails({});
    setAutoFillMissingPositions(true);
  }, [importLoading, importPreviewLoading]);

  const handleImportSelect = useCallback(async (file) => {
    if (!file.name.endsWith('.xlsx') && !file.name.endsWith('.xls')) {
      message.error('Поддерживаются только .xlsx / .xls файлы');
      return Upload.LIST_IGNORE;
    }
    setImportFile(file);
    setImportResult(null);
    setImportError(null);
    setImportPreview(null);
    setRecruiterEmails({});
    setImportPreviewLoading(true);

    try {
      const fd = new FormData();
      fd.append('file', file);
      const { data } = await api.post('/vacancies/import/preview', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportPreview(data);
      if (data.missing_dictionaries && data.missing_dictionaries.length > 0) {
        setSelectedDicts(new Set(data.missing_dictionaries.map(d => `${d.dict_type}:::${d.value}`)));
      } else {
        setSelectedDicts(new Set());
      }
      setRecruitersAction('leave_empty');
      setAutoFillMissingPositions(true);
    } catch (err) {
      const detail = err.response?.data?.detail;
      let errMsg = 'Ошибка анализа файла';
      let errList = [];
      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (detail && typeof detail === 'object') {
        errMsg = detail.message || 'Ошибка анализа файла';
        if (Array.isArray(detail.errors)) errList = detail.errors;
      }
      setImportError({ message: errMsg, errors: errList });
      message.error(errMsg);
    } finally {
      setImportPreviewLoading(false);
    }
    return false;
  }, []);

  const toggleDictItem = useCallback((key) => {
    setSelectedDicts(prev => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }, []);

  const selectAllDicts = useCallback(() => {
    if (!importPreview?.missing_dictionaries) return;
    setSelectedDicts(new Set(importPreview.missing_dictionaries.map(d => `${d.dict_type}:::${d.value}`)));
  }, [importPreview]);

  const unselectAllDicts = useCallback(() => {
    setSelectedDicts(new Set());
  }, []);

  const handleImportSubmit = useCallback(async () => {
    if (!importFile) return;
    setImportLoading(true);
    setImportError(null);
    try {
      const fd = new FormData();
      fd.append('file', importFile);

      if (importPreview?.missing_dictionaries?.length > 0) {
        const toAdd = importPreview.missing_dictionaries
          .filter(d => selectedDicts.has(`${d.dict_type}:::${d.value}`))
          .map(d => ({ type: d.dict_type, value: d.value }));
        fd.append('add_dictionaries_json', JSON.stringify(toAdd));
      }

      fd.append('recruiters_action', recruitersAction);
      if (recruitersAction === 'create_users' && importPreview?.missing_recruiters?.length > 0) {
        const rList = importPreview.missing_recruiters.map(r => ({
          name: r.name,
          email: (recruiterEmails[r.name] || '').trim(),
        }));
        fd.append('create_recruiters_json', JSON.stringify(rList));
      }

      fd.append('auto_fill_missing_positions', String(autoFillMissingPositions));
      fd.append('treat_dash_as_empty_date', 'true');

      const { data: res } = await api.post('/vacancies/import', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setImportResult(res);
      if (!res.errors?.length) {
        message.success(`Импорт завершён: создано ${res.created}, обновлено ${res.updated}`);
      } else {
        message.warning(`Создано ${res.created}, обновлено ${res.updated} (есть ошибки в строках: ${res.errors.length})`);
      }
      fetchData();
    } catch (err) {
      const detail = err.response?.data?.detail;
      let errMsg = 'Ошибка импорта';
      let errList = [];

      if (typeof detail === 'string') {
        errMsg = detail;
      } else if (detail && typeof detail === 'object') {
        errMsg = detail.message || 'Ошибка импорта';
        if (Array.isArray(detail.errors)) {
          errList = detail.errors;
        } else if (Array.isArray(detail)) {
          errList = detail.map(item => item.msg || (typeof item === 'string' ? item : JSON.stringify(item)));
        }
      }

      setImportError({ message: errMsg, errors: errList });
      message.error(errMsg);
    } finally {
      setImportLoading(false);
    }
  }, [importFile, importPreview, selectedDicts, recruitersAction, recruiterEmails, autoFillMissingPositions, fetchData]);

  const handleBulkDelete = useCallback(() => {
    if (selectedRowKeys.length === 0) return;
    
    if (selectAllSystem) {
      modal.confirm({
        title: `Удалить ВСЕ вакансии в системе (${total})?`,
        content: 'Это действие удалит абсолютно все вакансии, независимо от фильтров. Это нельзя отменить.',
        okText: 'Удалить всё',
        okType: 'danger',
        cancelText: 'Отмена',
        onOk: async () => {
          try {
            const res = await api.post('/vacancies/bulk-delete', { delete_all: true });
            message.success(`Удалено вакансий: ${res.data.deleted}`);
            if (res.data.errors?.length > 0) {
              message.warning(`Ошибки: ${res.data.errors.length}`);
            }
            setSelectedRowKeys([]);
            setSelectAllSystem(false);
            fetchData();
          } catch (error) {
            message.error(error.response?.data?.detail || 'Ошибка удаления');
          }
        },
      });
    } else {
      modal.confirm({
        title: `Удалить выбранные вакансии (${selectedRowKeys.length})?`,
        content: 'Это действие нельзя отменить.',
        okText: 'Удалить',
        okType: 'danger',
        cancelText: 'Отмена',
        onOk: async () => {
          try {
            const res = await api.post('/vacancies/bulk-delete', { ids: selectedRowKeys });
            message.success(`Удалено вакансий: ${res.data.deleted}`);
            if (res.data.errors?.length > 0) {
              message.warning(`Ошибки: ${res.data.errors.length}`);
            }
            setSelectedRowKeys([]);
            fetchData();
          } catch (error) {
            message.error(error.response?.data?.detail || 'Ошибка удаления');
          }
        },
      });
    }
  }, [selectedRowKeys, selectAllSystem, total, fetchData]);

  const handleSaveComment = useCallback(async (vacancyId, newComment) => {
    try {
      await api.patch(`/vacancies/${vacancyId}`, { comment: newComment });
      message.success('Комментарий сохранен');
      setData(prev => prev.map(row => row.id === vacancyId ? { ...row, comment: newComment } : row));
    } catch (err) {
      message.error(err.response?.data?.detail || 'Ошибка сохранения комментария');
    }
  }, []);

  const handleSaveCommentModal = useCallback(async () => {
    if (!commentModal.record) return;
    try {
      await api.patch(`/vacancies/${commentModal.record.id}`, { comment: commentModal.text });
      message.success('Комментарий сохранен');
      setData(prev => prev.map(row => row.id === commentModal.record.id ? { ...row, comment: commentModal.text } : row));
      setCommentModal({ open: false, record: null, text: '' });
    } catch (err) {
      message.error(err.response?.data?.detail || 'Ошибка сохранения комментария');
    }
  }, [commentModal]);

  const handleBulkAssignRecruiter = useCallback(async () => {
    if (!bulkRecruiterId || selectedRowKeys.length === 0) return;
    setBulkAssignLoading(true);
    try {
      const res = await api.post('/vacancies/bulk-assign-recruiter', {
        ids: selectedRowKeys,
        vacancy_ids: selectedRowKeys,
        recruiter_id: bulkRecruiterId,
      });
      const count = res.data.assigned_count ?? res.data.assigned ?? selectedRowKeys.length;
      message.success(`Рекрутер назначен на ${count} вакансий`);
      setBulkAssignModalOpen(false);
      setBulkRecruiterId(null);
      setSelectedRowKeys([]);
      fetchData();
    } catch (err) {
      message.error(err.response?.data?.detail || 'Ошибка массового назначения');
    } finally {
      setBulkAssignLoading(false);
    }
  }, [bulkRecruiterId, selectedRowKeys, fetchData]);

  const mkSort = (field) => {
    let order = null;
    if (Array.isArray(sortedInfo)) {
      const match = sortedInfo.find(s => (s.field === field || s.columnKey === field) && s.order);
      order = match ? match.order : null;
    } else {
      order = (sortedInfo?.field === field || sortedInfo?.columnKey === field) ? (sortedInfo.order || null) : null;
    }
    return {
      sorter: true,
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
            <Tooltip title="Комментарий">
              <Button type="text" size="small" icon={<CommentOutlined />}
                style={{ color: '#1890ff' }}
                onClick={() => openCommentModal(record)} />
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
        title: 'Уровень специалиста', dataIndex: 'level_id', key: 'level_id', ...mkSort('level_id'), width: 120,
        render: (_, r) => r.level_name || r.level?.value || '-',
        filteredValue: fi.level_id || null,
        ...dictFilter(dictionaries.specialist_level),
      },
      {
        title: 'Вакансия', dataIndex: 'position_name', key: 'position_name', ...mkSort('position_name'), width: 160, ellipsis: true,
        filteredValue: fi.position_name || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Статус вакансии', dataIndex: 'status_id', key: 'status_id', ...mkSort('status_id'), width: 140, ellipsis: true,
        render: (_, r) => {
          const s = r.status_name || r.status?.value;
          return s ? <span>{s}</span> : '-';
        },
        filteredValue: fi.status_id || null,
        ...dictFilter(dictionaries.vacancy_status, excludeStatusIds),
      },
      {
        title: 'ИТ роль', dataIndex: 'it_role_id', key: 'it_role_id', ...mkSort('it_role_id'), width: 130, ellipsis: true,
        render: (_, r) => r.it_role_name || r.it_role?.value || '-',
        filteredValue: fi.it_role_id || null,
        ...dictFilter(dictionaries.it_role),
      },
      {
        title: 'Адм. руководитель', dataIndex: 'admin_manager_id', key: 'admin_manager_id', ...mkSort('admin_manager_id'), width: 170, ellipsis: true,
        render: (_, r) => r.admin_manager_name || r.admin_manager?.value || '-',
        filteredValue: fi.admin_manager_id || null,
        ...dictFilter(dictionaries.admin_manager),
      },
      {
        title: 'Тимлид', dataIndex: 'team_lead_text', key: 'team_lead_text', ...mkSort('team_lead_text'), width: 150, ellipsis: true,
        render: (_, r) => r.team_lead_text || r.team_lead_name || r.team_lead?.value || '-',
        filteredValue: fi.team_lead_text || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Проект', dataIndex: 'project_id', key: 'project_id', ...mkSort('project_id'), width: 150,
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
        title: WH('Оффер принят'), dataIndex: 'offer_accepted', key: 'offer_accepted', ...mkSort('offer_accepted'),
        width: 100, align: 'center',
        filteredValue: fi.offer_accepted || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: (v) => <span style={{ fontWeight: 500, color: '#52C41A' }}>{v || 0}</span>,
      },
      {
        title: 'Причина отказа от Оффера', dataIndex: 'offer_rejection_reason', key: 'offer_rejection_reason', ...mkSort('offer_rejection_reason'), width: 170, ellipsis: true,
        filteredValue: fi.offer_rejection_reason || null,
        filters: (dictionaries?.offer_rejection_reason && dictionaries.offer_rejection_reason.length > 0)
          ? dictionaries.offer_rejection_reason.map(r => ({ text: r.value, value: r.value }))
          : OFFER_REJECTION_REASONS.map(r => ({ text: r.label, value: r.value })),
        filterSearch: true,
        filterDropdownProps: { getPopupContainer },
        render: (v) => v || '-',
      },
      {
        title: 'Город', dataIndex: 'city_text', key: 'city_text', ...mkSort('city_text'), width: 110,
        render: (_, r) => r.city_text || r.city_name || r.city?.value || '-',
        filteredValue: fi.city_text || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Источник найма', dataIndex: 'source_id', key: 'source_id', ...mkSort('source_id'), width: 120,
        render: (_, r) => r.source_name || r.source?.value || '-',
        filteredValue: fi.source_id || null,
        ...dictFilter(dictionaries.source),
      },
      {
        title: 'Внутренний перевод', dataIndex: 'internal_transfer_id', key: 'internal_transfer_id', ...mkSort('internal_transfer_id'), width: 120,
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
        title: 'ФИО кандидата', dataIndex: 'candidate_name', key: 'candidate_name', ...mkSort('candidate_name'), width: 160, ellipsis: true,
        filteredValue: fi.candidate_name || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Комментарий', dataIndex: 'comment', key: 'comment', ...mkSort('comment'), width: 200,
        filteredValue: fi.comment || null,
        ...TEXT_FILTER_DROPDOWN,
        render: (text, record) => (
          <EditableCommentCell
            record={record}
            onSaveComment={handleSaveComment}
          />
        ),
      },
      {
        title: 'Компания кандидата', dataIndex: 'candidate_company', key: 'candidate_company', ...mkSort('candidate_company'), width: 140, ellipsis: true,
        filteredValue: fi.candidate_company || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Новая / Замена', dataIndex: 'replacement_type_id', key: 'replacement_type_id', ...mkSort('replacement_type_id'), width: 110,
        render: (_, r) => r.replacement_type_name || r.replacement_type?.value || '-',
        filteredValue: fi.replacement_type_id || null,
        ...dictFilter(dictionaries.replacement_type),
      },
      {
        title: 'ФИО бывшего сотр.', dataIndex: 'ex_employee_name', key: 'ex_employee_name', ...mkSort('ex_employee_name'), width: 160, ellipsis: true,
        filteredValue: fi.ex_employee_name || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'ID ШЕ', dataIndex: 'unit_id', key: 'unit_id', ...mkSort('unit_id'), width: 110,
        filteredValue: fi.unit_id || null,
        ...TEXT_FILTER_DROPDOWN,
      },
      {
        title: 'Вид занятости', dataIndex: 'employment_type_id', key: 'employment_type_id', ...mkSort('employment_type_id'), width: 160,
        render: (_, r) => r.employment_type_name || r.employment_type?.value || '-',
        filteredValue: fi.employment_type_id || null,
        ...dictFilter(dictionaries.employment_type),
      },
      {
        title: 'ТЭО проекта', dataIndex: 'feasibility_id', key: 'feasibility_id', ...mkSort('feasibility_id'), width: 140, ellipsis: true,
        render: (_, r) => r.feasibility_name || r.feasibility?.value || r.feasibility_text || '-',
        filteredValue: fi.feasibility_id || null,
        ...dictFilter(dictionaries.feasibility),
      },
      {
        title: 'Ссылка IQHR', dataIndex: 'iqhr_link', key: 'iqhr_link', ...mkSort('iqhr_link'), width: 140, ellipsis: true,
        filteredValue: fi.iqhr_link || null,
        ...TEXT_FILTER_DROPDOWN,
        render: (link) => {
          if (!link) return '-';
          const isUrl = String(link).startsWith('http://') || String(link).startsWith('https://');
          return isUrl ? (
            <a href={link} target="_blank" rel="noopener noreferrer" title={link}>
              {link}
            </a>
          ) : (
            <span>{link}</span>
          );
        },
      },
      {
        title: 'Рекрутер', dataIndex: 'recruiter_id', key: 'recruiter_id', ...mkSort('recruiter_id'), width: 185, ellipsis: true,
        render: (_, r) => {
          const ownerName = r.recruiter?.full_name || r.recruiter_name || '-';
          const deleg = r.delegation;
          if (!deleg || !isAdmin) return ownerName;
          const tempName = deleg.delegated_to?.full_name || `ID ${deleg.delegated_to_id}`;
          const shortTemp = tempName.split(' ').slice(0, 2).join(' ');
          return (
            <span style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
              {ownerName}
              <Tag color="orange" style={{ margin: 0 }}>
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
        title: 'Доп. рекрутер', dataIndex: 'co_recruiter_id', key: 'co_recruiter_id', ...mkSort('co_recruiter_id'), width: 185, ellipsis: true,
        render: (_, r) => r.co_recruiter?.full_name || r.co_recruiter_name || '-',
        filters: [
          ...(users || []).map(u => ({ text: u.full_name, value: u.id })),
          { text: 'Без указания', value: 0 }
        ],
        filterSearch: true,
        filterDropdownProps: { getPopupContainer },
        filteredValue: fi.co_recruiter_id || null,
      },
      {
        title: 'Блок', dataIndex: 'block_id', key: 'block_id', ...mkSort('block_id'), width: 130, ellipsis: true,
        render: (_, r) => r.block_name || r.block?.value || '-',
        filteredValue: fi.block_id || null,
        ...dictFilter(dictionaries.block),
      },
      {
        title: WH('Срок работы (дней)'), dataIndex: 'work_duration_days', key: 'work_duration_days', ...mkSort('work_duration_days'),
        width: 100, align: 'center',
        filteredValue: fi.work_duration_days || null,
        ...NUMBER_FILTER_DROPDOWN,
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
    openCommentModal, handleSaveComment,
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
    rawColumns.forEach(c => {
      if (c.key) {
        m[c.key] = c;
        if (c.key === 'feasibility_id') {
          m['feasibility'] = c;
          m['feasibility_name'] = c;
          m['feasibility_text'] = c;
        }
      }
    });
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
        if (!isAdmin) return true;
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
        if (isAdmin && item.show === false) { used.add(item.key); return; }
        const col = rawColMap[item.key];
        if (!col) return;
        used.add(col.key);
        used.add(item.key);
        // Не даем ТЭО проекта быть зафиксированным (pinned/sticky)
        const fixedVal = (col.key === 'feasibility_id') ? undefined : (item.fixed === 'left' ? 'left' : undefined);
        const savedWidth = columnsStateMap[col.key]?.width || columnsStateMap[item.key]?.width;
        const widthVal = savedWidth ? Math.min(800, Math.max(80, savedWidth)) : (col.width ? Math.min(800, Math.max(80, col.width)) : 80);
        ordered.push({ 
          ...col, 
          fixed: fixedVal, 
          width: widthVal 
        });
      });

      settable.forEach(c => { 
        if (!used.has(c.key)) {
          const savedWidth = columnsStateMap[c.key]?.width;
          const widthVal = savedWidth ? Math.min(800, Math.max(80, savedWidth)) : (c.width ? Math.min(800, Math.max(80, c.width)) : 80);
          const fixedVal = (c.key === 'feasibility_id') ? undefined : (columnsStateMap[c.key]?.fixed === 'left' ? 'left' : (c.fixed === 'left' ? 'left' : undefined));
          ordered.push({
            ...c,
            fixed: fixedVal,
            width: widthVal,
          });
        }
      });
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
  }, [rawColumns, rawColMap, columnOrder, columnsStateMap, handleResize, isAdmin]);

  const tableWidth = useMemo(() => {
    return columns.reduce((acc, col) => acc + (col.width || 100), 0);
  }, [columns]);

  const openColumnSettings = useCallback(() => {
    const settable = rawColumns.filter(c => !c.hideInSetting && c.key);
    let orderList = [];

    if (columnOrder && columnOrder.length > 0) {
      const used = new Set();
      columnOrder.forEach(item => {
        const col = rawColMap[item.key];
        if (!col || col.hideInSetting) return;
        used.add(col.key);
        used.add(item.key);
        const label = typeof col.title === 'string'
          ? col.title
          : React.isValidElement(col.title)
            ? col.title.props?.children
            : String(col.key);
        const fixedVal = (col.key === 'feasibility_id') ? 'none' : (columnsStateMap[col.key]?.fixed || columnsStateMap[item.key]?.fixed || item.fixed || 'none');
        orderList.push({
          key:   col.key,
          label,
          show:  isAdmin ? (item.show !== false) : true,
          fixed: fixedVal,
        });
      });

      settable.forEach(col => {
        if (!used.has(col.key)) {
          const label = typeof col.title === 'string'
            ? col.title
            : React.isValidElement(col.title)
              ? col.title.props?.children
              : String(col.key);
          const fixedVal = (col.key === 'feasibility_id') ? 'none' : (columnsStateMap[col.key]?.fixed || 'none');
          orderList.push({
            key:   col.key,
            label,
            show:  isAdmin ? (columnsStateMap[col.key]?.show !== false) : true,
            fixed: fixedVal,
          });
        }
      });
    } else {
      orderList = settable.map(col => {
        const label = typeof col.title === 'string'
          ? col.title
          : React.isValidElement(col.title)
            ? col.title.props?.children
            : String(col.key);
        const fixedVal = (col.key === 'feasibility_id') ? 'none' : (columnsStateMap[col.key]?.fixed || col.fixed || 'none');
        return {
          key:   col.key,
          label,
          show:  isAdmin ? (columnsStateMap[col.key]?.show !== false) : true,
          fixed: fixedVal,
        };
      });
    }

    setColModalLocalOrder(orderList);
    setColModalVisible(true);
  }, [rawColumns, rawColMap, columnOrder, columnsStateMap, isAdmin]);

  const applyColumnSettings = useCallback(() => {
    const newState = {};
    colModalLocalOrder.forEach((item, idx) => {
      const currentWidth = columnsStateMap[item.key]?.width;
      newState[item.key] = {
        show:  isAdmin ? item.show : true,
        order: idx,
        fixed: item.fixed !== 'none' ? item.fixed : undefined,
        ...(currentWidth ? { width: currentWidth } : {}),
      };
    });
    setColumnsStateMap(newState);
    setColumnOrder(colModalLocalOrder.map(item => ({
      key: item.key, show: isAdmin ? item.show : true, fixed: item.fixed || 'none',
    })));
    setColModalVisible(false);
  }, [colModalLocalOrder, columnsStateMap, isAdmin]);

  const activeFiltersCount = Object.values(filteredInfo).filter(v => v && v.length > 0).length;
  const activeSortsCount = Array.isArray(sortedInfo)
    ? sortedInfo.filter(s => s && s.order).length
    : (sortedInfo?.order ? 1 : 0);
  const totalActiveCount = activeFiltersCount + activeSortsCount;

  return (
    <>
    <div ref={containerRef} className="vacancy-table-container"
      style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      <div className="table-toolbar" style={{
        display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 8,
        padding: '8px 12px', flexShrink: 0,
      }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: 'var(--text-color)' }}>Вакансии</span>
        <div style={{ flex: 1 }} />
        {isSuperAdmin && (
          <Button icon={<UploadOutlined />} size="small"
            onClick={() => setImportOpen(true)} data-testid="import-button">
            Импорт
          </Button>
        )}
        {isAdmin && selectedRowKeys.length > 0 && (
          <Button size="small" icon={<UserSwitchOutlined />}
            onClick={() => setBulkAssignModalOpen(true)} data-testid="bulk-assign-recruiter-button">
            Назначить рекрутера ({selectedRowKeys.length})
          </Button>
        )}
        {isSuperAdmin && selectedRowKeys.length > 0 && (
          <Button danger size="small" icon={<DeleteOutlined />}
            onClick={handleBulkDelete} data-testid="bulk-delete-button">
            {selectAllSystem ? `Удалить ВСЕ (${total})` : `Удалить выбранные (${selectedRowKeys.length})`}
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
          rowSelection={isAdmin ? {
            selectedRowKeys,
            onChange: (keys) => {
              setSelectedRowKeys(keys);
              if (keys.length === 0) setSelectAllSystem(false);
            },
            onSelectAll: (selected) => {
              if (selected && isSuperAdmin && total > data.length) {
                modal.confirm({
                  title: 'Выбор вакансий',
                  content: `Вы выбрали все вакансии на этой странице (${data.length}). Хотите выбрать вообще все вакансии в системе (${total}) для удаления?`,
                  okText: `Выбрать все (${total})`,
                  cancelText: `Только на странице (${data.length})`,
                  onOk: () => setSelectAllSystem(true),
                  onCancel: () => setSelectAllSystem(false)
                });
              } else {
                setSelectAllSystem(false);
              }
            }
          } : undefined}
          scroll={{ x: tableWidth, y: 'calc(100vh - 340px)' }}
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
        title={<span style={{ fontSize: 16, fontWeight: 700 }}>Импорт вакансий из Excel</span>}
        width={720}
        maskClosable={!importLoading && !importPreviewLoading}
        footer={[
          <Button key="cancel" onClick={handleImportClose} disabled={importLoading || importPreviewLoading} style={{ fontSize: 14 }}>
            {importResult ? 'Закрыть' : 'Отмена'}
          </Button>,
          !importResult && (
            <Button
              key="submit"
              type="primary"
              icon={<UploadOutlined />}
              loading={importLoading}
              disabled={!importFile || importPreviewLoading || !!importResult}
              onClick={handleImportSubmit}
              style={{ fontSize: 14 }}
            >
              {importPreview?.has_conflicts ? 'Применить и импортировать' : 'Импортировать'}
            </Button>
          ),
        ]}
        destroyOnClose
      >
        <Space direction="vertical" style={{ width: '100%', fontSize: 14 }} size={16}>
          {!importFile && (
            <Upload.Dragger
              accept=".xlsx,.xls"
              showUploadList={false}
              beforeUpload={handleImportSelect}
              disabled={importLoading || importPreviewLoading || !!importResult}
              style={{ padding: '24px 0' }}
            >
              <InboxOutlined style={{ fontSize: 44, color: '#1890ff', margin: '8px 0' }} />
              <p style={{ fontWeight: 600, fontSize: 15, margin: '6px 0' }}>Перетащите файл или нажмите для выбора</p>
              <p style={{ color: '#8c8c8c', fontSize: 13 }}>Поддерживаются файлы форматов .xlsx и .xls</p>
            </Upload.Dragger>
          )}

          {importFile && (
            <div style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: 8,
              padding: '12px 16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
            }}>
              <Space size={12}>
                <FileExcelOutlined style={{ fontSize: 28, color: '#16a34a' }} />
                <div>
                  <div style={{ fontWeight: 600, fontSize: 15, color: '#1e293b' }}>{importFile.name}</div>
                  <div style={{ color: '#64748b', fontSize: 13 }}>
                    {(importFile.size / 1024).toFixed(1)} КБ
                  </div>
                </div>
              </Space>
              {!importLoading && !importResult && (
                <Button size="middle" onClick={() => {
                  setImportFile(null);
                  setImportPreview(null);
                  setImportError(null);
                  setRecruiterEmails({});
                }} style={{ fontSize: 13 }}>
                  Выбрать другой файл
                </Button>
              )}
            </div>
          )}

          {importPreviewLoading && (
            <div style={{ textAlign: 'center', padding: '36px 12px' }}>
              <Spin size="large" />
              <div style={{ marginTop: 14, color: '#475569', fontSize: 14, fontWeight: 500 }}>
                Анализ файла... Проверяем колонки, справочники и строки
              </div>
            </div>
          )}

          {importPreview && !importResult && (
            <>
              {/* Статистика строк */}
              <div style={{
                background: '#f8fafc',
                border: '1px solid #e2e8f0',
                borderRadius: 6,
                padding: '8px 14px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                fontSize: 13,
                flexWrap: 'wrap',
                gap: 12,
              }}>
                <span>Всего строк: <strong>{importPreview.total_rows}</strong></span>
                <span style={{ color: '#0369a1' }}>К обновлению: <strong>{importPreview.existing_count}</strong></span>
                <span style={{ color: '#15803d' }}>Новых вакансий: <strong>{importPreview.new_count}</strong></span>
              </div>

              {/* Уведомление если нет конфликтов */}
              {!importPreview.has_conflicts && (
                <Alert
                  type="success"
                  showIcon
                  message={<span style={{ fontSize: 14, fontWeight: 600 }}>Файл проверен</span>}
                  description={<span style={{ fontSize: 13 }}>Все строки и справочники корректны. Можно начинать импорт.</span>}
                />
              )}

              {/* Блок параметров и сопоставления данных */}
              {importPreview.has_conflicts && (
                <div style={{
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: 8,
                  padding: '14px 16px',
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 8,
                    marginBottom: 12,
                    paddingBottom: 8,
                    borderBottom: '1px solid #f1f5f9',
                  }}>
                    <SettingOutlined style={{ color: '#0284c7', fontSize: 15 }} />
                    <span style={{ fontWeight: 600, color: '#1e293b', fontSize: 14 }}>
                      Параметры импорта
                    </span>
                  </div>

                  {/* 1. Недостающие справочники */}
                  {importPreview.missing_dictionaries?.length > 0 && (
                    <div style={{ marginBottom: 14 }}>
                      <div style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: 6,
                      }}>
                        <span style={{ fontWeight: 600, fontSize: 13, color: '#334155' }}>
                          Новые значения справочников ({importPreview.missing_dictionaries.length}):
                        </span>
                        <Space size={8} style={{ fontSize: 12 }}>
                          <Button size="small" type="link" onClick={selectAllDicts} style={{ padding: 0, height: 'auto', fontSize: 12 }}>
                            Выбрать все
                          </Button>
                          <span style={{ color: '#cbd5e1' }}>•</span>
                          <Button size="small" type="link" onClick={unselectAllDicts} style={{ padding: 0, height: 'auto', fontSize: 12 }}>
                            Снять все
                          </Button>
                        </Space>
                      </div>

                      <div style={{
                        maxHeight: 180,
                        overflowY: 'auto',
                        background: '#fafbfc',
                        border: '1px solid #e2e8f0',
                        borderRadius: 6,
                      }}>
                        {importPreview.missing_dictionaries.map((dictItem) => {
                          const key = `${dictItem.dict_type}:::${dictItem.value}`;
                          const isChecked = selectedDicts.has(key);
                          return (
                            <div key={key} style={{
                              display: 'flex',
                              alignItems: 'center',
                              justifyContent: 'space-between',
                              padding: '6px 10px',
                              borderBottom: '1px solid #f1f5f9',
                              fontSize: 13,
                              gap: 10,
                            }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flex: 1, minWidth: 0 }}>
                                <Checkbox
                                  checked={isChecked}
                                  onChange={() => toggleDictItem(key)}
                                />
                                <span style={{ fontWeight: 500, fontSize: 13, color: '#1e293b' }}>
                                  {dictItem.value}
                                </span>
                                <Tag color="blue" style={{ fontSize: 11, padding: '0 6px', margin: 0, borderRadius: 3 }}>
                                  {dictItem.dict_title || dictItem.dict_type}
                                </Tag>
                              </div>
                              <span style={{ color: '#94a3b8', fontSize: 12, whiteSpace: 'nowrap' }}>
                                {dictItem.count} {dictItem.count === 1 ? 'строка' : (dictItem.count > 1 && dictItem.count < 5 ? 'строки' : 'строк')}
                              </span>
                            </div>
                          );
                        })}
                      </div>
                      <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 4 }}>
                        Выбранные значения будут автоматически добавлены в справочники
                      </div>
                    </div>
                  )}

                  {/* 2. Ненайденные рекрутеры */}
                  {importPreview.missing_recruiters?.length > 0 && (
                    <div style={{ marginBottom: 14 }}>
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6, marginBottom: 6 }}>
                        <span style={{ fontWeight: 600, fontSize: 13, color: '#334155' }}>
                          Рекрутеры, не найденные в системе ({importPreview.missing_recruiters.length}):
                        </span>
                        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                          {importPreview.missing_recruiters.map((rec, i) => (
                            <Tag key={i} color="orange" style={{ margin: 0, fontSize: 12, padding: '1px 6px', borderRadius: 3 }}>
                              {rec.name} ({rec.count} {rec.count === 1 ? 'стр.' : 'стр.'})
                            </Tag>
                          ))}
                        </div>
                      </div>

                      <Radio.Group
                        value={recruitersAction}
                        onChange={(e) => setRecruitersAction(e.target.value)}
                        style={{ display: 'flex', flexDirection: 'column', gap: 4 }}
                      >
                        <Radio value="leave_empty">
                          <span style={{ fontSize: 13 }}>
                            Оставить пустым <span style={{ color: '#64748b', fontSize: 12 }}>(рекомендуется)</span>
                          </span>
                        </Radio>
                        <Radio value="create_users">
                          <span style={{ fontSize: 13 }}>
                            Создать учетные записи с ролью «Рекрутер»
                          </span>
                        </Radio>
                      </Radio.Group>

                      {recruitersAction === 'create_users' && (
                        <div style={{
                          marginTop: 8,
                          background: '#fafbfc',
                          border: '1px solid #e2e8f0',
                          borderRadius: 6,
                          padding: '8px 12px',
                          display: 'flex',
                          flexDirection: 'column',
                          gap: 6,
                        }}>
                          <div style={{ fontSize: 12, color: '#64748b' }}>
                            Корпоративный email для новых рекрутеров:
                          </div>
                          {importPreview.missing_recruiters.map((rec) => (
                            <div key={rec.name} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                              <span style={{ fontSize: 13, fontWeight: 500, minWidth: 140, color: '#1e293b' }}>
                                {rec.name}:
                              </span>
                              <Input
                                size="small"
                                placeholder="например: a.mosina@company.ru"
                                value={recruiterEmails[rec.name] || ''}
                                onChange={(e) => setRecruiterEmails(prev => ({ ...prev, [rec.name]: e.target.value }))}
                                style={{ maxWidth: 280, fontSize: 13 }}
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {/* 3. Вакансии без названия */}
                  {importPreview.missing_positions?.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      <Checkbox
                        checked={autoFillMissingPositions}
                        onChange={(e) => setAutoFillMissingPositions(e.target.checked)}
                      >
                        <span style={{ fontSize: 13, color: '#1e293b' }}>
                          Присвоить <strong>«Вакансия {'{ID}'}»</strong> строкам без названия ({importPreview.missing_positions.map(p => p.row).join(', ')})
                        </span>
                      </Checkbox>
                    </div>
                  )}

                  {/* 4. Прочерки в датах */}
                  {importPreview.dash_dates_count > 0 && (
                    <div style={{
                      color: '#64748b',
                      fontSize: 12,
                      display: 'flex',
                      alignItems: 'center',
                      gap: 6,
                      paddingTop: 6,
                      borderTop: '1px solid #f1f5f9',
                    }}>
                      <InfoCircleOutlined style={{ color: '#94a3b8' }} />
                      <span>Прочерки в датах ({importPreview.dash_dates_count} яч.) будут сохранены как пустые значения</span>
                    </div>
                  )}

                  {/* 5. Прочие ошибки формата */}
                  {importPreview.other_errors?.length > 0 && (
                    <div style={{ marginTop: 10 }}>
                      <div style={{ color: '#dc2626', fontWeight: 600, fontSize: 13, marginBottom: 4, display: 'flex', alignItems: 'center', gap: 6 }}>
                        <CloseCircleOutlined style={{ color: '#dc2626' }} />
                        <span>Ошибки формата данных ({importPreview.other_errors.length}):</span>
                      </div>
                      <div style={{
                        maxHeight: 120,
                        overflowY: 'auto',
                        background: '#fff7f7',
                        border: '1px solid #fecaca',
                        borderRadius: 6,
                        padding: '6px 10px',
                        fontSize: 12,
                        fontFamily: 'monospace',
                      }}>
                        {importPreview.other_errors.map((err, i) => (
                          <div key={i} style={{ color: '#dc2626', marginBottom: 2 }}>
                            • {err}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </>
          )}

          {importError && (
            <div style={{
              background: '#fff2f0',
              border: '1px solid #ffccc7',
              borderRadius: 8,
              padding: '14px 16px',
            }}>
              <div style={{ color: '#cf1322', fontWeight: 600, fontSize: 14, display: 'flex', alignItems: 'center', gap: 8, marginBottom: importError.errors?.length ? 10 : 0 }}>
                <CloseCircleOutlined style={{ color: '#cf1322' }} />
                <span>{importError.message}</span>
              </div>
              {importError.errors?.length > 0 && (
                <>
                  <div style={{ fontSize: 13, color: '#64748b', marginBottom: 6 }}>
                    Обнаружены ошибки ({importError.errors.length}):
                  </div>
                  <div style={{
                    maxHeight: 180,
                    overflowY: 'auto',
                    background: '#ffffff',
                    border: '1px solid #ffa39e',
                    borderRadius: 6,
                    padding: '8px 12px',
                    fontSize: 13,
                    lineHeight: '1.5',
                  }}>
                    {importError.errors.map((e, i) => (
                      <div key={i} style={{ color: '#cf1322', marginBottom: 4, fontFamily: 'monospace' }}>
                        • {e}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          )}

          {importResult && (
            <div style={{ background: '#f8fafc', border: '1px solid #cbd5e1', borderRadius: 8, padding: '14px 18px' }}>
              <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 12 }}>Результат импорта:</div>
              <Space size={24} style={{ fontSize: 14 }}>
                <span style={{ color: '#16a34a', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircleOutlined style={{ color: '#16a34a' }} /> Создано: <strong>{importResult.created}</strong>
                </span>
                <span style={{ color: '#2563eb', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
                  <SyncOutlined style={{ color: '#2563eb' }} /> Обновлено: <strong>{importResult.updated}</strong>
                </span>
                <span style={{ color: '#475569' }}>
                  Всего строк: <strong>{importResult.total_rows}</strong>
                </span>
              </Space>
              {importResult.errors?.length > 0 && (
                <div style={{ marginTop: 14 }}>
                  <div style={{ color: '#d97706', fontWeight: 600, fontSize: 13, marginBottom: 6, display: 'flex', alignItems: 'center', gap: 6 }}>
                    <ExclamationCircleOutlined style={{ color: '#d97706' }} />
                    <span>Пропущены строки с ошибками ({importResult.errors.length}):</span>
                  </div>
                  <div style={{
                    maxHeight: 180,
                    overflowY: 'auto',
                    background: '#fffbe6',
                    border: '1px solid #ffe58f',
                    borderRadius: 6,
                    padding: '8px 12px',
                    fontSize: 13,
                    lineHeight: '1.5',
                  }}>
                    {importResult.errors.map((e, i) => (
                      <div key={i} style={{ color: '#b45309', marginBottom: 4, fontFamily: 'monospace' }}>
                        • {e}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {!importFile && (
            <div style={{
              background: '#f8fafc', border: '1px solid #e2e8f0',
              borderRadius: 6, padding: '10px 14px', fontSize: 13, color: '#475569',
              display: 'flex', alignItems: 'center', gap: 8,
            }}>
              <InfoCircleOutlined style={{ color: '#64748b' }} />
              <span>Импорт обновляет существующие вакансии по полю «ID вакансии» и создаёт новые. Доступен только суперадмину.</span>
            </div>
          )}
        </Space>
      </Modal>

      {/* Модальное окно комментария к вакансии */}
      <Modal
        title={`Комментарий: ${commentModal.record?.position_name || ''}`}
        open={commentModal.open}
        onCancel={() => setCommentModal({ open: false, record: null, text: '' })}
        onOk={handleSaveCommentModal}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <div style={{ marginTop: 12 }}>
          <Input.TextArea
            rows={5}
            value={commentModal.text}
            onChange={(e) => setCommentModal(prev => ({ ...prev, text: e.target.value }))}
            placeholder="Введите комментарий..."
          />
        </div>
      </Modal>

      {/* Модальное окно массового назначения рекрутера */}
      <Modal
        title={`Массовое назначение рекрутера (${selectedRowKeys.length} вакансий)`}
        open={bulkAssignModalOpen}
        onCancel={() => {
          setBulkAssignModalOpen(false);
          setBulkRecruiterId(null);
        }}
        onOk={handleBulkAssignRecruiter}
        okText="Назначить"
        cancelText="Отмена"
        confirmLoading={bulkAssignLoading}
        okButtonProps={{ disabled: !bulkRecruiterId }}
      >
        <div style={{ marginTop: 12 }}>
          <div style={{ marginBottom: 8, fontWeight: 500 }}>Выберите нового рекрутера:</div>
          <Select
            style={{ width: '100%' }}
            placeholder="Выберите рекрутера"
            popupMatchSelectWidth={false}
            showSearch
            optionFilterProp="label"
            value={bulkRecruiterId}
            onChange={setBulkRecruiterId}
            options={(users || []).map(u => ({ value: u.id, label: u.full_name }))}
          />
        </div>
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

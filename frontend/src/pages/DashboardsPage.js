import React, { useState, useMemo, useEffect } from 'react';
import dayjs from 'dayjs';
import useIsMobile from '../hooks/useIsMobile';
import {
  Row, Col, Card, Select, Skeleton, Typography, Statistic, Divider,
  DatePicker, Button, Spin, Space, Radio, Modal, Tooltip,
  Popover, Checkbox, Input, Table, message, Tabs, Alert,
} from 'antd';
import {
  ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip as RTooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList,
  Cell as BCell,
  LineChart, Line,
} from 'recharts';
import {
  RiseOutlined, TeamOutlined,
  FunnelPlotOutlined, PieChartOutlined, FilterOutlined,
  ClearOutlined, FieldTimeOutlined, BankOutlined,
  FileTextOutlined, ReloadOutlined, InfoCircleOutlined, DollarOutlined,
  DownOutlined, DownloadOutlined, SearchOutlined,
  TableOutlined, SettingOutlined, HolderOutlined,
  ArrowLeftOutlined, ArrowRightOutlined, UndoOutlined, CheckOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api, ThemeContext } from '../App';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const T = {
  bg: 'var(--layout-bg)', border: 'var(--border-color)',
  text: 'var(--text-color)', sub: '#8b949e', muted: '#8b949e',
  blue: '#1677ff', green: '#16a34a', red: '#dc2626',
  amber: '#d97706', purple: '#7c3aed', teal: '#0d9488',
};

const PALETTE = [
  '#1677ff','#16a34a','#d97706','#7c3aed','#0d9488',
  '#dc2626','#ea580c','#0891b2','#65a30d','#be185d',
  '#4f46e5','#14b8a6','#f59e0b','#a855f7','#10b981',
];

const STATUS_COLOR = {
  'Открыта': '#1677ff', 'Закрыта': '#16a34a', 'Hold': '#d97706',
  'Отмена': '#dc2626', 'Оффер': '#7c3aed', 'Выход': '#0d9488',
  'Подготовка документов': '#ea580c', 'Проверка СБ': '#4f46e5',
  'Согласование фин условий': '#0891b2',
};

const CS  = { borderRadius: 10, border: `1px solid ${T.border}`, boxShadow: 'none', height: '100%' };
const CBS = { padding: '16px 20px' };
const CHS = { borderBottom: `1px solid ${T.border}`, padding: '12px 20px', minHeight: 'unset', fontSize: 14, fontWeight: 600, color: T.text };

// Unified typography standards across all dashboard charts
const FS_AXIS_LABEL = 13; // Category labels on axes (recruiter, status, company, level, stage)
const FS_AXIS_NUM   = 12; // Numeric ticks on axes (0, 10, 20...)
const FS_BAR_VAL    = 13; // Values directly on chart bars / points
const FS_LEGEND     = 13; // Legend items and percentages

// Descriptions and formulas for all dashboard charts — concise, clear and uniform
const CHART_FORMULAS = {
  salaries: {
    title: 'Медианная зарплата (Gross)',
    formula: 'Q1 (25%) • Медиана (50%) • Q3 (75%)',
    description: 'Расчёт 25-го перцентиля (Q1), медианы (50%) и 75-го перцентиля (Q3) совокупного дохода кандидатов Gross по вакансиям.',
    rules: 'Данные рассчитываются на основе поля «Зарплата кандидатов Gross» для вакансий с учётом всех активных фильтров.',
  },
  source: {
    title: 'Источник найма',
    formula: '(Вакансии источника / Всего закрытых) × 100%',
    description: 'Доля закрытых вакансий по каждому каналу подбора',
    rules: 'Только вакансии со статусом «Закрыта».',
  },
  replacement: {
    title: 'Тип вакансии (Новая / Замена)',
    formula: '(Вакансии типа / Всего вакансий) × 100%',
    description: 'Соотношение позиций под расширение команды (Новая) и на замену уволившихся специалистов (Замена).',
    rules: 'Все вакансии с учётом выбранных фильтров.',
  },
  employment: {
    title: 'Вид занятости',
    formula: '(Вакансии вида / Всего вакансий) × 100%',
    description: 'Распределение вакансий по формату найма',
    rules: 'Все вакансии с учётом выбранных фильтров.',
  },
  jo_conversion: {
    title: 'Конверсия принятия JO',
    formula: '(Закрытые вакансии / Сделано офферов) × 100%',
    description: 'Процент кандидатов, принявших предложение о работе (Job Offer), с динамикой по месяцам, кварталам или годам.',
    rules: 'Зелёный маркер — максимум периода, красный — минимум.',
  },
  levels: {
    title: 'Распределение по уровню ИТ роли',
    formula: 'Количество вакансий по каждому грейду',
    description: 'Число вакансий по квалификации: Junior, Middle, Senior, Lead, Руководитель.',
    rules: 'Все вакансии с учётом выбранных фильтров.',
  },
  recruiter_load: {
    title: 'Загрузка рекрутеров',
    formula: 'Количество вакансий у каждого рекрутера',
    description: 'Объём вакансий у каждого рекрутера команды.',
    rules: 'Учитываются основной и дополнительный рекрутеры.',
  },
  open_details: {
    title: 'Детализация «Открытых» вакансий',
    formula: 'Количество вакансий на каждом этапе подбора',
    description: 'Распределение активных позиций по текущим этапам (Открыта, Проверка СБ, Оффер, Согласование фин условий, Подготовка документов, Выход)',
    rules: 'Исключены финальные статусы («Закрыта», «Hold», «Отмена»).',
  },
  statuses: {
    title: 'Вакансии по статусам',
    formula: 'Открыта + Закрыта + Hold + Отмена',
    description: 'Общий баланс всех вакансий компании по ключевым группам статусов.',
    rules: '«Всего» = Открыта + Закрыта + Hold + Отмена. «Открыта» и «Hold» — остаток на дату конца периода (включая вакансии, ушедшие в Hold до начала периода). «Закрыта» и «Отмена» — поток переходов внутри периода. Статус «Выход» включён в «Открыта».',
  },
  statuses_ivakhin: {
    title: 'Вакансии по статусам для Ивахина А',
    formula: 'Открыта + Hold (остаток на конец месяца) с детализацией по ИТ-блокам',
    description: 'Уникальное количество вакансий компании в разрезе месяцев и ИТ-блоков.',
    rules: 'Учитываются только основные рекрутеры (дополнительные и замещающие не дублируют вакансии). «Открыта» и «Hold» — остаток на конец месяца. «Закрыта» и «Отмена» — поток за месяц. «Всего вакансий» = Открыта + Hold.',
  },
  funnel: {
    title: 'Воронка найма',
    formula: 'Сумма показателей из еженедельных отчётов и % перехода с этапа на этап',
    description: 'Движение кандидатов по этапам: Передано заказчику → Резюме одобрено → Собеседования → Оффер сделан → Оффер принят → Закрыта.',
    rules: 'Данные суммируются за выбранный период и рассчитывается % перехода.',
  },
  rejections: {
    title: 'Причины отказа',
    formula: 'Количество отказов по каждой причине',
    description: 'Причины, по которым кандидаты отклонили оффер (уровень дохода, контроффер, локация и др.).',
    rules: 'Отображаются все причины из справочника; при отсутствии отказов значение 0.',
  },
  companies: {
    title: 'Топ-15 компаний кандидатов',
    formula: 'Количество нанятых кандидатов из компании',
    description: 'Внешние компании-доноры, из которых чаще всего переходят успешно нанятые специалисты.',
    rules: 'Только закрытые вакансии с указанием компании кандидата.',
  },
  avg_days: {
    title: 'Средний срок закрытия (раб. дни)',
    formula: 'Сумма рабочих дней / Количество закрытых вакансий',
    description: 'Чистое рабочее время от даты открытия до даты закрытия по производственному календарю РФ.',
    rules: 'Выходные и праздники исключены; дни нахождения в «Hold» автоматически вычитаются.',
  },
  avg_days_timeline: {
    title: 'Средний срок закрытия вакансии (динамика)',
    formula: 'Сумма рабочих дней / Количество закрытых вакансий',
    description: 'Динамика чистого времени закрытия вакансий в рабочих днях по месяцам, кварталам и годам.',
    rules: 'Выходные и праздники исключены; дни нахождения в «Hold» автоматически вычитаются.',
  },
};

const DASHBOARD_CARDS_MAP = {
  salary: { id: 'salary', title: 'Медианная ЗП (Gross)', defaultSize: 24 },
  donut_source: { id: 'donut_source', title: 'Источник найма', defaultSize: 8 },
  donut_replacement: { id: 'donut_replacement', title: 'Тип вакансии (Новая/Замена)', defaultSize: 8 },
  donut_employment: { id: 'donut_employment', title: 'Вид занятости', defaultSize: 8 },
  avg_timeline: { id: 'avg_timeline', title: 'Динамика среднего срока закрытия', defaultSize: 24 },
  jo_conversion: { id: 'jo_conversion', title: 'Конверсия принятия JO', defaultSize: 24 },
  recruiter_load: { id: 'recruiter_load', title: 'Загрузка рекрутеров', defaultSize: 24 },
  ivakhin_statuses: { id: 'ivakhin_statuses', title: 'Вакансии по статусам для Ивахина А', defaultSize: 24 },
  statuses_chart: { id: 'statuses_chart', title: 'Вакансии по статусам', defaultSize: 12 },
  open_details: { id: 'open_details', title: 'Детализация «Открытых» вакансий', defaultSize: 12 },
  funnel: { id: 'funnel', title: 'Воронка найма', defaultSize: 14 },
  rejections: { id: 'rejections', title: 'Причины отказа', defaultSize: 10 },
  companies: { id: 'companies', title: 'Топ-15 компаний кандидатов', defaultSize: 24 },
  avg_days_role: { id: 'avg_days_role', title: 'Средний срок закрытия', defaultSize: 12 },
  levels: { id: 'levels', title: 'Распределение вакансий по уровню ИТ роли', defaultSize: 12 },
};

const DEFAULT_TAB_LAYOUTS = {
  all: [
    { id: 'salary', size: 24 },
    { id: 'donut_source', size: 8 },
    { id: 'donut_replacement', size: 8 },
    { id: 'donut_employment', size: 8 },
    { id: 'avg_timeline', size: 24 },
    { id: 'jo_conversion', size: 24 },
    { id: 'recruiter_load', size: 24 },
    { id: 'ivakhin_statuses', size: 24 },
    { id: 'statuses_chart', size: 12 },
    { id: 'open_details', size: 12 },
    { id: 'funnel', size: 14 },
    { id: 'rejections', size: 10 },
    { id: 'companies', size: 24 },
    { id: 'avg_days_role', size: 12 },
    { id: 'levels', size: 12 },
  ],
  statuses: [
    { id: 'recruiter_load', size: 24 },
    { id: 'ivakhin_statuses', size: 24 },
    { id: 'statuses_chart', size: 12 },
    { id: 'open_details', size: 12 },
  ],
  funnel: [
    { id: 'jo_conversion', size: 24 },
    { id: 'funnel', size: 14 },
    { id: 'rejections', size: 10 },
    { id: 'companies', size: 24 },
  ],
  analytics: [
    { id: 'salary', size: 24 },
    { id: 'donut_source', size: 8 },
    { id: 'donut_replacement', size: 8 },
    { id: 'donut_employment', size: 8 },
    { id: 'avg_timeline', size: 24 },
    { id: 'avg_days_role', size: 12 },
    { id: 'levels', size: 12 },
  ],
};

const CUSTOM_LAYOUTS_KEY = 'rms_dashboards_custom_layouts_v2';

const sanitizeLayout = (savedList, defaultList) => {
  if (!Array.isArray(savedList) || !savedList.length) return defaultList;
  const savedIds = new Set();
  const validCards = [];
  for (const item of savedList) {
    if (item && item.id && DASHBOARD_CARDS_MAP[item.id] && !savedIds.has(item.id)) {
      savedIds.add(item.id);
      validCards.push({
        id: item.id,
        size: Number(item.size) || DASHBOARD_CARDS_MAP[item.id]?.defaultSize || 24,
      });
    }
  }
  for (const def of defaultList) {
    if (!savedIds.has(def.id)) {
      validCards.push(def);
    }
  }
  return validCards.length ? validCards : defaultList;
};

const loadCustomLayouts = () => {
  try {
    const raw = localStorage.getItem(CUSTOM_LAYOUTS_KEY);
    if (!raw) return DEFAULT_TAB_LAYOUTS;
    const parsed = JSON.parse(raw);
    return {
      all: sanitizeLayout(parsed.all, DEFAULT_TAB_LAYOUTS.all),
      statuses: sanitizeLayout(parsed.statuses, DEFAULT_TAB_LAYOUTS.statuses),
      funnel: sanitizeLayout(parsed.funnel, DEFAULT_TAB_LAYOUTS.funnel),
      analytics: sanitizeLayout(parsed.analytics, DEFAULT_TAB_LAYOUTS.analytics),
    };
  } catch {
    return DEFAULT_TAB_LAYOUTS;
  }
};

const saveCustomLayouts = (layouts) => {
  try {
    localStorage.setItem(CUSTOM_LAYOUTS_KEY, JSON.stringify(layouts));
  } catch {}
};

// Subtle and elegant formula button
const FormulaButton = ({ chartKey, onOpen, isMobile }) => (
  <Tooltip title="Как рассчитывается график">
    <Button
      type="text"
      size="small"
      icon={<InfoCircleOutlined style={{ fontSize: 13 }} />}
      onClick={(e) => {
        e.stopPropagation();
        onOpen(chartKey);
      }}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 5,
        padding: '3px 10px',
        height: 26,
        borderRadius: 6,
        fontSize: 13,
        fontWeight: 500,
        color: '#64748b',
        background: 'rgba(100, 116, 139, 0.08)',
        border: '1px solid rgba(100, 116, 139, 0.18)',
        marginLeft: 8,
      }}
    >
      {!isMobile && 'Формула'}
    </Button>
  </Tooltip>
);

// Formula Modal dialog — large readable typography
const FormulaModal = ({ formulaKey, onClose }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const info = formulaKey ? CHART_FORMULAS[formulaKey] : null;

  return (
    <Modal
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <InfoCircleOutlined style={{ color: isDarkMode ? '#4096ff' : '#1677ff', fontSize: 19 }} />
          <span style={{ fontSize: 18, fontWeight: 600, color: 'var(--text-color)' }}>
            {info?.title}
          </span>
        </div>
      }
      open={!!info}
      onCancel={onClose}
      footer={[
        <Button
          key="close"
          type="primary"
          onClick={onClose}
          style={{ borderRadius: 8, minWidth: 110, height: 36, fontSize: 14, fontWeight: 500 }}
        >
          Понятно
        </Button>,
      ]}
      width={560}
      centered
      destroyOnClose
    >
      {info && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 18, paddingTop: 14, paddingBottom: 6 }}>
          {/* Плашка формулы */}
          <div
            style={{
              padding: '14px 18px',
              borderRadius: 10,
              background: isDarkMode ? 'rgba(56, 139, 253, 0.12)' : 'rgba(37, 99, 235, 0.06)',
              border: `1px solid ${isDarkMode ? 'rgba(56, 139, 253, 0.28)' : 'rgba(37, 99, 235, 0.18)'}`,
            }}
          >
            <div style={{ fontSize: 13, color: isDarkMode ? '#8b949e' : '#64748b', marginBottom: 6, fontWeight: 600 }}>
              Формула
            </div>
            <div style={{ fontSize: 16, fontWeight: 600, color: isDarkMode ? '#79c0ff' : '#1d4ed8', lineHeight: 1.5 }}>
              {info.formula}
            </div>
          </div>

          {/* Описание */}
          <div>
            <div style={{ fontSize: 13, color: isDarkMode ? '#8b949e' : '#64748b', marginBottom: 6, fontWeight: 600 }}>
              Как рассчитывается
            </div>
            <div style={{ fontSize: 15, color: 'var(--text-color)', lineHeight: 1.6 }}>
              {info.description}
            </div>
          </div>

          {/* Условие */}
          {info.rules && (
            <div>
              <div style={{ fontSize: 13, color: isDarkMode ? '#8b949e' : '#64748b', marginBottom: 6, fontWeight: 600 }}>
                Условие данных
              </div>
              <div style={{ fontSize: 15, color: 'var(--text-color)', lineHeight: 1.6 }}>
                {info.rules}
              </div>
            </div>
          )}
        </div>
      )}
    </Modal>
  );
};

const ExcelFilterSelect = ({ title, allLabel, value, onChange, options = [], isMobile, style }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');

  const allOptionIds = useMemo(() => (options || []).map(o => o.id), [options]);

  const selectedSet = useMemo(() => {
    if (value === null || value === undefined) return new Set(allOptionIds);
    return new Set(value);
  }, [value, allOptionIds]);

  const [tempSelected, setTempSelected] = useState(() => new Set(selectedSet));

  useEffect(() => {
    if (open) {
      setTempSelected(new Set(selectedSet));
      setSearch('');
    }
  }, [open, selectedSet]);

  const filteredOptions = useMemo(() => {
    if (!search.trim()) return options || [];
    const q = search.toLowerCase().trim();
    return (options || []).filter(o => String(o.value || '').toLowerCase().includes(q));
  }, [options, search]);

  const tempIsAll = allOptionIds.length > 0 && tempSelected.size === allOptionIds.length;
  const tempIsIndeterminate = tempSelected.size > 0 && tempSelected.size < allOptionIds.length;

  const handleToggleAll = (e) => {
    if (e.target.checked) {
      setTempSelected(new Set(allOptionIds));
    } else {
      setTempSelected(new Set());
    }
  };

  const handleToggleItem = (id) => {
    setTempSelected(prev => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleApply = () => {
    setOpen(false);
    if (tempSelected.size === 0 || tempSelected.size === allOptionIds.length) {
      onChange(null);
    } else {
      onChange(Array.from(tempSelected));
    }
  };

  const handleReset = () => {
    setTempSelected(new Set(allOptionIds));
    onChange(null);
    setOpen(false);
  };

  const hasFilter = value !== null && value !== undefined && value.length > 0 && value.length < allOptionIds.length;
  let btnText = allLabel || `Все ${title ? title.toLowerCase() : ''}`;

  if (hasFilter) {
    if (value.length === 1) {
      const opt = (options || []).find(o => o.id === value[0]);
      btnText = opt ? opt.value : 'Выбрано: 1';
    } else {
      btnText = `Выбрано: ${value.length}`;
    }
  }

  const activeBorderColor = '#fa541c';
  const defaultBorderColor = isDarkMode ? '#30363d' : '#d9d9d9';
  const defaultBg = isDarkMode ? '#161b22' : '#ffffff';
  const activeBg = isDarkMode ? '#2d1b15' : '#fff7e6';

  const content = (
    <div style={{ width: isMobile ? 220 : 250, padding: 2 }}>
      <div style={{ padding: '4px 6px', fontWeight: 600 }}>
        <Checkbox
          indeterminate={tempIsIndeterminate}
          checked={tempIsAll}
          onChange={handleToggleAll}
          style={{ fontWeight: 600 }}
        >
          {allLabel || `Все ${title ? title.toLowerCase() : ''}`}
        </Checkbox>
      </div>

      {options && options.length > 5 && (
        <Input
          size="small"
          prefix={<SearchOutlined style={{ color: '#888', fontSize: 12 }} />}
          placeholder="Поиск..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          allowClear
          style={{ margin: '6px 0', fontSize: 12 }}
        />
      )}

      <Divider style={{ margin: '4px 0' }} />

      <div style={{ maxHeight: 220, overflowY: 'auto', padding: '2px 4px' }}>
        {filteredOptions.length === 0 ? (
          <div style={{ color: '#888', fontSize: 12, padding: 8, textAlign: 'center' }}>Ничего не найдено</div>
        ) : (
          filteredOptions.map(opt => (
            <div key={opt.id} style={{ padding: '3px 2px' }}>
              <Checkbox
                checked={tempSelected.has(opt.id)}
                onChange={() => handleToggleItem(opt.id)}
                style={{ fontSize: 12 }}
              >
                <span title={opt.value} style={{ wordBreak: 'break-word' }}>{opt.value}</span>
              </Checkbox>
            </div>
          ))
        )}
      </div>

      <Divider style={{ margin: '6px 0 8px 0' }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Button size="small" type="link" onClick={handleReset} style={{ padding: 0, fontSize: 12 }}>
          Сбросить
        </Button>
        <Button size="small" type="primary" onClick={handleApply} style={{ fontSize: 12, borderRadius: 4 }}>
          Применить
        </Button>
      </div>
    </div>
  );

  return (
    <div style={{ display: 'inline-flex', flexDirection: 'column', ...style }}>
      {title && (
        <span style={{
          fontSize: 11,
          fontWeight: 500,
          color: isDarkMode ? '#8b949e' : '#64748b',
          marginBottom: 4,
        }}>
          {title}
        </span>
      )}
      <Popover
        content={content}
        trigger="click"
        open={open}
        onOpenChange={setOpen}
        placement="bottomLeft"
        overlayInnerStyle={{ padding: 10 }}
      >
        <button
          type="button"
          style={{
            height: 28,
            padding: '0 10px',
            borderRadius: 6,
            border: `1px solid ${hasFilter ? activeBorderColor : defaultBorderColor}`,
            background: hasFilter ? activeBg : defaultBg,
            color: hasFilter ? (isDarkMode ? '#ff7a45' : '#d4380d') : 'var(--text-color)',
            fontSize: 12,
            fontWeight: hasFilter ? 600 : 400,
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            gap: 6,
            outline: 'none',
            maxWidth: isMobile ? 140 : 180,
            transition: 'border-color 0.15s ease, background-color 0.15s ease',
          }}
        >
          <span style={{
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}>
            {btnText}
          </span>
          <DownOutlined style={{ fontSize: 9, opacity: 0.7 }} />
        </button>
      </Popover>
    </div>
  );
};

const getHeatmapBg = (val, maxVal, isDarkMode) => {
  if (!val || val <= 0) {
    return isDarkMode ? 'transparent' : '#ffffff';
  }
  const max = Math.max(maxVal || 1, 10);
  const t = Math.min(1.0, Math.max(0.0, val / max));
  const factor = Math.pow(t, 0.65);

  if (isDarkMode) {
    const r = Math.round(40 + factor * 170);
    const g = Math.round(35 + factor * 105);
    const b = 20;
    const a = (0.15 + factor * 0.7).toFixed(2);
    return `rgba(${r}, ${g}, ${b}, ${a})`;
  } else {
    const r = 255;
    const g = Math.round(255 - factor * 85);
    const b = Math.round(255 - factor * 215);
    return `rgb(${r}, ${g}, ${b})`;
  }
};

const RecruiterLoadCard = ({
  matrix = [],
  totals = {},
  barData = [],
  isMobile,
  onFormulaClick,
  onExportExcel,
  exportLoading,
}) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const [viewMode, setViewMode] = useState('table');

  const maxTotal = totals?.total_open || 100;

  const columns = [
    {
      title: 'рекрутер',
      dataIndex: 'recruiter',
      key: 'recruiter',
      width: isMobile ? 120 : 160,
      fixed: isMobile ? 'left' : false,
      render: (text) => <span style={{ fontWeight: 600 }}>{text}</span>,
    },
    {
      title: 'Выход',
      dataIndex: 'exit',
      key: 'exit',
      align: 'center',
      width: 70,
      render: (v) => v || '',
    },
    {
      title: 'Открыта',
      dataIndex: 'open',
      key: 'open',
      align: 'center',
      width: 80,
      render: (v) => v || '',
    },
    {
      title: 'Оффер',
      dataIndex: 'offer',
      key: 'offer',
      align: 'center',
      width: 70,
      render: (v) => v || '',
    },
    {
      title: 'Подготовка документов',
      dataIndex: 'docs_prep',
      key: 'docs_prep',
      align: 'center',
      width: 100,
      render: (v) => v || '',
    },
    {
      title: 'Проверка СБ',
      dataIndex: 'security_check',
      key: 'security_check',
      align: 'center',
      width: 95,
      render: (v) => v || '',
    },
    {
      title: 'Согласование фин условий',
      dataIndex: 'fin_approval',
      key: 'fin_approval',
      align: 'center',
      width: 110,
      render: (v) => v || '',
    },
    {
      title: 'Новые вакансии за текущую отчетную неделю',
      dataIndex: 'new_this_week',
      key: 'new_this_week',
      align: 'center',
      width: 130,
      render: (v) => v || '',
    },
    {
      title: 'Всего открыто на сегодня',
      dataIndex: 'total_open',
      key: 'total_open',
      align: 'center',
      width: 110,
      render: (v) => <span style={{ fontWeight: 700, color: '#000000' }}>{v}</span>,
      onCell: (record) => {
        const val = record?.total_open || 0;
        return {
          style: {
            background: getHeatmapBg(val, maxTotal, isDarkMode),
            fontWeight: 700,
          },
        };
      },
    },
  ];

  return (
    <Card
      style={CS}
      bodyStyle={{ padding: '14px 18px' }}
      headStyle={CHS}
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <TeamOutlined style={{ color: T.purple }} />
          <span>Загрузка рекрутеров</span>
        </div>
      }
      extra={
        <Space size={8} wrap>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={onExportExcel}
            loading={exportLoading}
            style={{ borderRadius: 6, fontSize: 12, fontWeight: 500 }}
          >
            Экспорт в Excel
          </Button>
          <Radio.Group
            size="small"
            value={viewMode}
            onChange={e => setViewMode(e.target.value)}
            buttonStyle="solid"
          >
            <Radio.Button value="table">Таблица</Radio.Button>
            <Radio.Button value="chart">График</Radio.Button>
          </Radio.Group>
          <FormulaButton chartKey="recruiter_load" onOpen={onFormulaClick} isMobile={isMobile} />
        </Space>
      }
    >
      {viewMode === 'table' ? (
        !matrix.length ? (
          <NoData text="Нет активных вакансий в работе у рекрутеров" />
        ) : (
          <div>
            <div style={{
              background: isDarkMode ? '#113565' : '#1677ff',
              color: '#ffffff',
              fontWeight: 600,
              fontSize: 16,
              textAlign: 'center',
              padding: '12px 16px',
              borderRadius: '6px 6px 0 0',
              letterSpacing: 0,
            }}>
              Всего активных вакансий в работе у рекрутера
            </div>
            <Table
              size="small"
              bordered
              pagination={false}
              columns={columns}
              dataSource={matrix.map((r, i) => ({ ...r, key: r.recruiter || i }))}
              scroll={{ x: 'max-content' }}
              summary={() => (
                <Table.Summary fixed>
                  <Table.Summary.Row style={{
                    background: isDarkMode ? '#262930' : '#f8f9fa',
                    fontWeight: 700,
                    borderTop: '2px solid #595959',
                  }}>
                    <Table.Summary.Cell index={0}><Text strong>Итого</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={1} align="center"><Text strong>{totals?.exit || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={2} align="center"><Text strong>{totals?.open || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={3} align="center"><Text strong>{totals?.offer || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={4} align="center"><Text strong>{totals?.docs_prep || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={5} align="center"><Text strong>{totals?.security_check || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={6} align="center"><Text strong>{totals?.fin_approval || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell index={7} align="center"><Text strong>{totals?.new_this_week || ''}</Text></Table.Summary.Cell>
                    <Table.Summary.Cell
                      index={8}
                      align="center"
                      style={{
                        background: getHeatmapBg(totals?.total_open || 0, maxTotal, isDarkMode),
                        borderBottom: '3px double #000',
                      }}
                    >
                      <Text strong style={{ fontSize: 13, color: '#000000' }}>
                        {totals?.total_open || 0}
                      </Text>
                    </Table.Summary.Cell>
                  </Table.Summary.Row>
                </Table.Summary>
              )}
            />
          </div>
        )
      ) : (
        !barData.length ? (
          <NoData text="Нет данных — возможно не заполнен рекрутер у вакансий" />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(200, barData.length * 42 + 20)}>
            <BarChart
              data={barData}
              layout="vertical"
              barSize={18}
              margin={{ top: 4, right: isMobile ? 16 : 64, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" axisLine={false} tickLine={false}
                style={{ fontSize: FS_AXIS_NUM, fill: T.muted }}
                domain={[0, dataMax => Math.round((barData[0]?.value || dataMax) * 1.2)]} />
              <YAxis type="category" dataKey="recruiter" width={isMobile ? 100 : 175}
                axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <RTooltip
                cursor={{ fill: 'rgba(128,128,128,0.15)' }}
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  return (
                    <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                      <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>
                      <div style={{ color: T.sub }}>Вакансий: <b style={{ color: T.purple }}>{payload[0].value}</b></div>
                    </div>
                  );
                }}
              />
              <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                {barData.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                <LabelList dataKey="value" position="right"
                  style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )
      )}
    </Card>
  );
};

const IvakhinStatusesCard = ({
  monthsData = [],
  isMobile,
  onFormulaClick,
  onExportExcel,
  exportLoading,
}) => {
  const { isDarkMode } = React.useContext(ThemeContext);

  const tableData = useMemo(() => {
    return (monthsData || []).map((m) => ({
      key: m.id,
      month: m.month,
      block: '',
      open: m.open,
      closed: m.closed,
      hold: m.hold,
      cancel: m.cancel,
      total: m.total,
      isMonthSummary: true,
      children: (m.blocks || []).map((b) => ({
        key: b.id,
        month: m.month,
        block: b.block,
        open: b.open,
        closed: b.closed,
        hold: b.hold,
        cancel: b.cancel,
        total: b.total,
        isMonthSummary: false,
      })),
    }));
  }, [monthsData]);

  const allKeys = useMemo(() => tableData.map((d) => d.key), [tableData]);
  const [expandedRowKeys, setExpandedRowKeys] = useState([]);

  useEffect(() => {
    if (allKeys.length && !expandedRowKeys.length) {
      setExpandedRowKeys(allKeys);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allKeys]);

  const handleExpandAll = () => setExpandedRowKeys(allKeys);
  const handleCollapseAll = () => setExpandedRowKeys([]);

  const columns = [
    {
      title: 'Месяц',
      dataIndex: 'month',
      key: 'month',
      width: isMobile ? 100 : 130,
      render: (text, record) => {
        if (record.isMonthSummary) {
          return <span style={{ fontWeight: 700, color: '#1677ff' }}>{text}</span>;
        }
        return <span style={{ color: '#8c8c8c' }}>{text}</span>;
      },
    },
    {
      title: 'Ит Блок',
      dataIndex: 'block',
      key: 'block',
      width: isMobile ? 140 : 200,
      ellipsis: true,
      render: (text, record) => {
        if (record.isMonthSummary) {
          return <span style={{ fontWeight: 600, color: '#8c8c8c', fontStyle: 'italic' }}>Итого</span>;
        }
        return <span style={{ fontWeight: 500 }}>{text}</span>;
      },
    },
    {
      title: 'Открыто',
      dataIndex: 'open',
      key: 'open',
      width: 78,
      align: 'right',
      render: (val, record) => (
        <span style={{ fontWeight: record.isMonthSummary ? 700 : 400, color: '#1677ff' }}>
          {val}
        </span>
      ),
    },
    {
      title: 'Закрыто',
      dataIndex: 'closed',
      key: 'closed',
      width: 78,
      align: 'right',
      render: (val, record) => (
        <span style={{ fontWeight: record.isMonthSummary ? 700 : 400, color: '#16a34a' }}>
          {val}
        </span>
      ),
    },
    {
      title: 'Hold',
      dataIndex: 'hold',
      key: 'hold',
      width: 70,
      align: 'right',
      render: (val, record) => (
        <span style={{ fontWeight: record.isMonthSummary ? 700 : 400, color: '#d97706' }}>
          {val}
        </span>
      ),
    },
    {
      title: 'Отмена',
      dataIndex: 'cancel',
      key: 'cancel',
      width: 72,
      align: 'right',
      render: (val, record) => (
        <span style={{ fontWeight: record.isMonthSummary ? 700 : 400, color: '#dc2626' }}>
          {val}
        </span>
      ),
    },
    {
      title: 'Всего вакансий',
      dataIndex: 'total',
      key: 'total',
      width: 115,
      align: 'right',
      render: (val) => (
        <span style={{ fontWeight: 700 }}>
          {val}
        </span>
      ),
    },
  ];

  return (
    <Card
      style={CS}
      bodyStyle={{ ...CBS, padding: '12px 16px' }}
      headStyle={CHS}
      title={
        <Space size={8}>
          <TableOutlined style={{ color: T.blue }} />
          <span>Вакансии по статусам для Ивахина А</span>
        </Space>
      }
      extra={
        <Space size={8}>
          <Space size={4} style={{ marginRight: 6 }}>
            <Button size="small" type="link" onClick={handleExpandAll} style={{ padding: '0 4px', fontSize: 12 }}>
              Развернуть всё
            </Button>
            <span style={{ color: '#8c8c8c' }}>|</span>
            <Button size="small" type="link" onClick={handleCollapseAll} style={{ padding: '0 4px', fontSize: 12 }}>
              Свернуть всё
            </Button>
          </Space>
          <Button
            size="small"
            icon={<DownloadOutlined />}
            onClick={onExportExcel}
            loading={exportLoading}
            style={{ borderRadius: 6, fontSize: 12, fontWeight: 500 }}
          >
            Экспорт в Excel
          </Button>
          <FormulaButton chartKey="statuses_ivakhin" onOpen={onFormulaClick} isMobile={isMobile} />
        </Space>
      }
    >
      {!tableData.length ? (
        <NoData text="Нет данных по статусам" />
      ) : (
        <Table
          columns={columns}
          dataSource={tableData}
          rowKey="key"
          size="small"
          bordered
          pagination={false}
          scroll={{ x: 740, y: 380 }}
          expandedRowKeys={expandedRowKeys}
          onExpandedRowsChange={setExpandedRowKeys}
          onRow={(record) => ({
            style: record.isMonthSummary
              ? {
                  backgroundColor: isDarkMode ? 'rgba(56, 139, 253, 0.12)' : '#f0f5ff',
                }
              : {},
          })}
        />
      )}
    </Card>
  );
};

const PieTip = ({ active, payload }) => {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
      <div style={{ fontWeight: 600, marginBottom: 3 }}>{d.name || d.status}</div>
      <div style={{ color: T.sub }}>Кол-во: <b style={{ color: T.text }}>{d.value}</b></div>
      <div style={{ color: T.sub }}>Доля: <b style={{ color: T.blue }}>{d.pct}%</b></div>
    </div>
  );
};

const BarTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
      <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: T.sub }}>{p.name}: <b style={{ color: p.fill || T.blue }}>{p.value}</b></div>
      ))}
    </div>
  );
};

const NoData = ({ text = 'Нет данных' }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 220 }}>
    <Text type="secondary" style={{ fontSize: 12 }}>{text}</Text>
  </div>
);

const renderPieLabel = (props) => {
  const { cx, cy, midAngle, outerRadius, payload, percent } = props;
  const RADIAN = Math.PI / 180;
  const sin = Math.sin(-RADIAN * midAngle);
  const cos = Math.cos(-RADIAN * midAngle);

  // Start just outside slice boundary
  const sx = cx + (outerRadius + 3) * cos;
  const sy = cy + (outerRadius + 3) * sin;

  // Diagonal elbow
  const mx = cx + (outerRadius + 14) * cos;
  const my = cy + (outerRadius + 14) * sin;

  // Horizontal line tip
  const isRight = cos >= 0;
  const ex = mx + (isRight ? 1 : -1) * 12;
  const ey = my;

  // Clean 6px margin between pointer tip and number
  const tx = ex + (isRight ? 1 : -1) * 6;
  const ty = ey;

  const pctVal = payload?.pct !== undefined
    ? payload.pct
    : Math.round((percent || 0) * 1000) / 10;
  const labelText = `${pctVal}%`;

  return (
    <g>
      <path
        d={`M${sx},${sy}L${mx},${my}L${ex},${ey}`}
        stroke="#8c8c8c"
        fill="none"
        strokeWidth={1.2}
      />
      <text
        x={tx}
        y={ty}
        fill={T.text}
        fontSize={11}
        fontWeight={600}
        textAnchor={isRight ? 'start' : 'end'}
        dominantBaseline="central"
      >
        {labelText}
      </text>
    </g>
  );
};

const SalaryCard = ({ data, isMobile, onFormulaClick }) => {
  const p50 = data?.p50 || 0;
  const p25 = data?.p25 || 0;
  const p75 = data?.p75 || 0;
  const hasData = p50 > 0 || p25 > 0 || p75 > 0;

  return (
    <Card
      style={CS}
      bodyStyle={{ padding: isMobile ? '16px 16px' : '18px 28px' }}
      headStyle={CHS}
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <DollarOutlined style={{ marginRight: 8, color: T.purple, fontSize: 16 }} />
            <span>Медианная ЗП (Gross)</span>
          </div>
          <FormulaButton chartKey="salaries" onOpen={onFormulaClick} isMobile={isMobile} />
        </div>
      }
    >
      {!hasData ? (
        <NoData text="Нет данных по зарплатам для выбранных фильтров" />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 16 : 48, flexWrap: 'wrap' }}>
            <Statistic
              title={<Text style={{ fontSize: 13, color: T.muted, fontWeight: 500 }}>Медианная ЗП (Gross)</Text>}
              value={p50}
              valueStyle={{ fontSize: isMobile ? 22 : 28, fontWeight: 600, color: T.purple, fontVariantNumeric: 'tabular-nums' }}
              suffix=" ₽"
            />
            {!isMobile && <Divider type="vertical" style={{ height: 48, margin: 0 }} />}
            <Statistic
              title={<Text style={{ fontSize: 13, color: T.muted, fontWeight: 500 }}>Q1 (25%)</Text>}
              value={p25}
              valueStyle={{ fontSize: isMobile ? 18 : 22, fontWeight: 600, color: T.sub, fontVariantNumeric: 'tabular-nums' }}
              suffix=" ₽"
            />
            {!isMobile && <Divider type="vertical" style={{ height: 48, margin: 0 }} />}
            <Statistic
              title={<Text style={{ fontSize: 13, color: T.muted, fontWeight: 500 }}>Q3 (75%)</Text>}
              value={p75}
              valueStyle={{ fontSize: isMobile ? 18 : 22, fontWeight: 600, color: T.sub, fontVariantNumeric: 'tabular-nums' }}
              suffix=" ₽"
            />
          </div>
          <div style={{ marginTop: 8, borderTop: `1px solid ${T.border}`, paddingTop: 6 }}>
            <Text style={{ fontSize: 11, color: T.muted }}>
              * Данные на основе сделанных офферов
            </Text>
          </div>
        </div>
      )}
    </Card>
  );
};

const DonutCard = ({ title, icon, data, color, chartKey, onFormulaClick, isMobile }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const strokeColor = isDarkMode ? '#161b22' : '#ffffff';
  return (
    <Card
      style={CS}
      bodyStyle={{ padding: '16px 24px' }}
      headStyle={CHS}
      title={
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <span style={{ marginRight: 8, color }}>{icon}</span>
            <span>{title}</span>
          </div>
          <FormulaButton chartKey={chartKey} onOpen={onFormulaClick} isMobile={isMobile} />
        </div>
      }
    >
      {!data?.length ? <NoData /> : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14 }}>
          <div style={{ width: '100%', height: 215 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name"
                  cx="50%" cy="50%" outerRadius={50}
                  labelLine={false} label={renderPieLabel}>
                  {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} stroke={strokeColor} strokeWidth={2} />)}
                </Pie>
                <RTooltip content={<PieTip />} />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12, justifyContent: 'center' }}>
            {data.map((item, i) => (
              <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <span style={{
                  display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
                  background: PALETTE[i % PALETTE.length], flexShrink: 0
                }} />
                <span style={{ fontSize: FS_LEGEND, color: T.sub, fontWeight: 500 }}>
                  {item.name}
                </span>
                <span style={{ fontSize: FS_BAR_VAL, fontWeight: 700, color: T.text }}>
                  {item.pct}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  );
};

const ConversionDot = ({ cx, cy, payload, maxVal, minVal, hasDiff, isDarkMode }) => {
  if (cx == null || cy == null || !payload) return null;
  const isMax = hasDiff && payload.value === maxVal;
  const isMin = hasDiff && payload.value === minVal;
  const green = isDarkMode ? '#3fb950' : '#16a34a';
  const red   = isDarkMode ? '#f85149' : '#dc2626';
  const blue  = isDarkMode ? '#4096ff' : '#1677ff';
  const color = isMax ? green : isMin ? red : blue;
  const r = (isMax || isMin) ? 6 : 4;

  const yPos = cy < 20 ? cy + 18 : cy - 10;

  return (
    <g key={`dot-${payload.label || payload.name}`}>
      <circle cx={cx} cy={cy} r={r} fill={color} stroke={color} strokeWidth={2} />
      <text
        x={cx}
        y={yPos}
        textAnchor="middle"
        fill={color}
        fontSize={FS_BAR_VAL}
        fontWeight={isMax || isMin ? 700 : 500}
      >
        {`${payload.value}%`}
      </text>
    </g>
  );
};

const JOConversionCard = ({ data, isMobile, onFormulaClick }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const [mode, setMode] = useState('month');

  const green = isDarkMode ? '#3fb950' : '#16a34a';
  const red   = isDarkMode ? '#f85149' : '#dc2626';
  const blue  = isDarkMode ? '#4096ff' : '#1677ff';
  const gridColor = isDarkMode ? '#2c3038' : '#e5e7eb';

  const list = data?.[mode] || [];
  const values = list.map(d => d.value);
  const maxVal = values.length ? Math.max(...values) : 0;
  const minVal = values.length ? Math.min(...values) : 0;
  const hasDiff = list.length > 1 && maxVal !== minVal;

  const maxItems = hasDiff ? list.filter(d => d.value === maxVal).map(d => d.name || d.label).join(', ') : '';
  const minItems = hasDiff ? list.filter(d => d.value === minVal).map(d => d.name || d.label).join(', ') : '';

  let statsText = null;
  if (!list.length) {
    statsText = <Text type="secondary" style={{ fontSize: 13 }}>Нет данных за выбранный период</Text>;
  } else if (!hasDiff) {
    statsText = (
      <span style={{ fontSize: 13, color: T.sub }}>
        Среднее за период: <b style={{ color: T.text }}>{list[0]?.value ?? 0}%</b>
      </span>
    );
  } else {
    statsText = (
      <span style={{ fontSize: 13, color: T.sub }}>
        Макс <b style={{ color: green }}>{maxVal}%</b> {maxItems ? `(${maxItems})` : ''} · Мин <b style={{ color: red }}>{minVal}%</b> {minItems ? `(${minItems})` : ''}
      </span>
    );
  }

  let yDomain = [0, 100];
  if (mode !== 'year' && hasDiff) {
    const floorMin = Math.max(0, Math.floor((minVal - 6) / 5) * 5);
    const ceilMax = Math.min(100, Math.ceil((maxVal + 6) / 5) * 5);
    yDomain = [floorMin, ceilMax];
  }

  return (
    <Card
      style={CS}
      bodyStyle={{ padding: '14px 20px' }}
      headStyle={CHS}
      title={<><RiseOutlined style={{ marginRight: 8, color: blue }} />Конверсия принятия JO</>}
      extra={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Radio.Group size="small" value={mode} onChange={e => setMode(e.target.value)} buttonStyle="solid">
            <Radio.Button value="month">Месяц</Radio.Button>
            <Radio.Button value="quarter">Квартал</Radio.Button>
            <Radio.Button value="year">Год</Radio.Button>
          </Radio.Group>
          <FormulaButton chartKey="jo_conversion" onOpen={onFormulaClick} isMobile={isMobile} />
        </div>
      }
    >
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 13 }}>{statsText}</div>
      </div>

      {!list.length ? (
        <NoData text="Нет данных по конверсии JO" />
      ) : mode === 'year' ? (
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={list} barSize={64} margin={{ top: 24, right: 24, bottom: 8, left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <YAxis domain={[0, 100]} width={isMobile ? 42 : 50} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <RTooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                      <div style={{ fontWeight: 600, marginBottom: 3, color: T.text }}>{d.name || d.label}</div>
                      <div style={{ color: T.sub }}>Конверсия: <b style={{ color: blue }}>{d.value}%</b></div>
                      <div style={{ color: T.sub }}>Закрыто: <b style={{ color: T.text }}>{d.closed}</b></div>
                      <div style={{ color: T.sub }}>Офферов: <b style={{ color: T.text }}>{d.offers}</b></div>
                    </div>
                  );
                }}
              />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {list.map((entry, idx) => {
                  const isMax = hasDiff && entry.value === maxVal;
                  const isMin = hasDiff && entry.value === minVal;
                  const col = isMax ? green : isMin ? red : blue;
                  return <BCell key={idx} fill={col} />;
                })}
                <LabelList dataKey="value" position="top" formatter={v => `${v}%`} style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div style={{ width: '100%', height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={list} margin={{ top: 24, right: isMobile ? 24 : 36, bottom: 8, left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} padding={{ left: 36, right: 36 }} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <YAxis domain={yDomain} width={isMobile ? 42 : 50} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <RTooltip
                content={({ active, payload }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                      <div style={{ fontWeight: 600, marginBottom: 3, color: T.text }}>{d.name || d.label}</div>
                      <div style={{ color: T.sub }}>Конверсия: <b style={{ color: blue }}>{d.value}%</b></div>
                      <div style={{ color: T.sub }}>Закрыто: <b style={{ color: T.text }}>{d.closed}</b></div>
                      <div style={{ color: T.sub }}>Офферов: <b style={{ color: T.text }}>{d.offers}</b></div>
                    </div>
                  );
                }}
              />
              <Line
                type="monotone"
                dataKey="value"
                stroke={blue}
                strokeWidth={2}
                dot={(props) => (
                  <ConversionDot
                    key={`dot-${props.index}`}
                    {...props}
                    maxVal={maxVal}
                    minVal={minVal}
                    hasDiff={hasDiff}
                    isDarkMode={isDarkMode}
                  />
                )}
                activeDot={{ r: 8 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, flexWrap: 'wrap', gap: 8, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
        <div style={{ display: 'flex', gap: 14, fontSize: FS_LEGEND, color: T.sub, alignItems: 'center' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <i style={{ width: 10, height: 10, borderRadius: '50%', background: green, display: 'inline-block' }} />
            Максимум
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <i style={{ width: 10, height: 10, borderRadius: '50%', background: red, display: 'inline-block' }} />
            Минимум
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <i style={{ width: 10, height: 10, borderRadius: '50%', background: blue, display: 'inline-block' }} />
            Остальные
          </span>
        </div>
      </div>
    </Card>
  );
};

const AvgDaysDot = ({ cx, cy, payload, maxVal, minVal, hasDiff, isDarkMode }) => {
  if (cx == null || cy == null || !payload) return null;
  const isBest = hasDiff && payload.value === minVal;
  const isWorst = hasDiff && payload.value === maxVal;
  const green = isDarkMode ? '#3fb950' : '#16a34a';
  const red   = isDarkMode ? '#f85149' : '#dc2626';
  const blue  = isDarkMode ? '#4096ff' : '#1677ff';
  const color = isBest ? green : isWorst ? red : blue;
  const r = (isBest || isWorst) ? 6 : 4;

  const yPos = cy < 20 ? cy + 18 : cy - 10;

  return (
    <g key={`dot-avg-${payload.label || payload.name}`}>
      <circle cx={cx} cy={cy} r={r} fill={color} stroke={color} strokeWidth={2} />
      <text
        x={cx}
        y={yPos}
        textAnchor="middle"
        fill={color}
        fontSize={FS_BAR_VAL}
        fontWeight={isBest || isWorst ? 700 : 500}
      >
        {`${payload.value}`}
      </text>
    </g>
  );
};

const AvgDaysTimelineCard = ({ data, isMobile, onFormulaClick }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const [mode, setMode] = useState('month');

  const green = isDarkMode ? '#3fb950' : '#16a34a';
  const red   = isDarkMode ? '#f85149' : '#dc2626';
  const blue  = isDarkMode ? '#4096ff' : '#1677ff';
  const amber = isDarkMode ? '#f59e0b' : '#d97706';
  const gridColor = isDarkMode ? '#2c3038' : '#e5e7eb';

  const list = (data?.[mode] || []).filter(d => d.value > 0 || d.count > 0);
  const values = list.map(d => d.value);
  const maxVal = values.length ? Math.max(...values) : 0;
  const minVal = values.length ? Math.min(...values) : 0;
  const hasDiff = list.length > 1 && maxVal !== minVal;

  const dyn = (arr, i) => {
    if (i < 1) return null;
    const prev = arr[i - 1].value;
    const curr = arr[i].value;
    if (!prev) return null;
    const x = curr - prev;
    return {
      abs: Math.round(x * 10) / 10,
      pct: Math.round((x / prev) * 1000) / 10,
    };
  };

  const lastIdx = list.length - 1;
  const lastItem = list[lastIdx];
  const lastDyn = dyn(list, lastIdx);

  const bestItem = hasDiff ? list.find(d => d.value === minVal) : null;
  const worstItem = hasDiff ? list.find(d => d.value === maxVal) : null;

  let yDomain = ['auto', 'auto'];
  if (values.length) {
    if (mode === 'year') {
      yDomain = [0, Math.ceil((maxVal + 15) / 10) * 10];
    } else {
      const floorMin = Math.max(0, Math.floor((minVal - 8) / 5) * 5);
      const ceilMax = Math.ceil((maxVal + 8) / 5) * 5;
      yDomain = [floorMin, ceilMax];
    }
  }

  const kpiTileStyle = {
    background: isDarkMode ? '#1e222b' : '#f8fafc',
    border: `1px solid ${T.border}`,
    borderRadius: 10,
    padding: '10px 14px',
    display: 'flex',
    flexDirection: 'column',
    justifyContent: 'center',
  };

  return (
    <Card
      style={CS}
      bodyStyle={{ padding: '14px 20px' }}
      headStyle={CHS}
      title={<><FieldTimeOutlined style={{ marginRight: 8, color: amber }} />Динамика среднего срока закрытия (раб. дни)</>}
      extra={
        <div style={{ display: 'flex', alignItems: 'center' }}>
          <Radio.Group size="small" value={mode} onChange={e => setMode(e.target.value)} buttonStyle="solid">
            <Radio.Button value="month">Месяц</Radio.Button>
            <Radio.Button value="quarter">Квартал</Radio.Button>
            <Radio.Button value="year">Год</Radio.Button>
          </Radio.Group>
          <FormulaButton chartKey="avg_days_timeline" onOpen={onFormulaClick} isMobile={isMobile} />
        </div>
      }
    >
      {/* 4 KPI cards matching Средний срок закрытия вакансии.html */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: isMobile ? '1fr 1fr' : 'repeat(4, 1fr)',
        gap: 10,
        marginBottom: 16
      }}>
        {/* KPI 1: Последний период */}
        <div style={kpiTileStyle}>
          <div style={{ fontSize: 12, color: T.muted, marginBottom: 2 }}>Последний период</div>
          <div style={{ fontSize: 19, fontWeight: 700, color: T.text }}>
            {lastItem ? `${lastItem.value} р.д.` : '—'}
          </div>
          <div style={{ fontSize: 12, color: T.muted }}>
            {lastItem ? (lastItem.name || lastItem.label) : ''}
          </div>
        </div>

        {/* KPI 2: Динамика к пред. периоду */}
        <div style={kpiTileStyle}>
          <div style={{ fontSize: 12, color: T.muted, marginBottom: 2 }}>Динамика к пред. периоду</div>
          <div style={{
            fontSize: 19,
            fontWeight: 700,
            color: !lastDyn ? T.text : (lastDyn.abs < 0 ? green : lastDyn.abs > 0 ? red : T.text)
          }}>
            {lastDyn ? (
              <>
                {lastDyn.abs < 0 ? '▼ ' : lastDyn.abs > 0 ? '▲ +' : ''}
                {lastDyn.abs < 0 ? lastDyn.abs : lastDyn.abs > 0 ? lastDyn.abs : 0} р.д.
              </>
            ) : '—'}
          </div>
          <div style={{ fontSize: 12, color: T.muted }}>
            {lastDyn ? `${lastDyn.pct > 0 ? '+' : ''}${lastDyn.pct}%` : 'нет предыдущего'}
          </div>
        </div>

        {/* KPI 3: Лучший (мин.) */}
        <div style={kpiTileStyle}>
          <div style={{ fontSize: 12, color: T.muted, marginBottom: 2 }}>Лучший (мин.)</div>
          <div style={{ fontSize: 19, fontWeight: 700, color: green }}>
            {bestItem ? `${bestItem.value} р.д.` : (list.length === 1 ? `${list[0].value} р.д.` : '—')}
          </div>
          <div style={{ fontSize: 12, color: T.muted }}>
            {bestItem ? (bestItem.name || bestItem.label) : (list.length === 1 ? (list[0].name || list[0].label) : '')}
          </div>
        </div>

        {/* KPI 4: Худший (макс.) */}
        <div style={kpiTileStyle}>
          <div style={{ fontSize: 12, color: T.muted, marginBottom: 2 }}>Худший (макс.)</div>
          <div style={{ fontSize: 19, fontWeight: 700, color: red }}>
            {worstItem ? `${worstItem.value} р.д.` : (list.length === 1 ? `${list[0].value} р.д.` : '—')}
          </div>
          <div style={{ fontSize: 12, color: T.muted }}>
            {worstItem ? (worstItem.name || worstItem.label) : (list.length === 1 ? (list[0].name || list[0].label) : '')}
          </div>
        </div>
      </div>

      {!list.length ? (
        <NoData text="Нет данных по срокам закрытия вакансий" />
      ) : (
        <div style={{ position: 'relative' }}>
          <ResponsiveContainer width="100%" height={240}>
            {mode === 'year' ? (
              <BarChart data={list} barSize={54} margin={{ top: 22, right: 24, bottom: 4, left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
                <YAxis domain={yDomain} width={isMobile ? 40 : 48} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
                <RTooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    return (
                      <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.name || label}</div>
                        <div style={{ color: T.sub }}>Средний срок: <b style={{ color: amber }}>{d.value} р.д.</b></div>
                        <div style={{ color: T.sub }}>Закрыто вакансий: <b>{d.count}</b></div>
                      </div>
                    );
                  }}
                />
                <Bar dataKey="value" fill={amber} radius={[6, 6, 0, 0]}>
                  <LabelList dataKey="value" position="top" formatter={v => `${v} р.д.`} style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
                </Bar>
              </BarChart>
            ) : (
              <LineChart data={list} margin={{ top: 24, right: 24, bottom: 18, left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} dy={6} padding={{ left: 36, right: 36 }} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
                <YAxis domain={yDomain} width={isMobile ? 40 : 48} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
                <RTooltip
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.length) return null;
                    const d = payload[0].payload;
                    const idx = list.findIndex(item => item.label === d.label);
                    const dy = dyn(list, idx);
                    return (
                      <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                        <div style={{ fontWeight: 600, marginBottom: 4 }}>{d.name || label}</div>
                        <div style={{ color: T.sub }}>Средний срок: <b style={{ color: amber }}>{d.value} р.д.</b></div>
                        <div style={{ color: T.sub }}>Закрыто вакансий: <b>{d.count}</b></div>
                        {dy && (
                          <div style={{ color: dy.abs < 0 ? green : dy.abs > 0 ? red : T.sub, marginTop: 4 }}>
                            К предыдущему: <b>{dy.abs > 0 ? `+${dy.abs}` : dy.abs} р.д. ({dy.pct > 0 ? `+${dy.pct}` : dy.pct}%)</b>
                          </div>
                        )}
                      </div>
                    );
                  }}
                />
                <Line
                  type="monotone"
                  dataKey="value"
                  stroke={blue}
                  strokeWidth={2}
                  dot={(props) => (
                    <AvgDaysDot
                      key={`dot-avg-${props.index}`}
                      {...props}
                      maxVal={maxVal}
                      minVal={minVal}
                      hasDiff={hasDiff}
                      isDarkMode={isDarkMode}
                    />
                  )}
                  activeDot={{ r: 8 }}
                />
              </LineChart>
            )}
          </ResponsiveContainer>
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 14, flexWrap: 'wrap', gap: 8, borderTop: `1px solid ${T.border}`, paddingTop: 10 }}>
        <div style={{ display: 'flex', gap: 14, fontSize: FS_LEGEND, color: T.sub, alignItems: 'center' }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <i style={{ width: 10, height: 10, borderRadius: '50%', background: green, display: 'inline-block' }} />
            Минимум (лучше)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <i style={{ width: 10, height: 10, borderRadius: '50%', background: red, display: 'inline-block' }} />
            Максимум (хуже)
          </span>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5 }}>
            <i style={{ width: 10, height: 10, borderRadius: '50%', background: blue, display: 'inline-block' }} />
            Остальные
          </span>
        </div>
      </div>
    </Card>
  );
};

const RejectionReasonsCard = ({ data, isMobile, onFormulaClick }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const red = isDarkMode ? '#f85149' : '#dc2626';

  const totalRejections = useMemo(() => (data || []).reduce((acc, d) => acc + (d.value || 0), 0), [data]);

  return (
    <Card
      style={CS}
      bodyStyle={{ padding: '14px 20px' }}
      headStyle={CHS}
      title={<><FileTextOutlined style={{ marginRight: 8, color: red }} />Причины отказа</>}
      extra={<FormulaButton chartKey="rejections" onOpen={onFormulaClick} isMobile={isMobile} />}
    >
      {!data?.length ? (
        <NoData text="Нет зарегистрированных отказов от оффера" />
      ) : (
        <ResponsiveContainer width="100%" height={Math.max(260, data.length * 40 + 30)}>
          <BarChart data={data} layout="vertical" barSize={22} margin={{ top: 8, right: isMobile ? 36 : 85, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={isDarkMode ? '#2c3038' : '#f0f0f0'} />
            <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} allowDecimals={false} />
            <YAxis type="category" dataKey="reason" width={isMobile ? 110 : 170} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
            <RTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                const d = payload[0].payload || {};
                const val = payload[0].value;
                const pct = d.pct !== undefined ? d.pct : (totalRejections ? Math.round((val / totalRejections) * 1000) / 10 : 0);
                return (
                  <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                    <div style={{ fontWeight: 600, marginBottom: 3, color: T.text }}>{label}</div>
                    <div style={{ color: T.sub }}>Количество отказов: <b style={{ color: red }}>{val} ({pct}%)</b></div>
                  </div>
                );
              }}
            />
            <Bar dataKey="value" radius={[0, 5, 5, 0]}>
              {data.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              <LabelList
                dataKey="value"
                position="right"
                formatter={(val, entry) => {
                  const d = entry?.payload || {};
                  const pct = d.pct !== undefined ? d.pct : (totalRejections ? Math.round((val / totalRejections) * 1000) / 10 : 0);
                  return `${val} (${pct}%)`;
                }}
                style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}
    </Card>
  );
};

const DASHBOARDS_FILTERS_KEY = 'rms_dashboards_filters';

const loadSavedDashboardsFilters = () => {
  try {
    const s = sessionStorage.getItem(DASHBOARDS_FILTERS_KEY);
    return s ? JSON.parse(s) : null;
  } catch { return null; }
};

const saveSavedDashboardsFilters = (filters) => {
  try {
    if (!filters) {
      sessionStorage.removeItem(DASHBOARDS_FILTERS_KEY);
    } else {
      sessionStorage.setItem(DASHBOARDS_FILTERS_KEY, JSON.stringify(filters));
    }
  } catch {}
};

export default function DashboardsPage() {
  const isMobile = useIsMobile();
  const { isDarkMode } = React.useContext(ThemeContext);
  const savedDashboardsFilters = React.useMemo(() => loadSavedDashboardsFilters(), []);

  const [period,         setPeriod]        = useState(() => {
    if (savedDashboardsFilters?.period && savedDashboardsFilters.period.length === 2) {
      return [dayjs(savedDashboardsFilters.period[0]), dayjs(savedDashboardsFilters.period[1])];
    }
    return null;
  });
  const [itRoleIds,      setItRoleIds]     = useState(() => savedDashboardsFilters?.itRoleIds ?? null);
  const [levelIds,       setLevelIds]      = useState(() => savedDashboardsFilters?.levelIds ?? null);
  const [adminMgrIds,    setAdminMgrIds]   = useState(() => savedDashboardsFilters?.adminMgrIds ?? null);
  const [projectIds,     setProjectIds]    = useState(() => savedDashboardsFilters?.projectIds ?? null);
  const [recruiterIds,   setRecruiterIds]  = useState(() => savedDashboardsFilters?.recruiterIds ?? null);
  const [blockIds,       setBlockIds]      = useState(() => savedDashboardsFilters?.blockIds ?? null);
  const [statusIds,      setStatusIds]     = useState(() => savedDashboardsFilters?.statusIds ?? null);
  const [vacancyIds,     setVacancyIds]    = useState(() => savedDashboardsFilters?.vacancyIds ?? null);
  const [groupBy,        setGroupBy]       = useState(() => savedDashboardsFilters?.groupBy ?? 'it_role');

  const [exportingRecruiterLoad, setExportingRecruiterLoad] = useState(false);
  const [exportingIvakhinStatuses, setExportingIvakhinStatuses] = useState(false);

  // Active formula modal
  const [activeFormulaKey, setActiveFormulaKey] = useState(null);

  // Dashboards tabs
  const [activeTab, setActiveTab] = useState('all');

  // Config mode & layout customization state
  const [isConfigMode, setIsConfigMode] = useState(false);
  const [tabLayouts, setTabLayouts] = useState(() => loadCustomLayouts());
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [dragOverIndex, setDragOverIndex] = useState(null);

  const currentCards = useMemo(() => {
    return tabLayouts[activeTab] || DEFAULT_TAB_LAYOUTS[activeTab] || DEFAULT_TAB_LAYOUTS.all;
  }, [tabLayouts, activeTab]);

  const updateCurrentCards = (newCards) => {
    const newLayouts = {
      ...tabLayouts,
      [activeTab]: newCards,
    };
    setTabLayouts(newLayouts);
    saveCustomLayouts(newLayouts);
  };

  const moveCard = (fromIndex, toIndex) => {
    if (toIndex < 0 || toIndex >= currentCards.length) return;
    const newCards = [...currentCards];
    const [removed] = newCards.splice(fromIndex, 1);
    newCards.splice(toIndex, 0, removed);
    updateCurrentCards(newCards);
  };

  const updateCardSize = (index, newSize) => {
    const newCards = [...currentCards];
    newCards[index] = { ...newCards[index], size: newSize };
    updateCurrentCards(newCards);
  };

  const resetCurrentTabLayout = () => {
    const defaultForTab = DEFAULT_TAB_LAYOUTS[activeTab] || DEFAULT_TAB_LAYOUTS.all;
    const newLayouts = {
      ...tabLayouts,
      [activeTab]: defaultForTab,
    };
    setTabLayouts(newLayouts);
    saveCustomLayouts(newLayouts);
    message.success('Расположение дашбордов сброшено по умолчанию');
  };

  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    try {
      e.dataTransfer.setData('text/plain', String(index));
    } catch {}
  };

  const handleDragOver = (e, index) => {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'move';
    }
    if (dragOverIndex !== index) {
      setDragOverIndex(index);
    }
  };

  const handleDrop = (e, dropIndex) => {
    e.preventDefault();
    if (draggedIndex === null || draggedIndex === undefined) return;
    if (draggedIndex !== dropIndex) {
      moveCard(draggedIndex, dropIndex);
    }
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  React.useEffect(() => {
    saveSavedDashboardsFilters({
      period: period && period[0] && period[1] ? [period[0].toISOString(), period[1].toISOString()] : null,
      itRoleIds,
      levelIds,
      adminMgrIds,
      projectIds,
      recruiterIds,
      blockIds,
      statusIds,
      vacancyIds,
      groupBy,
    });
  }, [period, itRoleIds, levelIds, adminMgrIds, projectIds, recruiterIds, blockIds, statusIds, vacancyIds, groupBy]);

  const buildParams = () => {
    const p = new URLSearchParams();
    if (period?.[0]) p.append('start_date', period[0].format('YYYY-MM-DD'));
    if (period?.[1]) p.append('end_date',   period[1].format('YYYY-MM-DD'));
    if (itRoleIds?.length)    p.append('it_role_ids',       itRoleIds.join(','));
    if (levelIds?.length)     p.append('level_ids',         levelIds.join(','));
    if (adminMgrIds?.length)  p.append('admin_manager_ids', adminMgrIds.join(','));
    if (projectIds?.length)   p.append('project_ids',       projectIds.join(','));
    if (recruiterIds?.length) p.append('recruiter_ids',     recruiterIds.join(','));
    if (blockIds?.length)     p.append('block_ids',         blockIds.join(','));
    if (statusIds?.length)    p.append('status_ids',        statusIds.join(','));
    if (vacancyIds?.length)   p.append('vacancy_ids',       vacancyIds.join(','));
    if (groupBy)              p.append('group_by',          groupBy);
    return p;
  };

  const fetchDashboardData = async () => {
    const params = buildParams();
    params.append('_t', Date.now());
    const res = await api.get(`/dashboards/metrics?${params.toString()}`);
    return res.data;
  };

  const handleExportRecruiterLoad = async () => {
    setExportingRecruiterLoad(true);
    try {
      const params = buildParams();
      const res = await api.get(`/dashboards/export/recruiter-load?${params.toString()}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'recruiter_load.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('Файл успешно выгружен');
    } catch (err) {
      console.error('Export error:', err);
      message.error('Ошибка при выгрузке в Excel');
    } finally {
      setExportingRecruiterLoad(false);
    }
  };

  const handleExportIvakhinStatuses = async () => {
    setExportingIvakhinStatuses(true);
    try {
      const params = buildParams();
      const res = await api.get(`/dashboards/export/ivakhin-statuses?${params.toString()}`, {
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'vacancies_by_status_ivakhin.xlsx');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      message.success('Файл успешно выгружен');
    } catch (err) {
      console.error('Export error:', err);
      message.error('Ошибка при выгрузке в Excel');
    } finally {
      setExportingIvakhinStatuses(false);
    }
  };

  const { data, isLoading, isFetching, refetch } = useQuery({
    queryKey: [
      'dashboards',
      period, itRoleIds, levelIds, adminMgrIds, projectIds, recruiterIds, blockIds, statusIds, vacancyIds, groupBy
    ],
    queryFn: fetchDashboardData,
    keepPreviousData: true,
    refetchOnWindowFocus: true,
  });

  React.useEffect(() => {
    if (!data?.filters) return;
    const clean = (curr, opts, setter) => {
      if (!curr || !curr.length) return;
      const validIds = new Set((opts || []).map(o => o.id));
      const filtered = curr.filter(id => validIds.has(id));
      if (filtered.length !== curr.length) {
        setter(filtered.length ? filtered : null);
      }
    };
    clean(itRoleIds, data.filters.it_roles, setItRoleIds);
    clean(levelIds, data.filters.levels, setLevelIds);
    clean(adminMgrIds, data.filters.admin_managers, setAdminMgrIds);
    clean(projectIds, data.filters.projects, setProjectIds);
    clean(recruiterIds, data.filters.recruiters, setRecruiterIds);
    clean(blockIds, data.filters.blocks, setBlockIds);
    clean(statusIds, data.filters.statuses, setStatusIds);
    clean(vacancyIds, data.filters.vacancies, setVacancyIds);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data?.filters]);

  const clearFilters = () => {
    setPeriod(null);
    setItRoleIds(null);
    setLevelIds(null);
    setAdminMgrIds(null);
    setProjectIds(null);
    setRecruiterIds(null);
    setBlockIds(null);
    setStatusIds(null);
    setVacancyIds(null);
    saveSavedDashboardsFilters(null);
  };

  const f = data?.filters || {};
  const hasFilters = period || itRoleIds || levelIds || adminMgrIds || projectIds || recruiterIds || blockIds || statusIds || vacancyIds;

  const chart1 = data?.chart1_source    || [];
  const chart2 = data?.chart2_open_closed || { total: 0, open: 0, closed: 0, hold: 0, cancel: 0 };
  const chart3 = data?.chart3_funnel    || [];
  const chart4 = data?.chart4_companies || [];
  const chart5 = data?.chart5_avg_days  || [];
  const chart6 = data?.chart6_statuses  || [];
  const chart8 = data?.chart8_recruiter_load || [];
  const recruiterMatrix = data?.recruiter_load_matrix || [];
  const recruiterTotals = data?.recruiter_load_totals || {};
  const chartLevels      = data?.chart_levels      || [];
  const chartReplacement = data?.chart_replacement || [];
  const chartEmployment  = data?.chart_employment  || [];
  const chartRejections  = data?.chart_rejections  || [];
  const chartJoConv      = data?.chart_jo_conversion || { month: [], quarter: [], year: [] };
  const chartAvgDaysTimeline = data?.chart_avg_days_timeline || { month: [], quarter: [], year: [] };
  const chartSalaries    = data?.chart_salaries    || { p25: 0, p50: 0, p75: 0, count: 0 };
  const chartIvakhinStatuses = data?.chart_ivakhin_statuses || [];

  const bar2data = [
    { name: 'Всего',   value: chart2.total,  fill: T.sub   },
    { name: 'Открыта', value: chart2.open,   fill: T.blue  },
    { name: 'Закрыта', value: chart2.closed, fill: T.green },
    { name: 'Hold',    value: chart2.hold,   fill: T.amber },
    { name: 'Отмена',  value: chart2.cancel, fill: T.red   },
  ].filter(d => d.value > 0);

  const DRILL_DOWN_EXCLUDE = new Set(['Закрыта', 'Hold', 'Отмена', 'Всего']);
  const chart6Details = chart6.filter(r => !DRILL_DOWN_EXCLUDE.has(r.status));

  const cardRenderers = {
    salary: () => (
      <SalaryCard
        data={chartSalaries}
        isMobile={isMobile}
        onFormulaClick={setActiveFormulaKey}
      />
    ),
    donut_source: () => (
      <DonutCard 
        title="Источник найма" 
        icon={<PieChartOutlined />} 
        color={T.purple} 
        data={chart1}
        chartKey="source"
        onFormulaClick={setActiveFormulaKey}
        isMobile={isMobile}
      />
    ),
    donut_replacement: () => (
      <DonutCard 
        title="Тип вакансии (Новая/Замена)" 
        icon={<PieChartOutlined />} 
        color={T.amber} 
        data={chartReplacement}
        chartKey="replacement"
        onFormulaClick={setActiveFormulaKey}
        isMobile={isMobile}
      />
    ),
    donut_employment: () => (
      <DonutCard 
        title="Вид занятости" 
        icon={<PieChartOutlined />} 
        color={T.teal} 
        data={chartEmployment}
        chartKey="employment"
        onFormulaClick={setActiveFormulaKey}
        isMobile={isMobile}
      />
    ),
    avg_timeline: () => (
      <AvgDaysTimelineCard
        data={chartAvgDaysTimeline}
        isMobile={isMobile}
        onFormulaClick={setActiveFormulaKey}
      />
    ),
    jo_conversion: () => (
      <JOConversionCard
        data={chartJoConv}
        isMobile={isMobile}
        onFormulaClick={setActiveFormulaKey}
      />
    ),
    recruiter_load: () => (
      <RecruiterLoadCard
        matrix={recruiterMatrix}
        totals={recruiterTotals}
        barData={chart8}
        isMobile={isMobile}
        onFormulaClick={setActiveFormulaKey}
        onExportExcel={handleExportRecruiterLoad}
        exportLoading={exportingRecruiterLoad}
      />
    ),
    ivakhin_statuses: () => (
      <IvakhinStatusesCard
        monthsData={chartIvakhinStatuses}
        isMobile={isMobile}
        onFormulaClick={() => setActiveFormulaKey('statuses_ivakhin')}
        onExportExcel={handleExportIvakhinStatuses}
        exportLoading={exportingIvakhinStatuses}
      />
    ),
    statuses_chart: () => (
      <Card
        style={CS} bodyStyle={CBS} headStyle={CHS}
        title={<><PieChartOutlined style={{ marginRight: 8, color: T.blue }} />Вакансии по статусам</>}
        extra={<FormulaButton chartKey="statuses" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
      >
        {bar2data.length === 0 ? <NoData /> : (
          <ResponsiveContainer width="100%" height={230}>
            <BarChart data={bar2data} barSize={52} margin={{ top: 16, right: 20, bottom: 4, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
              <XAxis dataKey="name" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <YAxis axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <RTooltip content={<BarTip />} cursor={{ fill: 'rgba(128,128,128,0.15)' }} />
              <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                {bar2data.map((b, i) => <BCell key={i} fill={b.fill} />)}
                <LabelList dataKey="value" position="top" style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    ),
    open_details: () => (
      <Card
        style={CS} bodyStyle={CBS} headStyle={CHS}
        title={<><PieChartOutlined style={{ marginRight: 8 }} />Детализация «Открытых» вакансий</>}
        extra={<FormulaButton chartKey="open_details" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
      >
        {!chart6Details.length ? (
          <NoData text="Нет промежуточных статусов" />
        ) : (
          <ResponsiveContainer width="100%" height={Math.max(200, chart6Details.length * 48 + 24)}>
            <BarChart data={chart6Details} layout="vertical" barSize={26}
              margin={{ top: 4, right: isMobile ? 16 : 80, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <YAxis type="category" dataKey="status" width={isMobile ? 100 : 210} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <RTooltip content={<BarTip />} cursor={{ fill: 'rgba(128,128,128,0.15)' }} />
              <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                {chart6Details.map((r, i) => (
                  <BCell key={i} fill={STATUS_COLOR[r.status] || PALETTE[i % PALETTE.length]} />
                ))}
                <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    ),
    funnel: () => (
      <Card
        style={CS} bodyStyle={CBS} headStyle={CHS}
        title={<><FunnelPlotOutlined style={{ marginRight: 8, color: T.teal }} />Воронка найма</>}
        extra={<FormulaButton chartKey="funnel" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
      >
        {chart3.every(r => r.value === 0) ? <NoData /> : (
          <ResponsiveContainer width="100%" height={Math.max(260, chart3.length * 42 + 20)}>
            <BarChart data={chart3} layout="vertical" barSize={24} margin={{ top: 4, right: isMobile ? 40 : 115, bottom: 4, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <YAxis type="category" dataKey="stage" width={isMobile ? 110 : 175} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub, fontWeight: 500 }} />
              <RTooltip
                cursor={{ fill: 'rgba(128,128,128,0.15)' }}
                content={({ active, payload, label }) => {
                  if (!active || !payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                      <div style={{ fontWeight: 600, marginBottom: 4 }}>{label}</div>
                      <div style={{ color: T.sub }}>Кандидатов: <b style={{ color: T.teal }}>{d.value}</b></div>
                      {d.conv_step !== undefined && d.stage !== 'Передано заказчику' && (
                        <div style={{ color: T.sub, marginTop: 2 }}>Конверсия с пред. этапа: <b style={{ color: T.text }}>{d.conv_step}%</b></div>
                      )}
                      {d.conv_total !== undefined && (
                        <div style={{ color: T.sub, marginTop: 2 }}>Общая конверсия от старта: <b style={{ color: T.text }}>{d.conv_total}%</b></div>
                      )}
                    </div>
                  );
                }}
              />
              <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                {chart3.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                <LabelList
                  dataKey="value"
                  position="right"
                  formatter={(val, entry) => {
                    const d = entry?.payload || {};
                    if (d.conv_step !== undefined && d.stage !== 'Передано заказчику') {
                      return `${val} (${d.conv_step}%)`;
                    }
                    return `${val}`;
                  }}
                  style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }}
                />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    ),
    rejections: () => (
      <RejectionReasonsCard
        data={chartRejections}
        isMobile={isMobile}
        onFormulaClick={setActiveFormulaKey}
      />
    ),
    companies: () => (
      <Card
        style={CS} bodyStyle={CBS} headStyle={CHS}
        title={<><BankOutlined style={{ marginRight: 8, color: T.blue }} />Топ-15 компаний кандидатов</>}
        extra={<FormulaButton chartKey="companies" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
      >
        {!chart4.length ? <NoData text="Нет данных о компаниях кандидатов" /> : (
          <ResponsiveContainer width="100%" height={Math.max(220, chart4.length * 36 + 40)}>
            <BarChart data={chart4} layout="vertical" barSize={22}
              margin={{ top: 4, right: isMobile ? 16 : 72, bottom: 4, left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <YAxis type="category" dataKey="company" width={isMobile ? 90 : 150} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <RTooltip content={<BarTip />} cursor={{ fill: 'rgba(128,128,128,0.15)' }} />
              <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                {chart4.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    ),
    avg_days_role: () => (
      <Card
        style={CS} bodyStyle={CBS} headStyle={CHS}
        title={<><FieldTimeOutlined style={{ marginRight: 8, color: T.amber }} />Средний срок закрытия (раб. дни)</>}
        extra={
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <Radio.Group size="small" value={groupBy} onChange={e => setGroupBy(e.target.value)} buttonStyle="solid">
              <Radio.Button value="it_role">По ИТ ролям</Radio.Button>
              <Radio.Button value="level">По Уровням</Radio.Button>
            </Radio.Group>
            <FormulaButton chartKey="avg_days" onOpen={setActiveFormulaKey} isMobile={isMobile} />
          </div>
        }
      >
        {!chart5.length ? <NoData text="Нет данных по закрытым вакансиям" /> : (
          <div style={{ maxHeight: 520, overflowY: 'auto' }}>
            <div style={{ height: Math.max(220, chart5.length * 36 + 30) }}>
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chart5} layout="vertical" barSize={20}
                  margin={{ top: 4, right: isMobile ? 16 : 90, bottom: 4, left: 8 }}>
                  <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                  <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
                  <YAxis type="category" dataKey="label" width={isMobile ? 100 : 175} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
                  <RTooltip
                    cursor={{ fill: 'rgba(128,128,128,0.15)' }}
                    content={({ active, payload, label }) => {
                      if (!active || !payload?.length) return null;
                      const d = payload[0].payload;
                      return (
                        <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                          <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>
                          <div style={{ color: T.sub }}>Средний срок: <b style={{ color: T.amber }}>{d.avg_days} раб. дн.</b></div>
                          <div style={{ color: T.sub }}>Вакансий: <b>{d.count}</b></div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="avg_days" fill={T.amber} radius={[0, 5, 5, 0]}>
                    <LabelList dataKey="avg_days" position="right"
                      formatter={v => `${v} д.`}
                      style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </Card>
    ),
    levels: () => (
      <Card
        style={CS} bodyStyle={CBS} headStyle={CHS}
        title={<><TeamOutlined style={{ marginRight: 8, color: T.blue }} />Распределение вакансий по уровню ИТ роли</>}
        extra={<FormulaButton chartKey="levels" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
      >
        {!chartLevels.length ? <NoData text="Нет данных по уровням" /> : (
          <ResponsiveContainer width="100%" height={Math.max(260, chartLevels.length * 42 + 20)}>
            <BarChart data={chartLevels} layout="vertical" barSize={24}
              margin={{ top: 4, right: isMobile ? 16 : 64, bottom: 4, left: 16 }}>
              <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
              <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
              <YAxis type="category" dataKey="level" width={isMobile ? 100 : 160} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <RTooltip content={<BarTip />} cursor={{ fill: 'rgba(128,128,128,0.15)' }} />
              <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                {chartLevels.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </Card>
    ),
  };

  return (
    <div style={{ padding: isMobile ? '12px 8px' : '20px 24px', background: T.bg, minHeight: '100vh' }}>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: 10 }}>
        <div>
          <Title level={4} style={{ margin: 0, fontWeight: 700, color: T.text }}>Аналитика и дашборды</Title>
        </div>
        <Space>
          <Button 
            type="primary" 
            icon={<ReloadOutlined />} 
            onClick={() => refetch()} 
            loading={isFetching}
            style={{ borderRadius: 6 }}
          >
            Обновить
          </Button>
          <Tooltip title={isConfigMode ? 'Завершить настройку' : 'Настройка дашбордов'}>
            <Button 
              icon={<SettingOutlined />}
              type={isConfigMode ? 'primary' : 'default'}
              onClick={() => setIsConfigMode(!isConfigMode)}
              style={{ borderRadius: 6 }}
            />
          </Tooltip>
        </Space>
      </div>

      <Card
        style={{ borderRadius: 10, border: `1px solid ${T.border}`, marginBottom: 16 }}
        bodyStyle={{ padding: '14px 20px' }}
      >
        <div style={{ display: 'flex', alignItems: 'flex-end', gap: isMobile ? 8 : 12, flexWrap: 'wrap' }}>
          <div style={{ display: 'inline-flex', flexDirection: 'column' }}>
            <span style={{
              fontSize: 11,
              fontWeight: 500,
              color: isDarkMode ? '#8b949e' : '#64748b',
              marginBottom: 4,
            }}>
              Период
            </span>
            <RangePicker
              size="small"
              value={period}
              onChange={val => setPeriod(val || null)}
              format="DD.MM.YYYY"
              placeholder={['Дата от', 'до']}
              allowClear
              style={{ width: isMobile ? 180 : 210, height: 28 }}
            />
          </div>

          <ExcelFilterSelect title="ИТ роль" allLabel="Все ИТ роли" value={itRoleIds} onChange={setItRoleIds} options={f.it_roles} isMobile={isMobile} />
          <ExcelFilterSelect title="Уровень" allLabel="Все уровни" value={levelIds} onChange={setLevelIds} options={f.levels} isMobile={isMobile} />
          <ExcelFilterSelect title="Адм. руководитель" allLabel="Все руководители" value={adminMgrIds} onChange={setAdminMgrIds} options={f.admin_managers} isMobile={isMobile} style={{ minWidth: isMobile ? 130 : 160 }} />
          <ExcelFilterSelect title="Проект" allLabel="Все проекты" value={projectIds} onChange={setProjectIds} options={f.projects} isMobile={isMobile} />
          <ExcelFilterSelect title="Рекрутер" allLabel="Все рекрутеры" value={recruiterIds} onChange={setRecruiterIds} options={f.recruiters} isMobile={isMobile} />
          <ExcelFilterSelect title="ИТ Блок" allLabel="Все блоки" value={blockIds} onChange={setBlockIds} options={f.blocks} isMobile={isMobile} />
          <ExcelFilterSelect title="Статус" allLabel="Все статусы" value={statusIds} onChange={setStatusIds} options={f.statuses} isMobile={isMobile} style={{ minWidth: isMobile ? 120 : 140 }} />
          <ExcelFilterSelect title="ID вакансии" allLabel="Все вакансии" value={vacancyIds} onChange={setVacancyIds} options={f.vacancies} isMobile={isMobile} style={{ minWidth: isMobile ? 110 : 130 }} />

          {hasFilters && (
            <Button size="small" icon={<ClearOutlined />} onClick={clearFilters} style={{ color: T.red, borderColor: T.red, fontSize: 12, height: 28, alignSelf: 'flex-end' }}>
              Сбросить
            </Button>
          )}
          {isFetching && <Spin size="small" style={{ marginLeft: 8, alignSelf: 'flex-end', marginBottom: 4 }} />}
        </div>
      </Card>

      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        style={{ marginBottom: 16 }}
        items={[
          { key: 'all', label: 'Все' },
          { key: 'statuses', label: 'Статусы и загрузка' },
          { key: 'funnel', label: 'Воронка и конверсия' },
          { key: 'analytics', label: 'Сроки и структура' },
        ]}
      />

      {isConfigMode && (
        <Alert
          type="info"
          showIcon
          style={{ marginBottom: 16, borderRadius: 8 }}
          message={
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
              <span style={{ fontSize: 13 }}>
                <b>Режим настройки активен:</b> перетаскивайте карточки мышью за маркер <b>⠿</b> или меняйте порядок кнопками <b>← / →</b>, а также настраивайте ширину. Изменения сохраняются автоматически.
              </span>
              <Space>
                <Button
                  size="small"
                  icon={<UndoOutlined />}
                  onClick={resetCurrentTabLayout}
                >
                  Сбросить по умолчанию
                </Button>
                <Button
                  type="primary"
                  size="small"
                  icon={<CheckOutlined />}
                  onClick={() => setIsConfigMode(false)}
                >
                  Готово
                </Button>
              </Space>
            </div>
          }
        />
      )}

      {isLoading && !data ? (
        <Row gutter={[20, 20]}>
          <Col xs={24} lg={24}><Card style={CS}><Skeleton active paragraph={{ rows: 2 }} /></Card></Col>
          <Col xs={24} lg={8}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={8}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={8}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={24}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={24}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={12}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
          <Col xs={24} lg={12}><Card style={CS}><Skeleton active paragraph={{ rows: 6 }} /></Card></Col>
        </Row>
      ) : (
        <Row gutter={[20, 20]}>
          {currentCards.map((card, index) => {
            const renderer = cardRenderers[card.id];
            if (!renderer) return null;
            const isDragging = draggedIndex === index;
            const isOver = dragOverIndex === index;

            return (
              <Col
                key={card.id}
                xs={24}
                lg={card.size || DASHBOARD_CARDS_MAP[card.id]?.defaultSize || 24}
                style={{
                  transition: 'opacity 0.2s ease',
                  opacity: isDragging ? 0.35 : 1,
                }}
              >
                <div
                  onDragOver={(e) => isConfigMode && handleDragOver(e, index)}
                  onDrop={(e) => isConfigMode && handleDrop(e, index)}
                  style={{
                    height: '100%',
                    position: 'relative',
                    borderRadius: 10,
                    outline: isConfigMode && isOver ? '2px dashed #1677ff' : 'none',
                    outlineOffset: 4,
                  }}
                >
                  {isConfigMode && (
                    <div
                      draggable
                      onDragStart={(e) => handleDragStart(e, index)}
                      onDragEnd={handleDragEnd}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '6px 12px',
                        marginBottom: 8,
                        background: isDarkMode ? '#1e293b' : '#f8fafc',
                        border: `1px solid ${isDarkMode ? '#334155' : '#cbd5e1'}`,
                        borderRadius: 8,
                        cursor: 'grab',
                        userSelect: 'none',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.05)',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
                        <HolderOutlined style={{ color: '#1677ff', fontSize: 16, cursor: 'grab' }} />
                        <span style={{
                          fontWeight: 600,
                          fontSize: 13,
                          color: isDarkMode ? '#f1f5f9' : '#1e293b',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}>
                          {DASHBOARD_CARDS_MAP[card.id]?.title || card.id}
                        </span>
                      </div>

                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
                        <Button.Group size="small">
                          <Tooltip title="Сдвинуть влево/выше">
                            <Button
                              size="small"
                              disabled={index === 0}
                              icon={<ArrowLeftOutlined />}
                              onClick={() => moveCard(index, index - 1)}
                            />
                          </Tooltip>
                          <Tooltip title="Сдвинуть вправо/ниже">
                            <Button
                              size="small"
                              disabled={index === currentCards.length - 1}
                              icon={<ArrowRightOutlined />}
                              onClick={() => moveCard(index, index + 1)}
                            />
                          </Tooltip>
                        </Button.Group>

                        <Select
                          size="small"
                          value={card.size || DASHBOARD_CARDS_MAP[card.id]?.defaultSize || 24}
                          onChange={(val) => updateCardSize(index, val)}
                          style={{ width: 110 }}
                          options={[
                            { value: 8, label: '33% (1/3)' },
                            { value: 10, label: '40%' },
                            { value: 12, label: '50% (1/2)' },
                            { value: 14, label: '60%' },
                            { value: 16, label: '66% (2/3)' },
                            { value: 24, label: '100% (Вся)' },
                          ]}
                        />
                      </div>
                    </div>
                  )}

                  {renderer()}
                </div>
              </Col>
            );
          })}
        </Row>
      )}

      {/* Formula Modal */}
      <FormulaModal
        formulaKey={activeFormulaKey}
        onClose={() => setActiveFormulaKey(null)}
      />

    </div>
  );
}
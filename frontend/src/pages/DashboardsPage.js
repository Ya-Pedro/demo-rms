import React, { useState } from 'react';
import dayjs from 'dayjs';
import useIsMobile from '../hooks/useIsMobile';
import {
  Row, Col, Card, Select, Skeleton, Typography,
  DatePicker, Button, Spin, Space, Radio, Modal, Tooltip,
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
  FileTextOutlined, ReloadOutlined, InfoCircleOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { api, ThemeContext } from '../App';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const T = {
  bg: 'var(--layout-bg)', border: 'var(--border-color)',
  text: 'var(--text-color)', sub: '#8b949e', muted: '#8b949e',
  blue: '#58a6ff', green: '#3fb950', red: '#f85149',
  amber: '#d29922', purple: '#bc8cff', teal: '#56d364',
};

const PALETTE = [
  '#2563eb','#16a34a','#d97706','#7c3aed','#0d9488',
  '#dc2626','#ea580c','#0891b2','#65a30d','#be185d',
  '#6366f1','#14b8a6','#f59e0b','#8b5cf6','#10b981',
];

const STATUS_COLOR = {
  'Открыта': T.blue, 'Закрыта': T.green, 'Hold': T.amber,
  'Отмена': T.red, 'Оффер': T.purple, 'Выход': T.teal,
  'Подготовка документов': '#f59e0b', 'Проверка СБ': '#6366f1',
  'Согласование фин условий': '#14b8a6',
};

const CS  = { borderRadius: 10, border: `1px solid ${T.border}`, boxShadow: '0 1px 4px rgba(0,0,0,0.06)', height: '100%' };
const CBS = { padding: '14px 18px' };
const CHS = { borderBottom: `1px solid ${T.border}`, padding: '12px 20px', minHeight: 'unset', fontSize: 14, fontWeight: 700, color: T.text };

// Unified typography standards across all dashboard charts
const FS_AXIS_LABEL = 13; // Category labels on axes (recruiter, status, company, level, stage)
const FS_AXIS_NUM   = 12; // Numeric ticks on axes (0, 10, 20...)
const FS_BAR_VAL    = 13; // Values directly on chart bars / points
const FS_LEGEND     = 13; // Legend items and percentages

// Descriptions and formulas for all dashboard charts — concise, clear and uniform
const CHART_FORMULAS = {
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
    rules: '«Всего» = Открыта + Закрыта + Hold + Отмена. Статус «Выход» включён в «Открыта».',
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
          <InfoCircleOutlined style={{ color: isDarkMode ? '#58a6ff' : '#2563eb', fontSize: 19 }} />
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

const MultiFlt = ({ value, onChange, options, placeholder, style, isMobile }) => (
  <Select
    mode="multiple"
    value={value || []}
    onChange={v => onChange(v.length ? v : null)}
    placeholder={placeholder}
    allowClear
    size="small"
    maxTagCount={1}
    style={{ minWidth: isMobile ? 120 : 150, fontSize: 12, ...style }}
    getPopupContainer={() => document.body}
    showSearch
    optionFilterProp="children"
  >
    {(options || []).map(o => (
      <Select.Option key={o.id} value={o.id}>{o.value}</Select.Option>
    ))}
  </Select>
);

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
  const { cx, cy, midAngle, outerRadius, percent } = props;
  if (percent < 0.05) return null;
  const RADIAN = Math.PI / 180;
  const radius = outerRadius + 16;
  const x = cx + radius * Math.cos(-midAngle * RADIAN);
  const y = cy + radius * Math.sin(-midAngle * RADIAN);
  return (
    <text x={x} y={y} fill={T.text} fontSize={FS_AXIS_LABEL} fontWeight={600} textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
      {`${(percent * 100).toFixed(0)}%`}
    </text>
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
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div style={{ width: '100%', height: 200 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={data} dataKey="value" nameKey="name"
                  cx="50%" cy="50%" outerRadius={55}
                  labelLine={true} label={renderPieLabel}>
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
  const green = isDarkMode ? '#2fc08c' : '#169b6b';
  const red   = isDarkMode ? '#f06462' : '#d93f3e';
  const blue  = isDarkMode ? '#5aa0f0' : '#2a78d6';
  const color = isMax ? green : isMin ? red : blue;
  const r = (isMax || isMin) ? 7 : 4.5;

  return (
    <g key={`dot-${payload.label || payload.name}`}>
      <circle cx={cx} cy={cy} r={r} fill={color} stroke={color} strokeWidth={2} />
      <text
        x={cx}
        y={isMin ? cy + 18 : cy - 12}
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

  const green = isDarkMode ? '#2fc08c' : '#169b6b';
  const red   = isDarkMode ? '#f06462' : '#d93f3e';
  const blue  = isDarkMode ? '#5aa0f0' : '#2a78d6';
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
            <BarChart data={list} barSize={64} margin={{ top: 24, right: 24, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <YAxis domain={[0, 100]} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
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
            <LineChart data={list} margin={{ top: 24, right: isMobile ? 20 : 36, bottom: 8, left: 8 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey="label" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
              <YAxis domain={yDomain} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
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
        <span style={{ fontSize: 12, color: T.muted }}>
          {mode === 'month' ? 'Ось Y сужена, чтобы были видны колебания.' : mode === 'quarter' ? 'Квартал — кумулятивно по итогам квартала.' : 'Год — кумулятивный показатель за год; ось Y от 0 до 100%.'}
        </span>
      </div>
    </Card>
  );
};

const AvgDaysDot = ({ cx, cy, payload, maxVal, minVal, hasDiff, isDarkMode }) => {
  if (cx == null || cy == null || !payload) return null;
  const isBest = hasDiff && payload.value === minVal;
  const isWorst = hasDiff && payload.value === maxVal;
  const green = isDarkMode ? '#2fc08c' : '#169b6b';
  const red   = isDarkMode ? '#f06462' : '#d93f3e';
  const blue  = isDarkMode ? '#5aa0f0' : '#2a78d6';
  const color = isBest ? green : isWorst ? red : blue;
  const r = (isBest || isWorst) ? 7 : 4.5;

  return (
    <g key={`dot-avg-${payload.label || payload.name}`}>
      <circle cx={cx} cy={cy} r={r} fill={color} stroke={color} strokeWidth={2} />
      <text
        x={cx}
        y={isBest ? cy + 18 : cy - 12}
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

  const green = isDarkMode ? '#2fc08c' : '#169b6b';
  const red   = isDarkMode ? '#f06462' : '#d93f3e';
  const blue  = isDarkMode ? '#5aa0f0' : '#2a78d6';
  const amber = isDarkMode ? '#f59f00' : '#d97706';
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
      const floorMin = Math.max(0, Math.floor((minVal - 5) / 5) * 5);
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
              <BarChart data={list} barSize={54} margin={{ top: 22, right: 24, bottom: 4, left: 4 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
                <YAxis domain={yDomain} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
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
              <LineChart data={list} margin={{ top: 24, right: 24, bottom: 4, left: 4 }}>
                <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
                <XAxis dataKey="label" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
                <YAxis domain={yDomain} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
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
        <span style={{ fontSize: 12, color: T.muted }}>
          {mode === 'month' ? 'Данные по месяцам выбранного года. Рассчитано по производственному календарю РФ.' : mode === 'quarter' ? 'Квартал — средний срок закрытия за квартал.' : 'Год — средний срок закрытия за год; ось Y от 0.'}
        </span>
      </div>
    </Card>
  );
};

const RejectionReasonsCard = ({ data, isMobile, onFormulaClick }) => {
  const { isDarkMode } = React.useContext(ThemeContext);
  const red = isDarkMode ? '#f06462' : '#f85149';

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
          <BarChart data={data} layout="vertical" barSize={22} margin={{ top: 8, right: isMobile ? 24 : 64, bottom: 8, left: 8 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke={isDarkMode ? '#2c3038' : '#f0f0f0'} />
            <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} allowDecimals={false} />
            <YAxis type="category" dataKey="reason" width={isMobile ? 110 : 170} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
            <RTooltip
              content={({ active, payload, label }) => {
                if (!active || !payload?.length) return null;
                return (
                  <div style={{ background: 'var(--card-bg)', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                    <div style={{ fontWeight: 600, marginBottom: 3, color: T.text }}>{label}</div>
                    <div style={{ color: T.sub }}>Количество отказов: <b style={{ color: red }}>{payload[0].value}</b></div>
                  </div>
                );
              }}
            />
            <Bar dataKey="value" radius={[0, 5, 5, 0]}>
              {data.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
              <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
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

  // Active formula modal
  const [activeFormulaKey, setActiveFormulaKey] = useState(null);

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
  const chartLevels      = data?.chart_levels      || [];
  const chartReplacement = data?.chart_replacement || [];
  const chartEmployment  = data?.chart_employment  || [];
  const chartRejections  = data?.chart_rejections  || [];
  const chartJoConv      = data?.chart_jo_conversion || { month: [], quarter: [], year: [] };
  const chartAvgDaysTimeline = data?.chart_avg_days_timeline || { month: [], quarter: [], year: [] };

  const bar2data = [
    { name: 'Всего',   value: chart2.total,  fill: T.sub   },
    { name: 'Открыта', value: chart2.open,   fill: T.blue  },
    { name: 'Закрыта', value: chart2.closed, fill: T.green },
    { name: 'Hold',    value: chart2.hold,   fill: T.amber },
    { name: 'Отмена',  value: chart2.cancel, fill: T.red   },
  ].filter(d => d.value > 0);

  const DRILL_DOWN_EXCLUDE = new Set(['Закрыта', 'Hold', 'Отмена', 'Всего']);
  const chart6Details = chart6.filter(r => !DRILL_DOWN_EXCLUDE.has(r.status));

  return (
    <div style={{ padding: isMobile ? '12px 8px' : '20px 24px', background: T.bg, minHeight: '100vh' }}>

      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <Title level={4} style={{ margin: 0, fontWeight: 700, color: T.text }}>Аналитика и дашборды</Title>
          <Text style={{ color: T.muted, fontSize: 13 }}>Агрегированная статистика по всем вакансиям</Text>
        </div>
        <Button 
          type="primary" 
          icon={<ReloadOutlined />} 
          onClick={() => refetch()} 
          loading={isFetching}
          style={{ borderRadius: 6 }}
        >
          Обновить
        </Button>
      </div>

      <Card
        style={{ borderRadius: 10, border: `1px solid ${T.border}`, marginBottom: 20 }}
        bodyStyle={{ padding: '14px 20px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: isMobile ? 6 : 8, flexWrap: 'wrap' }}>
          <FilterOutlined style={{ color: T.sub, fontSize: 14 }} />
          <Text style={{ fontSize: 13, color: T.text, marginRight: 4, whiteSpace: 'nowrap' }}>Фильтры:</Text>

          <RangePicker
            size="small"
            value={period}
            onChange={val => setPeriod(val || null)}
            format="DD.MM.YYYY"
            placeholder={['Дата от', 'до']}
            allowClear
            style={{ width: isMobile ? 180 : 230 }}
          />

          <MultiFlt value={itRoleIds} onChange={setItRoleIds} options={f.it_roles} placeholder="ИТ роль" isMobile={isMobile} />
          <MultiFlt value={levelIds} onChange={setLevelIds} options={f.levels} placeholder="Уровень" isMobile={isMobile} />
          <MultiFlt value={adminMgrIds} onChange={setAdminMgrIds} options={f.admin_managers} placeholder="Адм. руководитель" isMobile={isMobile} style={{ minWidth: isMobile ? 140 : 180 }} />
          <MultiFlt value={projectIds} onChange={setProjectIds} options={f.projects} placeholder="Проект" isMobile={isMobile} />
          <MultiFlt value={recruiterIds} onChange={setRecruiterIds} options={f.recruiters} placeholder="Рекрутер" isMobile={isMobile} />
          <MultiFlt value={blockIds} onChange={setBlockIds} options={f.blocks} placeholder="ИТ Блок" isMobile={isMobile} />
          <MultiFlt value={statusIds} onChange={setStatusIds} options={f.statuses} placeholder="Статус вакансии" isMobile={isMobile} style={{ minWidth: isMobile ? 130 : 160 }} />
          <MultiFlt value={vacancyIds} onChange={setVacancyIds} options={f.vacancies} placeholder="ID вакансии" isMobile={isMobile} style={{ minWidth: isMobile ? 110 : 130 }} />

          {hasFilters && (
            <Button size="small" icon={<ClearOutlined />} onClick={clearFilters} style={{ color: T.red, borderColor: T.red, fontSize: 12 }}>
              Сбросить
            </Button>
          )}
          {isFetching && <Spin size="small" style={{ marginLeft: 8 }} />}
        </div>
      </Card>

      {isLoading && !data ? (
        <Row gutter={[20, 20]}>
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

          {/* 1. Источник найма */}
          <Col xs={24} lg={8}>
            <DonutCard 
              title="Источник найма" 
              icon={<PieChartOutlined />} 
              color={T.purple} 
              data={chart1}
              chartKey="source"
              onFormulaClick={setActiveFormulaKey}
              isMobile={isMobile}
            />
          </Col>

          {/* 2. Тип вакансии (Новая/Замена) */}
          <Col xs={24} lg={8}>
            <DonutCard 
              title="Тип вакансии (Новая/Замена)" 
              icon={<PieChartOutlined />} 
              color={T.amber} 
              data={chartReplacement}
              chartKey="replacement"
              onFormulaClick={setActiveFormulaKey}
              isMobile={isMobile}
            />
          </Col>

          {/* 3. Вид занятости */}
          <Col xs={24} lg={8}>
            <DonutCard 
              title="Вид занятости" 
              icon={<PieChartOutlined />} 
              color={T.teal} 
              data={chartEmployment}
              chartKey="employment"
              onFormulaClick={setActiveFormulaKey}
              isMobile={isMobile}
            />
          </Col>

          {/* 4. Вторая линия — Конверсия принятия JO */}
          <Col xs={24} lg={24}>
            <JOConversionCard
              data={chartJoConv}
              isMobile={isMobile}
              onFormulaClick={setActiveFormulaKey}
            />
          </Col>

          {/* Динамика среднего срока закрытия (раб. дни) */}
          <Col xs={24} lg={24}>
            <AvgDaysTimelineCard
              data={chartAvgDaysTimeline}
              isMobile={isMobile}
              onFormulaClick={setActiveFormulaKey}
            />
          </Col>

          {/* 5. Распределение вакансий по уровню ИТ роли */}
          <Col xs={24} lg={12}>
            <Card
              style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><TeamOutlined style={{ marginRight: 8, color: T.blue }} />Распределение вакансий по уровню ИТ роли</>}
              extra={<FormulaButton chartKey="levels" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
            >
              {!chartLevels.length ? <NoData text="Нет данных по уровням" /> : (
                <ResponsiveContainer width="100%" height={Math.max(200, chartLevels.length * 42 + 20)}>
                  <BarChart data={chartLevels} layout="vertical" barSize={22}
                    margin={{ top: 4, right: isMobile ? 16 : 64, bottom: 4, left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_NUM, fill: T.muted }} />
                    <YAxis type="category" dataKey="level" width={isMobile ? 90 : 140} axisLine={false} tickLine={false} style={{ fontSize: FS_AXIS_LABEL, fill: T.sub }} />
                    <RTooltip content={<BarTip />} cursor={{ fill: 'rgba(128,128,128,0.15)' }} />
                    <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                      {chartLevels.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {/* 6. Загрузка рекрутеров */}
          <Col xs={24} lg={12}>
            <Card
              style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><TeamOutlined style={{ marginRight: 8, color: T.purple }} />Загрузка рекрутеров</>}
              extra={<FormulaButton chartKey="recruiter_load" onOpen={setActiveFormulaKey} isMobile={isMobile} />}
            >
              {!chart8.length ? (
                <NoData text="Нет данных — возможно не заполнен рекрутер у вакансий" />
              ) : (
                <ResponsiveContainer width="100%" height={Math.max(200, chart8.length * 42 + 20)}>
                  <BarChart
                    data={chart8}
                    layout="vertical"
                    barSize={18}
                    margin={{ top: 4, right: isMobile ? 16 : 64, bottom: 4, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false}
                      style={{ fontSize: FS_AXIS_NUM, fill: T.muted }}
                      domain={[0, dataMax => Math.round((chart8[0]?.value || dataMax) * 1.2)]} />
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
                      {chart8.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      <LabelList dataKey="value" position="right"
                        style={{ fontWeight: 700, fontSize: FS_BAR_VAL, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {/* 7. Детализация «Открытых» вакансий */}
          <Col xs={24} lg={12}>
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
          </Col>

          {/* 8. Вакансии по статусам */}
          <Col xs={24} lg={12}>
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
          </Col>

          {/* 9. Воронка найма */}
          <Col xs={24} lg={14}>
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
          </Col>

          {/* 10. Причины отказа */}
          <Col xs={24} lg={10}>
            <RejectionReasonsCard
              data={chartRejections}
              isMobile={isMobile}
              onFormulaClick={setActiveFormulaKey}
            />
          </Col>

          {/* 11. Топ-15 компаний кандидатов */}
          <Col xs={24} lg={12}>
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
          </Col>

          {/* 12. Средний срок закрытия (раб. дни) */}
          <Col xs={24} lg={12}>
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
          </Col>

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
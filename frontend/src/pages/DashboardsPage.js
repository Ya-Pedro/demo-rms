import React, { useState, useEffect, useCallback } from 'react';
import {
  Row, Col, Card, Select, Spin, Typography, Statistic,
  Tag, Divider, Empty, DatePicker, Radio, Space, Button,
} from 'antd';
import {
  ResponsiveContainer,
  PieChart, Pie, Cell, Tooltip as RTooltip, Legend,
  BarChart, Bar, XAxis, YAxis, CartesianGrid, LabelList,
  Cell as BCell,
} from 'recharts';
import {
  RiseOutlined, TeamOutlined, TrophyOutlined,
  FieldTimeOutlined, BankOutlined, FunnelPlotOutlined,
  PieChartOutlined, CalendarOutlined, FilterOutlined,
  ClearOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { api } from '../App';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

const T = {
  bg: '#f0f2f5', border: '#e8eaed',
  text: '#1a1d23', sub: '#6b7280', muted: '#9ca3af',
  blue: '#2563eb', green: '#16a34a', red: '#dc2626',
  amber: '#d97706', purple: '#7c3aed', teal: '#0d9488',
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

const MultiFlt = ({ value, onChange, options, placeholder, style }) => (
  <Select
    mode="multiple"
    value={value || []}
    onChange={v => onChange(v.length ? v : null)}
    placeholder={placeholder}
    allowClear
    size="small"
    maxTagCount={1}
    style={{ minWidth: 150, fontSize: 12, ...style }}
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
    <div style={{ background: '#fff', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
      <div style={{ fontWeight: 600, marginBottom: 3 }}>{d.name || d.status}</div>
      <div style={{ color: T.sub }}>Кол-во: <b style={{ color: T.text }}>{d.value}</b></div>
      <div style={{ color: T.sub }}>Доля: <b style={{ color: T.blue }}>{d.pct}%</b></div>
    </div>
  );
};

const BarTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: '#fff', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
      <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: T.sub }}>{p.name}: <b style={{ color: p.fill || T.blue }}>{p.value}</b></div>
      ))}
    </div>
  );
};

const PieLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent }) => {
  if (percent < 0.05) return null;
  const R = Math.PI / 180;
  const r = innerRadius + (outerRadius - innerRadius) * 0.58;
  return (
    <text x={cx + r * Math.cos(-midAngle * R)} y={cy + r * Math.sin(-midAngle * R)}
      fill="#fff" textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={700}>
      {`${(percent * 100).toFixed(1)}%`}
    </text>
  );
};

const NoData = ({ text = 'Нет данных' }) => (
  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 220 }}>
    <Empty description={<Text type="secondary" style={{ fontSize: 12 }}>{text}</Text>} image={Empty.PRESENTED_IMAGE_SIMPLE} />
  </div>
);

const DonutCard = ({ title, icon, data, color }) => (
  <Card style={CS} bodyStyle={{ padding: '16px 24px' }} headStyle={CHS}
    title={<><span style={{ marginRight: 8, color }}>{icon}</span>{title}</>}>
    {!data?.length ? <NoData /> : (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 20 }}>
        <div style={{ width: 180, height: 180 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie data={data} dataKey="value" nameKey="name"
                cx="50%" cy="50%" innerRadius={48} outerRadius={88}
                labelLine={false} label={PieLabel}>
                {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
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
              <span style={{ fontSize: 13, color: T.sub, fontWeight: 500 }}>
                {item.name}
              </span>
              <span style={{ fontSize: 13, fontWeight: 700, color: T.text }}>
                {item.pct}%
              </span>
            </div>
          ))}
        </div>
      </div>
    )}
  </Card>
);

export default function DashboardsPage() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);

  const [period,         setPeriod]        = useState(null);
  const [itRoleIds,      setItRoleIds]     = useState(null);
  const [levelIds,       setLevelIds]      = useState(null);
  const [adminMgrIds,    setAdminMgrIds]   = useState(null);
  const [projectIds,     setProjectIds]    = useState(null);
  const [recruiterIds,   setRecruiterIds]  = useState(null);
  const [blockIds,       setBlockIds]      = useState(null);
  const [statusIds,      setStatusIds]     = useState(null);

  const [groupBy, setGroupBy] = useState('it_role');

  const buildParams = useCallback(() => {
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
    if (groupBy)              p.append('group_by',          groupBy);
    return p;
  }, [period, itRoleIds, levelIds, adminMgrIds, projectIds, recruiterIds, blockIds, statusIds, groupBy]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/dashboards/metrics?${buildParams()}`);
      setData(res.data);
    } catch (e) {
      console.error('Dashboard error', e);
    } finally {
      setLoading(false);
    }
  }, [buildParams]);

  useEffect(() => { fetchData(); }, [fetchData]);

  const clearFilters = () => {
    setPeriod(null);
    setItRoleIds(null);
    setLevelIds(null);
    setAdminMgrIds(null);
    setProjectIds(null);
    setRecruiterIds(null);
    setBlockIds(null);
    setStatusIds(null);
  };

  const f = data?.filters || {};
  const hasFilters = period || itRoleIds || levelIds || adminMgrIds || projectIds || recruiterIds || blockIds || statusIds;

  const chart1 = data?.chart1_source    || [];
  const chart2 = data?.chart2_open_closed || { total: 0, open: 0, closed: 0, exit: 0, hold: 0, cancel: 0 };
  const chart3 = data?.chart3_funnel    || [];
  const chart4 = data?.chart4_companies || [];
  const chart5 = data?.chart5_avg_days  || [];
  const chart6 = data?.chart6_statuses  || [];
  const chart7 = data?.chart7_jo_rate   || { jo_rate: 0, closed: 0, offers_total: 0 };
  const chart8 = data?.chart8_recruiter_load || [];
  
  const chartLevels      = data?.chart_levels      || [];
  const chartReplacement = data?.chart_replacement || [];
  const chartEmployment  = data?.chart_employment  || [];
  const chartSalaries    = data?.chart_salaries    || { p25: 0, p50: 0, p75: 0 };

  const joRate  = chart7.jo_rate;
  const joColor = joRate >= 70 ? T.green : joRate >= 40 ? T.amber : T.red;
  const joTag   = joRate >= 70 ? 'success' : joRate >= 40 ? 'warning' : 'error';
  const joLabel = joRate >= 70 ? 'Отличный результат' : joRate >= 40 ? 'Есть куда расти' : 'Требует внимания';

  const bar2data = [
    { name: 'Всего',   value: chart2.total,  fill: T.sub   },
    { name: 'Открыта', value: chart2.open,   fill: T.blue  },
    { name: 'Закрыта', value: chart2.closed, fill: T.green },
    { name: 'Выход',   value: chart2.exit,   fill: T.teal  },
    { name: 'Hold',    value: chart2.hold,   fill: T.amber },
    { name: 'Отмена',  value: chart2.cancel, fill: T.red   },
  ].filter(d => d.value > 0);

  const DRILL_DOWN_EXCLUDE = new Set(['Закрыта', 'Выход', 'Hold', 'Отмена', 'Всего']);
  const chart6Details = chart6.filter(r => !DRILL_DOWN_EXCLUDE.has(r.status));

  return (
    <div style={{ padding: '20px 24px', background: T.bg, minHeight: '100vh' }}>

      {}
      <div style={{ marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0, fontWeight: 700, color: T.text }}>Аналитика и дашборды</Title>
        <Text style={{ color: T.muted, fontSize: 13 }}>Агрегированная статистика по всем вакансиям</Text>
      </div>

      {}
      <Card
        style={{ borderRadius: 10, border: `1px solid ${T.border}`, marginBottom: 20 }}
        bodyStyle={{ padding: '14px 20px' }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
          <FilterOutlined style={{ color: T.sub, fontSize: 14 }} />
          <Text style={{ fontSize: 13, color: T.sub, marginRight: 4, whiteSpace: 'nowrap' }}>Фильтры:</Text>

          <RangePicker
            size="small"
            value={period}
            onChange={val => setPeriod(val || null)}
            format="DD.MM.YYYY"
            placeholder={['Дата открытия от', 'до']}
            allowClear
            style={{ width: 230 }}
          />

          <MultiFlt
            value={itRoleIds}
            onChange={setItRoleIds}
            options={f.it_roles}
            placeholder="ИТ роль"
          />

          <MultiFlt
            value={levelIds}
            onChange={setLevelIds}
            options={f.levels}
            placeholder="Уровень"
          />

          <MultiFlt
            value={adminMgrIds}
            onChange={setAdminMgrIds}
            options={f.admin_managers}
            placeholder="Адм. руководитель"
            style={{ minWidth: 180 }}
          />

          <MultiFlt
            value={projectIds}
            onChange={setProjectIds}
            options={f.projects}
            placeholder="Проект"
          />

          <MultiFlt
            value={recruiterIds}
            onChange={setRecruiterIds}
            options={f.recruiters}
            placeholder="Рекрутер"
          />

          <MultiFlt
            value={blockIds}
            onChange={setBlockIds}
            options={f.blocks}
            placeholder="ИТ Блок"
          />

          <MultiFlt
            value={statusIds}
            onChange={setStatusIds}
            options={f.statuses}
            placeholder="Статус вакансии"
            style={{ minWidth: 160 }}
          />

          {hasFilters && (
            <Button
              size="small"
              icon={<ClearOutlined />}
              onClick={clearFilters}
              style={{ color: T.red, borderColor: T.red, fontSize: 12 }}
            >
              Сбросить
            </Button>
          )}

          {loading && <Spin size="small" style={{ marginLeft: 8 }} />}
        </div>
      </Card>

      {loading && !data ? (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: 400 }}>
          <Spin size="large" />
        </div>
      ) : (
        <Row gutter={[20, 20]}>

          {}
          <Col xs={24} lg={24}>
            <Card style={CS} bodyStyle={{ padding: '20px 28px' }} headStyle={CHS}
              title={<><RiseOutlined style={{ marginRight: 8, color: T.blue }} />Коэффициент принятия Job Offer</>}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 32, flexWrap: 'wrap' }}>
                <div>
                  <div style={{ fontSize: 64, fontWeight: 800, lineHeight: 1, color: joColor, letterSpacing: '-2px' }}>
                    {joRate.toFixed(1)}<span style={{ fontSize: 28, fontWeight: 600 }}>%</span>
                  </div>
                  <Tag color={joTag} style={{ marginTop: 8, fontSize: 12, padding: '2px 10px' }}>{joLabel}</Tag>
                </div>
                <Divider type="vertical" style={{ height: 72, margin: '0' }} />
                <Statistic
                  title={<Text style={{ fontSize: 12, color: T.muted }}>Закрытых + Выход</Text>}
                  value={chart7.closed}
                  valueStyle={{ fontSize: 28, fontWeight: 700, color: T.green }}
                  prefix={<TrophyOutlined style={{ fontSize: 18, marginRight: 4 }} />}
                />
                <Divider type="vertical" style={{ height: 72, margin: '0' }} />
                <Statistic
                  title={<Text style={{ fontSize: 12, color: T.muted }}>Всего офферов</Text>}
                  value={chart7.offers_total}
                  valueStyle={{ fontSize: 28, fontWeight: 700, color: T.blue }}
                  prefix={<TeamOutlined style={{ fontSize: 18, marginRight: 4 }} />}
                />
                <Divider type="vertical" style={{ height: 72, margin: '0' }} />
                <div style={{ display: 'flex', gap: 24, paddingLeft: 16 }}>
                  <Statistic
                    title={<Text style={{ fontSize: 12, color: T.muted }}>Медианная ЗП (Gross)</Text>}
                    value={chartSalaries.p50}
                    valueStyle={{ fontSize: 28, fontWeight: 700, color: T.purple }}
                    suffix="₽"
                  />
                  <Statistic
                    title={<Text style={{ fontSize: 12, color: T.muted }}>Q1 (25%)</Text>}
                    value={chartSalaries.p25}
                    valueStyle={{ fontSize: 20, fontWeight: 600, color: T.sub }}
                    suffix="₽"
                  />
                  <Statistic
                    title={<Text style={{ fontSize: 12, color: T.muted }}>Q3 (75%)</Text>}
                    value={chartSalaries.p75}
                    valueStyle={{ fontSize: 20, fontWeight: 600, color: T.sub }}
                    suffix="₽"
                  />
                </div>
              </div>
            </Card>
          </Col>

          <Col xs={24} lg={8}>
            <DonutCard 
              title="Источник найма" 
              icon={<PieChartOutlined />} 
              color={T.purple} 
              data={chart1} 
            />
          </Col>

          <Col xs={24} lg={8}>
            <DonutCard 
              title="Тип вакансии (Новая/Замена)" 
              icon={<PieChartOutlined />} 
              color={T.amber} 
              data={chartReplacement} 
            />
          </Col>

          <Col xs={24} lg={8}>
            <DonutCard 
              title="Вид занятости" 
              icon={<PieChartOutlined />} 
              color={T.teal} 
              data={chartEmployment} 
            />
          </Col>

          <Col xs={24} lg={12}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><TeamOutlined style={{ marginRight: 8, color: T.blue }} />Распределение вакансий по уровню ИТ роли</>}>
              {!chartLevels.length ? <NoData text="Нет данных по уровням" /> : (
                <ResponsiveContainer width="100%" height={Math.max(200, chartLevels.length * 42 + 20)}>
                  <BarChart data={chartLevels} layout="vertical" barSize={22}
                    margin={{ top: 4, right: 64, bottom: 4, left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: 12, fill: T.muted }} />
                    <YAxis type="category" dataKey="level" width={140} axisLine={false} tickLine={false} style={{ fontSize: 14, fill: T.sub }} />
                    <RTooltip content={<BarTip />} />
                    <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                      {chartLevels.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: 14, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {}
          <Col xs={24} lg={12}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><TeamOutlined style={{ marginRight: 8, color: T.purple }} />Загрузка рекрутеров</>}>
              {!chart8.length ? (
                <NoData text="Нет данных — возможно не заполнен рекрутер у вакансий" />
              ) : (
                <ResponsiveContainer width="100%" height={Math.max(200, chart8.length * 42 + 20)}>
                  <BarChart
                    data={chart8}
                    layout="vertical"
                    barSize={18}
                    margin={{ top: 4, right: 64, bottom: 4, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false}
                      style={{ fontSize: 11, fill: T.muted }}
                      domain={[0, dataMax => Math.round((chart8[0]?.value || dataMax) * 1.2)]} />
                    <YAxis type="category" dataKey="recruiter" width={175}
                      axisLine={false} tickLine={false} style={{ fontSize: 14, fill: T.sub }} />
                    <RTooltip
                      content={({ active, payload, label }) => {
                        if (!active || !payload?.length) return null;
                        return (
                          <div style={{ background: '#fff', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
                            <div style={{ fontWeight: 600, marginBottom: 3 }}>{label}</div>
                            <div style={{ color: T.sub }}>Вакансий: <b style={{ color: T.purple }}>{payload[0].value}</b></div>
                          </div>
                        );
                      }}
                    />
                    <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                      {chart8.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      <LabelList dataKey="value" position="right"
                        style={{ fontWeight: 700, fontSize: 14, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><PieChartOutlined style={{ marginRight: 8 }} />Детализация «Открытых» вакансий</>}>
              {!chart6Details.length ? (
                <NoData text="Нет промежуточных статусов" />
              ) : (
                <ResponsiveContainer width="100%" height={Math.max(200, chart6Details.length * 48 + 24)}>
                  <BarChart data={chart6Details} layout="vertical" barSize={26}
                    margin={{ top: 4, right: 80, bottom: 4, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: 12, fill: T.muted }} />
                    <YAxis type="category" dataKey="status" width={210} axisLine={false} tickLine={false} style={{ fontSize: 15, fill: T.sub }} />
                    <RTooltip content={<BarTip />} />
                    <Bar dataKey="value" radius={[0, 6, 6, 0]}>
                      {chart6Details.map((r, i) => (
                        <BCell key={i} fill={STATUS_COLOR[r.status] || PALETTE[i % PALETTE.length]} />
                      ))}
                      <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: 15, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {}
          <Col xs={24} lg={10}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><PieChartOutlined style={{ marginRight: 8, color: T.blue }} />Вакансии по статусам</>}>
              {bar2data.length === 0 ? <NoData /> : (
                <ResponsiveContainer width="100%" height={230}>
                  <BarChart data={bar2data} barSize={52} margin={{ top: 16, right: 20, bottom: 4, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} style={{ fontSize: 12, fill: T.sub }} />
                    <YAxis axisLine={false} tickLine={false} style={{ fontSize: 11, fill: T.muted }} />
                    <RTooltip content={<BarTip />} />
                    <Bar dataKey="value" radius={[6, 6, 0, 0]}>
                      {bar2data.map((b, i) => <BCell key={i} fill={b.fill} />)}
                      <LabelList dataKey="value" position="top" style={{ fontWeight: 700, fontSize: 13, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={14}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><FunnelPlotOutlined style={{ marginRight: 8, color: T.teal }} />Воронка найма</>}>
              {chart3.every(r => r.value === 0) ? <NoData /> : (
                <ResponsiveContainer width="100%" height={230}>
                  <BarChart data={chart3} layout="vertical" barSize={24} margin={{ top: 4, right: 64, bottom: 4, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: 11, fill: T.muted }} />
                    <YAxis type="category" dataKey="stage" width={175} axisLine={false} tickLine={false} style={{ fontSize: 13, fill: T.sub, fontWeight: 500 }} />
                    <RTooltip content={<BarTip />} />
                    <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                      {chart3.map((_, i) => <BCell key={i} fill={PALETTE[i]} />)}
                      <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: 13, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          {}
          <Col xs={24} lg={10}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><FieldTimeOutlined style={{ marginRight: 8, color: T.amber }} />Средний срок закрытия (раб. дни)</>}
              extra={
                <Radio.Group size="small" value={groupBy} onChange={e => setGroupBy(e.target.value)}
                  buttonStyle="solid">
                  <Radio.Button value="it_role">По ИТ ролям</Radio.Button>
                  <Radio.Button value="level">По Уровням</Radio.Button>
                </Radio.Group>
              }>
              {!chart5.length ? <NoData text="Нет данных по закрытым вакансиям" /> : (
                <ResponsiveContainer width="100%" height={Math.max(220, chart5.length * 44 + 40)}>
                  <BarChart data={chart5} layout="vertical" barSize={24}
                    margin={{ top: 4, right: 90, bottom: 4, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: 11, fill: T.muted }} />
                    <YAxis type="category" dataKey="label" width={175} axisLine={false} tickLine={false} style={{ fontSize: 13, fill: T.sub }} />
                    <RTooltip
                      content={({ active, payload, label }) => {
                        if (!active || !payload?.length) return null;
                        const d = payload[0].payload;
                        return (
                          <div style={{ background: '#fff', border: `1px solid ${T.border}`, borderRadius: 8, padding: '8px 12px', fontSize: 12, boxShadow: '0 4px 12px rgba(0,0,0,.1)' }}>
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
                        style={{ fontWeight: 700, fontSize: 13, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={14}>
            <Card style={CS} bodyStyle={CBS} headStyle={CHS}
              title={<><BankOutlined style={{ marginRight: 8, color: T.blue }} />Топ-15 компаний кандидатов</>}>
              {!chart4.length ? <NoData text="Нет данных о компаниях кандидатов" /> : (
                <ResponsiveContainer width="100%" height={Math.max(220, chart4.length * 38 + 40)}>
                  <BarChart data={chart4} layout="vertical" barSize={22}
                    margin={{ top: 4, right: 72, bottom: 4, left: 16 }}>
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f0f0f0" />
                    <XAxis type="number" axisLine={false} tickLine={false} style={{ fontSize: 12, fill: T.muted }} />
                    <YAxis type="category" dataKey="company" width={150} axisLine={false} tickLine={false} style={{ fontSize: 15, fill: T.sub }} />
                    <RTooltip content={<BarTip />} />
                    <Bar dataKey="value" radius={[0, 5, 5, 0]}>
                      {chart4.map((_, i) => <BCell key={i} fill={PALETTE[i % PALETTE.length]} />)}
                      <LabelList dataKey="value" position="right" style={{ fontWeight: 700, fontSize: 15, fill: T.text }} />
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              )}
            </Card>
          </Col>

        </Row>
      )}
    </div>
  );
}
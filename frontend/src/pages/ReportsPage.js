
import React, { useState, useCallback, useEffect, useRef } from 'react';
import { tokenStorage } from '../tokenStorage';
import {
  Button, Select, DatePicker, Input, message, Table, Modal, Tooltip,
} from 'antd';
import {
  DownloadOutlined, ReloadOutlined, ClearOutlined, SearchOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { api } from '../App';
import ReportsTour from '../components/ReportsTour';
import './statusRows.css';

dayjs.extend(isoWeek);

const { RangePicker } = DatePicker;
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;

const STATUS_ROW_CLASS = {
  'Открыта':                  'vt-row--open',
  'Согласование фин условий': 'vt-row--beige',
  'Проверка СБ':              'vt-row--beige',
  'Проверка сб':              'vt-row--beige',
  'Оффер':                    'vt-row--light-green',
  'Подготовка документов':    'vt-row--light-green',
  'Выход':                    'vt-row--light-green',
  'Закрыта':                  'vt-row--green',
  'Hold':                     'vt-row--blue',
  'Отмена':                   'vt-row--red',
};

const getRowClassName = (record) =>
  STATUS_ROW_CLASS[record.status_name] || '';

const WH = (text) => (
  <div style={{ whiteSpace: 'normal', lineHeight: '1.3', textAlign: 'center', fontWeight: 500 }}>
    {text}
  </div>
);

const PS_KEY  = 'rms_reports_page_size';
const loadPS  = () => { try { const v = parseInt(localStorage.getItem(PS_KEY), 10); return [25,50,100].includes(v) ? v : 50; } catch { return 50; } };
const savePS  = (s) => { try { localStorage.setItem(PS_KEY, String(s)); } catch {} };

const EXPORT_PERIODS = [
  { value: 'current_week',  label: 'За текущую неделю' },
  { value: 'current_month', label: 'За текущий месяц' },
  { value: 'current_year',  label: 'За текущий год' },
  { value: 'all_time',      label: 'За всё время' },
  { value: 'custom',        label: 'Произвольный период' },
];

const YEAR_OPTIONS = (() => {
  const y = dayjs().year();
  return [y, y-1, y-2].map(v => ({ value: v, label: String(v) }));
})();

const MONTH_OPTIONS = [
  {value:1,label:'Январь'},{value:2,label:'Февраль'},{value:3,label:'Март'},
  {value:4,label:'Апрель'},{value:5,label:'Май'},{value:6,label:'Июнь'},
  {value:7,label:'Июль'},{value:8,label:'Август'},{value:9,label:'Сентябрь'},
  {value:10,label:'Октябрь'},{value:11,label:'Ноябрь'},{value:12,label:'Декабрь'},
];

const generateWeekOptions = (year) => {
  const y = year || dayjs().year();
  const max = y === dayjs().year() ? dayjs().isoWeek() : 52;
  return Array.from({ length: max }, (_, i) => {
    const w = max - i;
    const s = dayjs().year(y).isoWeek(w).startOf('isoWeek');
    return { value: w, label: `Нед. ${w}: ${s.format('DD.MM')}-${s.add(6,'day').format('DD.MM')}` };
  });
};

const ReportsPage = () => {

  const [user, setUser] = useState(() => tokenStorage.getUser());

  const handleReportsTourComplete = useCallback(async () => {
    try {
      const { completeTour } = await import('../api');
      const updatedUser = await completeTour('reports');
      setUser(updatedUser);
      tokenStorage.setUser(updatedUser);
    } catch (err) {
      console.error('[Tour] Не удалось сохранить флаг тура:', err);
    }
  }, []);
  const [data,        setData]        = useState([]);
  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(false);
  const [pageSize,    setPageSize]    = useState(loadPS());
  const [curPage,     setCurPage]     = useState(1);
  

  const [sortField,   setSortField]   = useState(null);
  const [sortOrder,   setSortOrder]   = useState('desc');

  const [selYear,   setSelYear]   = useState(null);
  const [selMonth,  setSelMonth]  = useState(null);
  const [selWeek,   setSelWeek]   = useState(null);
  const [dateRange, setDateRange] = useState(null);

  const [searchVacancyId, setSearchVacancyId] = useState('');

  const [exportModal,   setExportModal]   = useState(false);
  const [exportPeriod,  setExportPeriod]  = useState('all_time');
  const [exportDates,   setExportDates]   = useState(null);
  const [exportLoading, setExportLoading] = useState(false);

  const tourRef = useRef();

  const weekOptions = generateWeekOptions(selYear || dayjs().year());

  const buildParams = useCallback(({
    page  = curPage,
    ps    = pageSize,
    sf    = sortField,
    so    = sortOrder,
    yr    = selYear,
    mo    = selMonth,
    wk    = selWeek,
    dr    = dateRange,
    svid  = searchVacancyId,
  } = {}) => {
    const p = new URLSearchParams();
    p.append('skip',  String((page - 1) * ps));
    p.append('limit', String(ps));

    if (sf) {
      p.append('sort_field', sf);
      p.append('sort_order', so === 'ascend' ? 'asc' : 'desc');
    }

    if (yr) p.append('year', yr);
    if (mo) p.append('month', mo);
    if (wk) p.append('week_number', wk);
    if (dr?.length === 2) {
      p.append('start_date', dr[0].format('YYYY-MM-DD'));
      p.append('end_date',   dr[1].format('YYYY-MM-DD'));
    }
    if (svid?.trim()) p.append('search_vacancy_id', svid.trim());

    return p;
  }, [curPage, pageSize, sortField, sortOrder, selYear, selMonth, selWeek, dateRange, searchVacancyId]);

  const fetchData = useCallback(async (overrides = {}) => {
    setLoading(true);
    try {
      const p   = buildParams(overrides);
      const res = await api.get(`/reports/all?${p.toString()}`);
      setData(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch { message.error('Ошибка загрузки отчётов'); }
    finally  { setLoading(false); }
  }, [buildParams]);

  useEffect(() => { fetchData(); }, []);

  const handleTableChange = (pag, filters, sorter) => {
    const sf = sorter.field || sorter.columnKey || null;
    const so = sorter.order || 'desc';
    if (pag.pageSize !== pageSize) savePS(pag.pageSize);
    
    setPageSize(pag.pageSize);
    setCurPage(pag.current);
    setSortField(sf);
    setSortOrder(so);

    fetchData({ page: pag.current, ps: pag.pageSize, sf, so });
  };

  const handleReset = () => {
    setSelYear(null); setSelMonth(null); setSelWeek(null); setDateRange(null);
    setSearchVacancyId('');
    setSortField(null); setSortOrder('desc');
    setCurPage(1);
    
    setLoading(true);
    const p = new URLSearchParams();
    p.append('skip', '0');
    p.append('limit', String(pageSize));
    api.get(`/reports/all?${p.toString()}`)
      .then(r => { setData(r.data.items || []); setTotal(r.data.total || 0); })
      .catch(() => message.error('Ошибка загрузки'))
      .finally(() => setLoading(false));
  };

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const token = tokenStorage.getAccess();
      const p = new URLSearchParams();

      if (exportPeriod === 'current_week') {
        const mon = dayjs().startOf('isoWeek');
        p.append('start_date', mon.format('YYYY-MM-DD'));
        p.append('end_date',   mon.add(6,'day').format('YYYY-MM-DD'));
      } else if (exportPeriod === 'current_month') {
        p.append('start_date', dayjs().startOf('month').format('YYYY-MM-DD'));
        p.append('end_date',   dayjs().endOf('month').format('YYYY-MM-DD'));
      } else if (exportPeriod === 'current_year') {
        p.append('start_date', dayjs().startOf('year').format('YYYY-MM-DD'));
        p.append('end_date',   dayjs().endOf('year').format('YYYY-MM-DD'));
      } else if (exportPeriod === 'custom' && exportDates?.length === 2) {
        p.append('start_date', exportDates[0].format('YYYY-MM-DD'));
        p.append('end_date',   exportDates[1].format('YYYY-MM-DD'));
      }
      
      if (sortField) {
        p.append('sort_field', sortField);
        p.append('sort_order', sortOrder === 'ascend' ? 'asc' : 'desc');
      }

      const resp = await fetch(`${BACKEND_URL}/api/reports/all/export?${p.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error();
      const blob = await resp.blob();
      const url  = window.URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url;
      const cd   = resp.headers.get('Content-Disposition');
      a.download = cd?.match(/filename="?(.+?)"?$/)?.[1] || 'reports_export.xlsx';
      document.body.appendChild(a); a.click();
      document.body.removeChild(a); window.URL.revokeObjectURL(url);
      setExportModal(false);
      message.success('Экспорт завершён');
    } catch { message.error('Ошибка экспорта'); }
    finally  { setExportLoading(false); }
  };

  const mkSort = (field) => ({
    sorter: true,
    sortOrder: sortField === field ? (sortOrder || null) : null,
  });

  const columns = [
    {
      title:'№', key:'_idx', width:50, fixed:'left', align:'center',
      render:(_,__,i) => (curPage-1)*pageSize + i + 1,
    },
    {
      title:'ID вакансии', dataIndex:'vacancy_ext_id', key:'vacancy_ext_id', width:130,
      render: v => v || '-',
    },
    {
      title:'Дата открытия', dataIndex:'open_date', key:'open_date', width:120,
      ...mkSort('open_date'),
      render: v => v ? dayjs(v).format('DD.MM.YY') : '-',
    },
    {
      title:WH('Кол-во'), dataIndex:'quantity', key:'quantity', width:80, align:'center',
      ...mkSort('quantity'),
      render: v => v ?? '-',
    },
    {
      title:'Уровень специалиста', dataIndex:'level_name', key:'level_name', width:130,
      render: v => v || '-',
    },
    {
      title:'Вакансия', dataIndex:'vacancy_name', key:'vacancy_name', width:170, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Статус вакансии', dataIndex:'status_name', key:'status_name', width:180,
      render: v => v ? <span style={{ fontSize:11 }}>{v}</span> : '-',
    },
    {
      title:'ИТ роль', dataIndex:'it_role_name', key:'it_role_name', width:140, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Адм. руководитель', dataIndex:'customer', key:'customer', width:180, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Тимлид', dataIndex:'team_lead_name', key:'team_lead_name', width:160, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Проект', dataIndex:'project_name', key:'project_name', width:150, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:WH('Передано заказчику'), dataIndex:'total_resumes_sent', key:'total_resumes_sent', width:130, align:'center',
      ...mkSort('total_resumes_sent'),
      render: v => <span style={{ fontWeight:500, color:'#1890FF' }}>{v ?? 0}</span>,
    },
    {
      title:WH('Резюме одобрено'), dataIndex:'total_candidates_agreed', key:'total_candidates_agreed', width:130, align:'center',
      ...mkSort('total_candidates_agreed'),
      render: v => <span style={{ fontWeight:500, color:'#52C41A' }}>{v ?? 0}</span>,
    },
    {
      title:WH('Соб. факт'), dataIndex:'total_interviews_conducted', key:'total_interviews_conducted', width:120, align:'center',
      ...mkSort('total_interviews_conducted'),
      render: v => <span style={{ fontWeight:500, color:'#722ED1' }}>{v ?? 0}</span>,
    },
    {
      title:WH('Соб. план'), dataIndex:'total_interviews_planned', key:'total_interviews_planned', width:120, align:'center',
      ...mkSort('total_interviews_planned'),
      render: v => <span style={{ fontWeight:500, color:'#FA8C16' }}>{v ?? 0}</span>,
    },
    {
      title:WH('Оффер'), dataIndex:'total_offer_made', key:'total_offer_made', width:100, align:'center',
      ...mkSort('total_offer_made'),
      render: v => <span style={{ fontWeight:500, color:'#EB2F96' }}>{v ?? 0}</span>,
    },
    {
      title:'Город', dataIndex:'city_name', key:'city_name', width:110,
      render: v => v || '-',
    },
    {
      title:'Источник найма', dataIndex:'source_name', key:'source_name', width:140,
      render: v => v || '-',
    },
    {
      title:'Внутр. перевод', dataIndex:'internal_transfer_name', key:'internal_transfer_name', width:140,
      render: v => v || '-',
    },
    {
      title:'Дата изм. статуса', dataIndex:'status_changed_at', key:'status_changed_at', width:130,
      render: v => v ? dayjs(v).format('DD.MM.YY') : '-',
    },
    {
      title:'Дата закрытия', dataIndex:'close_date', key:'close_date', width:120,
      render: v => v ? dayjs(v).format('DD.MM.YY') : '-',
    },
    {
      title:'ФИО кандидата', dataIndex:'candidate_name', key:'candidate_name', width:180, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Компания кандидата', dataIndex:'candidate_company', key:'candidate_company', width:160, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Новая / Замена', dataIndex:'replacement_type_name', key:'replacement_type_name', width:120,
      render: v => v || '-',
    },
    {
      title:'ФИО бывшего сотр.', dataIndex:'ex_employee_name', key:'ex_employee_name', width:170, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'ID ШЕ', dataIndex:'unit_id', key:'unit_id', width:110,
      render: v => v || '-',
    },
    {
      title:'Вид занятости', dataIndex:'employment_type_name', key:'employment_type_name', width:170,
      render: v => v || '-',
    },
    {
      title:'ТЭО проекта', dataIndex:'feasibility_name', key:'feasibility_name', width:150,
      render: v => v || '-',
    },
    {
      title:'IQHR', dataIndex:'iqhr_link', key:'iqhr_link', width:100, align:'center',
      render: v => v ? <a href={v} target="_blank" rel="noopener noreferrer" style={{ fontSize:11 }}>Открыть</a> : '-',
    },
    {
      title:'Рекрутер', dataIndex:'recruiter_name', key:'recruiter_name', width:160, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:'Блок', dataIndex:'block_name', key:'block_name', width:140, ellipsis:true,
      render: v => v || '-',
    },
    {
      title:WH('Срок работы (дней)'), dataIndex:'work_duration_days', key:'work_duration_days', width:110, align:'center',
      ...mkSort('work_duration_days'),
      render: v => v !== null && v !== undefined ? v : '-',
    },
    {
      title:WH('Зарплата кандидатов Gross'), dataIndex:'salary_gross', key:'salary_gross', width:150, align:'center',
      ...mkSort('salary_gross'),
      render: v => v !== null && v !== undefined ? Number(v).toLocaleString('ru-RU') : '-',
    },
    {
      title:'Год', dataIndex:'year', key:'year', width:90, align:'center',
      render: v => v || '-',
    },
    {
      title:WH('Кол-во отчётов'), dataIndex:'report_count', key:'report_count', width:110, align:'center',
    },
    {
      title:'Дата создания', dataIndex:'first_report_date', key:'first_report_date', width:150,
      render: v => v ? dayjs(v).format('DD.MM.YY HH:mm') : '-',
    },
    {
      title:'Дата обновления', dataIndex:'last_updated', key:'last_updated', width:150,
      render: v => v ? dayjs(v).format('DD.MM.YY HH:mm') : '-',
    },
  ];

  const hasFilters = selYear || selMonth || selWeek || dateRange || searchVacancyId?.trim();

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', gap:10 }}>

      <div style={{
        background:'#fff', padding:'10px 14px', borderRadius:6,
        display:'flex', flexWrap:'wrap', alignItems:'center', gap:8,
        boxShadow:'0 1px 3px rgba(0,0,0,0.06)', flexShrink:0,
      }}>
        {}
        <div
          data-tour-reports="filters"
          style={{ display:'flex', flexWrap:'wrap', alignItems:'center', gap:8 }}
        >
          <span style={{ fontSize:12, color:'#595959', fontWeight:500 }}>Период:</span>

          <Select placeholder="Год" value={selYear}
            onChange={v => { setSelYear(v); setSelWeek(null); }}
            allowClear style={{ width:90 }} options={YEAR_OPTIONS} size="small"
          />
          <Select placeholder="Месяц" value={selMonth} onChange={setSelMonth}
            allowClear style={{ width:120 }} options={MONTH_OPTIONS} size="small"
          />
          <Select placeholder="Неделя" value={selWeek} onChange={setSelWeek}
            allowClear style={{ width:260 }} options={weekOptions}
            showSearch optionFilterProp="label" size="small"
          />
          <RangePicker value={dateRange} onChange={setDateRange} format="DD.MM.YYYY"
            placeholder={['Начало','Конец']} style={{ width:230 }} size="small"
          />

          <Input.Search
            placeholder="Поиск по ID..."
            value={searchVacancyId}
            onChange={e => setSearchVacancyId(e.target.value)}
            onSearch={() => { setCurPage(1); fetchData({ page: 1, svid: searchVacancyId }); }}
            onPressEnter={() => { setCurPage(1); fetchData({ page: 1, svid: searchVacancyId }); }}
            allowClear
            onClear={() => { setSearchVacancyId(''); fetchData({ page: 1, svid: '' }); }}
            size="small"
            style={{ width: 180 }}
          />

          <Button type="primary" size="small"
            onClick={() => { setCurPage(1); fetchData({ page:1 }); }}>
            Применить
          </Button>
        </div>
        {}
        <Button size="small" icon={<ClearOutlined />} onClick={handleReset}
          disabled={!hasFilters && !sortField}
          data-tour-reports="reset-btn">
          Сбросить фильтры
        </Button>

        <div style={{ flex:1 }} />

        <Button size="small" icon={<ReloadOutlined />}
          onClick={() => fetchData()} title="Обновить"
          data-tour-reports="reload-btn" />
        {user?.role === 'recruiter' && (
          <Tooltip title="Обучение по работе с отчётами">
            <Button
              icon={<QuestionCircleOutlined />}
              size="small"
              onClick={() => tourRef.current?.start()}
              data-testid="reports-tour-button"
              data-tour-reports="tour-btn"
            />
          </Tooltip>
        )}
        <Button type="primary" size="small" icon={<DownloadOutlined />}
          onClick={() => setExportModal(true)}>
          Экспорт
        </Button>
      </div>

      <div data-tour-reports="table" style={{ flex:1, overflow:'hidden', background:'#fff', borderRadius:6 }}>
        <Table
          columns={columns}
          dataSource={data}
          rowKey="id"
          loading={loading}
          size="small"
          bordered
          rowClassName={getRowClassName}
          pagination={{
            current: curPage,
            pageSize,
            total,
            showSizeChanger: true,
            pageSizeOptions: ['25','50','100'],
            showTotal: t => `Всего: ${t}`,
          }}
          onChange={handleTableChange}
          scroll={{ x: 5000, y: 'calc(100vh - 235px)' }}
        />
      </div>

      <Modal
        title="Экспорт отчётов в Excel"
        open={exportModal}
        onCancel={() => setExportModal(false)}
        onOk={handleExport}
        okText="Скачать"
        cancelText="Отмена"
        confirmLoading={exportLoading}
        width={440}
      >
        <div style={{ marginBottom:16 }}>
          <label style={{ display:'block', marginBottom:8, fontWeight:500 }}>Выберите период:</label>
          <Select
            value={exportPeriod}
            onChange={v => { setExportPeriod(v); if (v !== 'custom') setExportDates(null); }}
            options={EXPORT_PERIODS}
            style={{ width:'100%' }}
          />
        </div>
        {exportPeriod === 'custom' && (
          <div style={{ marginBottom:16 }}>
            <label style={{ display:'block', marginBottom:8, fontWeight:500 }}>Выберите даты:</label>
            <RangePicker
              value={exportDates}
              onChange={setExportDates}
              format="DD.MM.YYYY"
              style={{ width:'100%' }}
              placeholder={['Дата начала','Дата конца']}
            />
          </div>
        )}
        <p style={{ color:'#8c8c8c', fontSize:12, margin:0 }}>
          Отчёты фильтруются по дате начала недели в выбранном периоде.
          Сортировка (если применена к колонке) также учитывается.
        </p>
      </Modal>

      <ReportsTour ref={tourRef} user={user} onComplete={handleReportsTourComplete} />
    </div>
  );
};

export default ReportsPage;

import React, { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { tokenStorage } from '../tokenStorage';
import {
  Button, Select, DatePicker, Input, message, Table, Modal, Tooltip, Space, Checkbox
} from 'antd';
import {
  DownloadOutlined, ReloadOutlined, ClearOutlined, SearchOutlined,
  QuestionCircleOutlined, FilterOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { api } from '../App';
import ReportsTour from '../components/ReportsTour';
import useIsMobile from '../hooks/useIsMobile';
import './statusRows.css';

dayjs.extend(isoWeek);

const { RangePicker } = DatePicker;
const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';

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
  <div style={{ whiteSpace: 'normal', lineHeight: '1.3', textAlign: 'center' }}>
    {text}
  </div>
);

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

const PS_KEY  = 'rms_reports_page_size';
const loadPS  = () => { try { const v = parseInt(localStorage.getItem(PS_KEY), 10); return [25,50,100].includes(v) ? v : 50; } catch { return 50; } };
const savePS  = (s) => { try { localStorage.setItem(PS_KEY, String(s)); } catch {} }

const EXPORT_PERIODS = [
  { value: 'current_filter', label: 'Текущий период на странице' },
  { value: 'current_week',   label: 'За текущую неделю' },
  { value: 'current_month',  label: 'За текущий месяц' },
  { value: 'current_year',   label: 'За текущий год' },
  { value: 'all_time',       label: 'За всё время' },
  { value: 'custom',         label: 'Произвольный период' },
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

// Ключи текстовых и числовых фильтров (значение — строка, не ID)
const TEXT_FILTER_KEYS = new Set([
  'vacancy_ext_id', 'vacancy_name', 'team_lead_name', 'city_name',
  'candidate_name', 'candidate_company', 'ex_employee_name', 'unit_id',
  'feasibility_name', 'iqhr_link', 'comment', 'offer_rejection_reason',
]);

const REPORTS_FILTERS_KEY = 'rms_reports_filters';
const loadSavedReportsFilters = () => {
  try {
    const s = sessionStorage.getItem(REPORTS_FILTERS_KEY);
    return s ? JSON.parse(s) : null;
  } catch { return null; }
};
const saveSavedReportsFilters = (data) => {
  try {
    if (!data) {
      sessionStorage.removeItem(REPORTS_FILTERS_KEY);
    } else {
      sessionStorage.setItem(REPORTS_FILTERS_KEY, JSON.stringify(data));
    }
  } catch {}
};

const NUMBER_FILTER_KEYS = new Set([
  'quantity', 'total_resumes_sent', 'total_candidates_agreed', 
  'total_interviews_planned', 'total_interviews_conducted', 
  'total_offer_made', 'total_offer_accepted', 'work_duration_days', 'salary_gross', 'report_count'
]);

const DATE_FILTER_KEYS = new Set(['open_date', 'close_date', 'status_changed_at']);

const getPopupContainer = () => document.body;

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
  filterIcon: filtered => <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
};

const NUMBER_FILTER_DROPDOWN = {
  filterDropdown: ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => (
    <div style={{ padding: 8 }}>
      <Input
        type="number"
        autoFocus
        placeholder="Число..."
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
  filterIcon: filtered => <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} />,
};

const ReportsPage = () => {

  const isMobile = useIsMobile();
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

  const [data, setData] = useState([]);
  const [dictionaries, setDictionaries] = useState({});

  useEffect(() => {
    const loadDictionaries = async () => {
      try {
        const types = [
          'specialist_level', 'vacancy_status', 'it_role', 'admin_manager',
          'project', 'source', 'internal_transfer', 'replacement_type',
          'employment_type', 'block', 'recruiter'
        ];
        const results = {};
        for (const type of types) {
          if (type === 'recruiter') continue;
          const response = await api.get(`/dictionaries/by-type/${type}`);
          results[type] = response.data;
        }
        const usersResp = await api.get('/users?limit=1000');
        results['recruiter'] = (usersResp.data.items || []).map(u => ({ id: u.id, value: u.full_name }));
        setDictionaries(results);
      } catch (error) {
        console.error('Failed to load dictionaries:', error);
      }
    };
    loadDictionaries();
  }, []);

  useEffect(() => {
    document.body.classList.add('no-page-scroll');
    return () => document.body.classList.remove('no-page-scroll');
  }, []);

  const [total,       setTotal]       = useState(0);
  const [loading,     setLoading]     = useState(false);
  const [pageSize,    setPageSize]    = useState(loadPS());
  const savedReportsFilters = useMemo(() => loadSavedReportsFilters(), []);

  const [curPage,     setCurPage]     = useState(() => savedReportsFilters?.curPage || 1);

  // Фильтры столбцов — как в VacancyTable (filteredInfo)
  const [filteredInfo, setFilteredInfo] = useState(() => savedReportsFilters?.filteredInfo || {});
  // Сортировка — ref для синхронного доступа + state для re-render
  const sortedInfoRef = useRef({});
  const [sortedInfo,  setSortedInfo]  = useState({});

  // Верхние фильтры по датам/периоду
  const [selYear,   setSelYear]   = useState(() => savedReportsFilters?.selYear ?? null);
  const [selMonth,  setSelMonth]  = useState(() => savedReportsFilters?.selMonth ?? null);
  const [selWeek,   setSelWeek]   = useState(() => savedReportsFilters?.selWeek ?? null);
  const [dateRange, setDateRange] = useState(() => {
    if (savedReportsFilters?.dateRange && savedReportsFilters.dateRange.length === 2) {
      return [dayjs(savedReportsFilters.dateRange[0]), dayjs(savedReportsFilters.dateRange[1])];
    }
    return null;
  });
  const [searchVacancyId, setSearchVacancyId] = useState(() => savedReportsFilters?.searchVacancyId || '');
  const [onlyActiveWork,  setOnlyActiveWork]  = useState(() => savedReportsFilters?.onlyActiveWork ?? false);

  const [exportModal,      setExportModal]      = useState(false);
  const [exportPeriod,     setExportPeriod]     = useState('current_filter');
  const [exportDates,      setExportDates]      = useState(null);
  const [exportOnlyActive, setExportOnlyActive] = useState(false);
  const [exportLoading,    setExportLoading]    = useState(false);

  const tourRef = useRef();

  const [columnWidths, setColumnWidths] = useState(() => {
    try {
      const saved = localStorage.getItem('rms_reports_column_widths');
      return saved ? JSON.parse(saved) : {};
    } catch {
      return {};
    }
  });

  const handleResize = useCallback((key, width) => {
    setColumnWidths(prev => {
      const next = { ...prev, [key]: width };
      try {
        localStorage.setItem('rms_reports_column_widths', JSON.stringify(next));
      } catch (err) {}
      return next;
    });
  }, []);

  // Request-ID: предотвращает перезапись данных устаревшими ответами
  const latestReqRef = useRef(0);

  const weekOptions = generateWeekOptions(selYear || dayjs().year());

  // ─── fetchData (паттерн VacancyTable) ────────────────────────────────────
  // filteredInfo, selYear, selMonth, selWeek, dateRange, searchVacancyId — в deps,
  // чтобы дефолты в сигнатуре всегда были актуальными.
  const fetchData = useCallback(async ({
    page  = curPage,
    ps    = pageSize,
    si    = sortedInfoRef.current,
    fi    = filteredInfo,
    yr    = selYear,
    mo    = selMonth,
    wk    = selWeek,
    dr    = dateRange,
    svid  = searchVacancyId,
    oaw   = onlyActiveWork,
  } = {}) => {
    const reqId = ++latestReqRef.current;
    setLoading(true);
    try {
      const p = new URLSearchParams();

      // TEXT_FILTER_KEYS, NUMBER_FILTER_KEYS → строки, остальные → массивы ID (словарные)
      // Бэкенд сам различает через get_str / get_list
      for (const [key, vals] of Object.entries(fi || {})) {
        if (!vals || vals.length === 0) continue;
        if (DATE_FILTER_KEYS.has(key)) {
          const val = Array.isArray(vals) ? vals[0] : vals;
          if (val != null && val !== '') {
            const parts = String(val).split('|');
            if (parts.length === 2) {
              const [from, to] = parts;
              const parseDate = (s) => {
                const d = dayjs(s, 'DD.MM.YY', true);
                return d.isValid() ? d.format('YYYY-MM-DD') : s;
              };
              if (from) p.append(`${key}_from`, parseDate(from));
              if (to)   p.append(`${key}_to`,   parseDate(to));
            } else {
              p.append(key, String(val));
            }
          }
        } else if (TEXT_FILTER_KEYS.has(key) || NUMBER_FILTER_KEYS.has(key)) {
          const val = String(Array.isArray(vals) ? vals[0] : vals).trim();
          if (val) p.append(key, val);
        } else {
          vals.forEach(v => p.append(key, String(v)));
        }
      }

      p.append('skip',  String((page - 1) * ps));
      p.append('limit', String(ps));

      // ── Сортировка ──
      const rawSorters = Array.isArray(si) ? si : (si && (si.field || si.columnKey) ? [si] : []);
      const validSorters = rawSorters.filter(s => s && s.order && (s.field || s.columnKey));
      if (validSorters.length > 0) {
        const sf = validSorters.map(s => s.field || s.columnKey);
        const so = validSorters.map(s => s.order === 'ascend' ? 'asc' : 'desc');
        p.append('sort_field', sf.join(','));
        p.append('sort_order', so.join(','));
      }

      // ── Верхние фильтры по периоду ──
      if (yr) p.append('year', yr);
      if (mo) p.append('month', mo);
      if (wk) p.append('week_number', wk);
      if (dr?.length === 2) {
        p.append('start_date', dr[0].format('YYYY-MM-DD'));
        p.append('end_date',   dr[1].format('YYYY-MM-DD'));
      }
      if (svid?.trim()) p.append('search_vacancy_id', svid.trim());
      if (oaw) p.append('only_active_work', 'true');

      const res = await api.get(`/reports/all?${p.toString()}`);

      // Игнорируем устаревшие ответы
      if (reqId !== latestReqRef.current) return;

      setData(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch (err) {
      if (reqId === latestReqRef.current) {
        message.error('Ошибка загрузки отчётов');
      }
    } finally {
      if (reqId === latestReqRef.current) setLoading(false);
    }
  }, [curPage, pageSize, filteredInfo, selYear, selMonth, selWeek, dateRange, searchVacancyId, onlyActiveWork]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    saveSavedReportsFilters({
      filteredInfo,
      selYear,
      selMonth,
      selWeek,
      dateRange: dateRange && dateRange[0] && dateRange[1] ? [dateRange[0].toISOString(), dateRange[1].toISOString()] : null,
      searchVacancyId,
      onlyActiveWork,
      curPage,
    });
  }, [filteredInfo, selYear, selMonth, selWeek, dateRange, searchVacancyId, onlyActiveWork, curPage]);

  useEffect(() => { fetchData(); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ─── handleTableChange (паттерн VacancyTable) ────────────────────────────
  const handleTableChange = useCallback((pag, filters, sorter) => {
    const newPage = pag.current  || 1;
    const newPs   = pag.pageSize || pageSize;
    let newSi     = sorter || null;
    if (Array.isArray(newSi)) {
      newSi = newSi.filter(s => s && s.order);
      if (newSi.length === 0) newSi = null;
    } else if (newSi && !newSi.order) {
      newSi = null;
    }
    const newFi   = filters || {};

    if (newPs !== pageSize) savePS(newPs);

    sortedInfoRef.current = newSi;
    setSortedInfo(newSi);
    setFilteredInfo(newFi);
    setCurPage(newPage);
    if (newPs !== pageSize) setPageSize(newPs);

    // Передаём всё явно — не зависим от замыкания
    fetchData({ page: newPage, ps: newPs, si: newSi, fi: newFi });
  }, [pageSize, fetchData]);

  // ─── Сброс фильтров столбцов ─────────────────────────────────────────────
  const handleResetTableFilters = useCallback(() => {
    sortedInfoRef.current = null;
    setSortedInfo(null);
    setFilteredInfo({});
    setCurPage(1);
    fetchData({ page: 1, si: null, fi: {} });
    message.success('Фильтры столбцов сброшены');
  }, [fetchData]);

  // Кол-во активных фильтров столбцов
  const activeTableFiltersCount = useMemo(() => {
    const filtersCount = Object.values(filteredInfo).filter(v => v && v.length > 0).length;
    const sortsCount = Array.isArray(sortedInfo)
      ? sortedInfo.filter(s => s && s.order).length
      : (sortedInfo?.order ? 1 : 0);
    return filtersCount + sortsCount;
  }, [filteredInfo, sortedInfo]);

  // ─── Сброс всего (верхние фильтры + столбцы) ─────────────────────────────
  const handleReset = useCallback(() => {
    setSelYear(null); setSelMonth(null); setSelWeek(null); setDateRange(null);
    setSearchVacancyId('');
    setOnlyActiveWork(false);
    sortedInfoRef.current = null;
    setSortedInfo(null);
    setFilteredInfo({});
    setCurPage(1);
    saveSavedReportsFilters(null);
    fetchData({ page: 1, si: null, fi: {}, yr: null, mo: null, wk: null, dr: null, svid: '', oaw: false });
  }, [fetchData]);

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const token = tokenStorage.getAccess();
      const p = new URLSearchParams();

      if (exportPeriod === 'current_filter') {
        if (selYear) p.append('year', selYear);
        if (selMonth) p.append('month', selMonth);
        if (selWeek) p.append('week_number', selWeek);
        if (dateRange?.length === 2) {
          p.append('start_date', dateRange[0].format('YYYY-MM-DD'));
          p.append('end_date',   dateRange[1].format('YYYY-MM-DD'));
        }
      } else if (exportPeriod === 'current_week') {
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

      if (exportOnlyActive) {
        p.append('only_active_work', 'true');
      }

      const si = sortedInfoRef.current;
      const rawSorters = Array.isArray(si) ? si : (si && (si.field || si.columnKey) ? [si] : []);
      const validSorters = rawSorters.filter(s => s && s.order && (s.field || s.columnKey));
      if (validSorters.length > 0) {
        const sf = validSorters.map(s => s.field || s.columnKey);
        const so = validSorters.map(s => s.order === 'ascend' ? 'asc' : 'desc');
        p.append('sort_field', sf.join(','));
        p.append('sort_order', so.join(','));
      }

      Object.entries(filteredInfo || {}).forEach(([k, vals]) => {
        if (!vals || vals.length === 0) return;
        if (DATE_FILTER_KEYS.has(k)) {
          const val = Array.isArray(vals) ? vals[0] : vals;
          if (val != null && val !== '') {
            const parts = String(val).split('|');
            if (parts.length === 2) {
              const [from, to] = parts;
              const parseDate = (s) => {
                const d = dayjs(s, 'DD.MM.YY', true);
                return d.isValid() ? d.format('YYYY-MM-DD') : s;
              };
              if (from) p.append(`${k}_from`, parseDate(from));
              if (to)   p.append(`${k}_to`,   parseDate(to));
            } else {
              p.append(k, String(val));
            }
          }
        } else if (TEXT_FILTER_KEYS.has(k) || NUMBER_FILTER_KEYS.has(k)) {
          const val = String(Array.isArray(vals) ? vals[0] : vals).trim();
          if (val) p.append(k, val);
        } else {
          vals.forEach(v => p.append(k, String(v)));
        }
      });

      const resp = await fetch(`${API_BASE}/reports/all/export?${p.toString()}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!resp.ok) throw new Error();
      const blob = await resp.blob();
      const url  = window.URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = url;
      const cd   = resp.headers.get('Content-Disposition');
      a.download = cd?.match(/filename="?(.+?)"?$/)?.[1] || 'reports_export.xlsx';
      document.body.appendChild(a); 
      a.click();
      setTimeout(() => {
        document.body.removeChild(a); 
        window.URL.revokeObjectURL(url);
      }, 1000);
      setExportModal(false);
      message.success('Экспорт завершён');
    } catch { message.error('Ошибка экспорта'); }
    finally  { setExportLoading(false); }
  };

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

  // ─── Хелпер для словарных фильтров ───────────────────────────────────────
  const dictFilter = useCallback((items) => ({
    filters: [
      ...(items || []).map(d => ({ text: d.value, value: d.id })),
      { text: 'Без указания', value: 0 },
    ],
    filterSearch: true,
    filterDropdownProps: { getPopupContainer },
  }), []);

  // ─── Колонки (useMemo как в VacancyTable) ────────────────────────────────
  const columns = useMemo(() => {
    const fi = filteredInfo;
    const rawColumns = [
      {
        title:'№', key:'_idx', width:50, fixed:'left', align:'center',
        render:(_,__,i) => (curPage-1)*pageSize + i + 1,
      },
      {
        title:'ID вакансии', dataIndex:'vacancy_ext_id', key:'vacancy_ext_id', width:130,
        ...mkSort('vacancy_ext_id'),
        filteredValue: fi['vacancy_ext_id'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Дата открытия', dataIndex:'open_date', key:'open_date', width:120,
        ...mkSort('open_date'),
        filteredValue: fi['open_date'] || null,
        ...DATE_FILTER_DROPDOWN,
        render: v => v ? dayjs(v).format('DD.MM.YY') : '-',
      },
      {
        title:WH('Кол-во'), dataIndex:'quantity', key:'quantity', width:80, align:'center',
        ...mkSort('quantity'),
        filteredValue: fi['quantity'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => v ?? '-',
      },
      {
        title:'Уровень специалиста', dataIndex:'level_name', key:'level_name', width:130,
        ...mkSort('level_name'),
        filteredValue: fi['level_name'] || null,
        ...dictFilter(dictionaries?.specialist_level),
        render: v => v || '-',
      },
      {
        title:'Вакансия', dataIndex:'vacancy_name', key:'vacancy_name', width:170, ellipsis:true,
        ...mkSort('vacancy_name'),
        filteredValue: fi['vacancy_name'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Статус вакансии', dataIndex:'status_name', key:'status_name', width:180,
        ...mkSort('status_name'),
        filteredValue: fi['status_name'] || null,
        ...dictFilter(dictionaries?.vacancy_status),
        render: v => v ? <span>{v}</span> : '-',
      },
      {
        title:'ИТ роль', dataIndex:'it_role_name', key:'it_role_name', width:140, ellipsis:true,
        ...mkSort('it_role_name'),
        filteredValue: fi['it_role_name'] || null,
        ...dictFilter(dictionaries?.it_role),
        render: v => v || '-',
      },
      {
        title:'Адм. руководитель', dataIndex:'admin_manager_name', key:'customer', width:180, ellipsis:true,
        ...mkSort('customer'),
        filteredValue: fi['customer'] || null,
        ...dictFilter(dictionaries?.admin_manager),
        render: v => v || '-',
      },
      {
        title:'Тимлид', dataIndex:'team_lead_name', key:'team_lead_name', width:160, ellipsis:true,
        ...mkSort('team_lead_name'),
        filteredValue: fi['team_lead_name'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Проект', dataIndex:'project_name', key:'project_name', width:150, ellipsis:true,
        ...mkSort('project_name'),
        filteredValue: fi['project_name'] || null,
        ...dictFilter(dictionaries?.project),
        render: v => v || '-',
      },
      {
        title:WH('Передано заказчику'), dataIndex:'total_resumes_sent', key:'total_resumes_sent', width:130, align:'center',
        ...mkSort('total_resumes_sent'),
        filteredValue: fi['total_resumes_sent'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => <span style={{ fontWeight:500, color:'#1890FF' }}>{v ?? 0}</span>,
      },
      {
        title:WH('Резюме одобрено'), dataIndex:'total_candidates_agreed', key:'total_candidates_agreed', width:130, align:'center',
        ...mkSort('total_candidates_agreed'),
        filteredValue: fi['total_candidates_agreed'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => <span style={{ fontWeight:500, color:'#52C41A' }}>{v ?? 0}</span>,
      },
      {
        title:WH('Соб. факт'), dataIndex:'total_interviews_conducted', key:'total_interviews_conducted', width:120, align:'center',
        ...mkSort('total_interviews_conducted'),
        filteredValue: fi['total_interviews_conducted'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => <span style={{ fontWeight:500, color:'#722ED1' }}>{v ?? 0}</span>,
      },
      {
        title:WH('Соб. план'), dataIndex:'total_interviews_planned', key:'total_interviews_planned', width:120, align:'center',
        ...mkSort('total_interviews_planned'),
        filteredValue: fi['total_interviews_planned'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => <span style={{ fontWeight:500, color:'#FA8C16' }}>{v ?? 0}</span>,
      },
      {
        title:'Оффер', dataIndex:'total_offer_made', key:'total_offer_made', width: 110, align: 'center',
        ...mkSort('total_offer_made'),
        filteredValue: fi['total_offer_made'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => <span style={{ fontWeight:500, color:'#EB2F96' }}>{v ?? 0}</span>,
      },
      {
        title:WH('Оффер принят'), dataIndex:'total_offer_accepted', key:'total_offer_accepted', width: 110, align: 'center',
        ...mkSort('total_offer_accepted'),
        filteredValue: fi['total_offer_accepted'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => <span style={{ fontWeight:500, color:'#52C41A' }}>{v ?? 0}</span>,
      },
      {
        title:'Причина отказа от Оффера', dataIndex:'offer_rejection_reason', key:'offer_rejection_reason', width: 170, ellipsis: true,
        ...mkSort('offer_rejection_reason'),
        filteredValue: fi['offer_rejection_reason'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Город', dataIndex:'city_name', key:'city_name', width:110,
        ...mkSort('city_name'),
        filteredValue: fi['city_name'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Источник найма', dataIndex:'source_name', key:'source_name', width:140,
        ...mkSort('source_name'),
        filteredValue: fi['source_name'] || null,
        ...dictFilter(dictionaries?.source),
        render: v => v || '-',
      },
      {
        title:'Внутр. перевод', dataIndex:'internal_transfer_name', key:'internal_transfer_name', width:140,
        ...mkSort('internal_transfer_name'),
        filteredValue: fi['internal_transfer_name'] || null,
        ...dictFilter(dictionaries?.internal_transfer),
        render: v => v || '-',
      },
      {
        title:'Дата изм. статуса', dataIndex:'status_changed_at', key:'status_changed_at', width:130,
        ...mkSort('status_changed_at'),
        filteredValue: fi['status_changed_at'] || null,
        ...DATE_FILTER_DROPDOWN,
        render: v => v ? dayjs(v).format('DD.MM.YY') : '-',
      },
      {
        title:'Дата закрытия', dataIndex:'close_date', key:'close_date', width:120,
        ...mkSort('close_date'),
        filteredValue: fi['close_date'] || null,
        ...DATE_FILTER_DROPDOWN,
        render: v => v ? dayjs(v).format('DD.MM.YY') : '-',
      },
      {
        title:'ФИО кандидата', dataIndex:'candidate_name', key:'candidate_name', width:180, ellipsis:true,
        ...mkSort('candidate_name'),
        filteredValue: fi['candidate_name'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Комментарий', dataIndex:'comment', key:'comment', width:180, ellipsis:true,
        ...mkSort('comment'),
        filteredValue: fi['comment'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Компания кандидата', dataIndex:'candidate_company', key:'candidate_company', width:160, ellipsis:true,
        ...mkSort('candidate_company'),
        filteredValue: fi['candidate_company'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Новая / Замена', dataIndex:'replacement_type_name', key:'replacement_type_name', width:120,
        ...mkSort('replacement_type_name'),
        filteredValue: fi['replacement_type_name'] || null,
        ...dictFilter(dictionaries?.replacement_type),
        render: v => v || '-',
      },
      {
        title:'ФИО бывшего сотр.', dataIndex:'ex_employee_name', key:'ex_employee_name', width:170, ellipsis:true,
        ...mkSort('ex_employee_name'),
        filteredValue: fi['ex_employee_name'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'ID ШЕ', dataIndex:'unit_id', key:'unit_id', width:110,
        ...mkSort('unit_id'),
        filteredValue: fi['unit_id'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Вид занятости', dataIndex:'employment_type_name', key:'employment_type_name', width:170,
        ...mkSort('employment_type_name'),
        filteredValue: fi['employment_type_name'] || null,
        ...dictFilter(dictionaries?.employment_type),
        render: v => v || '-',
      },
      {
        title:'ТЭО проекта', dataIndex:'feasibility_name', key:'feasibility_name', width:150,
        ...mkSort('feasibility_name'),
        filteredValue: fi['feasibility_name'] || null,
        ...TEXT_FILTER_DROPDOWN,
        render: v => v || '-',
      },
      {
        title:'Ссылка IQHR', dataIndex:'iqhr_link', key:'iqhr_link', width:140, ellipsis:true,
        ...mkSort('iqhr_link'),
        filteredValue: fi['iqhr_link'] || null,
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
        title:'Рекрутер', dataIndex:'recruiter_name', key:'recruiter_name', width:160, ellipsis:true,
        ...mkSort('recruiter_name'),
        filteredValue: fi['recruiter_name'] || null,
        ...dictFilter(dictionaries?.recruiter),
        render: (v, r) => v || r.recruiter?.full_name || '-',
      },
      {
        title:'Доп. рекрутер', dataIndex:'co_recruiter_name', key:'co_recruiter_name', width:160, ellipsis:true,
        ...mkSort('co_recruiter_name'),
        filteredValue: fi['co_recruiter_name'] || null,
        ...dictFilter(dictionaries?.recruiter),
        render: (v, r) => v || r.co_recruiter?.full_name || '-',
      },
      {
        title:'Блок', dataIndex:'block_name', key:'block_name', width:140, ellipsis:true,
        ...mkSort('block_name'),
        filteredValue: fi['block_name'] || null,
        ...dictFilter(dictionaries?.block),
        render: v => v || '-',
      },
      {
        title:WH('Срок работы (дней)'), dataIndex:'work_duration_days', key:'work_duration_days', width:110, align:'center',
        ...mkSort('work_duration_days'),
        filteredValue: fi['work_duration_days'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => v !== null && v !== undefined ? v : '-',
      },
      {
        title:WH('Зарплата кандидатов Gross'), dataIndex:'salary_gross', key:'salary_gross', width:150, align:'center',
        ...mkSort('salary_gross'),
        filteredValue: fi['salary_gross'] || null,
        ...NUMBER_FILTER_DROPDOWN,
        render: v => v !== null && v !== undefined ? Number(v).toLocaleString('ru-RU') : '-',
      },
      {
        title:'Год', dataIndex:'year', key:'year', width:90, align:'center',
        ...mkSort('year'),
        render: v => v || '-',
      },
      {
        title:WH('Кол-во отчётов'), dataIndex:'report_count', key:'report_count', width:110, align:'center',
        ...mkSort('report_count'),
        filteredValue: fi['report_count'] || null,
        ...NUMBER_FILTER_DROPDOWN,
      },
      {
        title:'Дата создания', dataIndex:'first_report_date', key:'first_report_date', width:150,
        ...mkSort('first_report_date'),
        render: v => v ? dayjs(v).format('DD.MM.YY HH:mm') : '-',
      },
      {
        title:'Дата обновления', dataIndex:'last_updated', key:'last_updated', width:150,
        ...mkSort('last_updated'),
        render: v => v ? dayjs(v).format('DD.MM.YY HH:mm') : '-',
      },
    ];

    return rawColumns.map(col => {
      const savedWidth = columnWidths[col.key];
      const widthVal = savedWidth ? Math.min(800, Math.max(80, savedWidth)) : (col.width ? Math.min(800, Math.max(80, col.width)) : 80);
      
      const updatedCol = {
        ...col,
        width: col.key === '_idx' ? 50 : widthVal,
      };

      if (!col.key || col.key === '_idx') return updatedCol;

      return {
        ...updatedCol,
        onHeaderCell: (c) => ({
          width: c.width,
          onResize: (width) => handleResize(col.key, width),
        }),
      };
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filteredInfo, sortedInfo, dictionaries, curPage, pageSize, dictFilter, columnWidths, handleResize]);

  const tableWidth = useMemo(() => {
    return columns.reduce((acc, col) => acc + (col.width || 100), 0);
  }, [columns]);

  const hasTopFilters = selYear || selMonth || selWeek || dateRange || searchVacancyId?.trim() || onlyActiveWork;

  return (
    <div style={{ display:'flex', flexDirection:'column', height:'100%', gap:10 }}>

      {/* ── Верхняя панель фильтров ── */}
      <div className="table-toolbar" style={{
        padding:'10px 14px', borderRadius:6,
        display:'flex', flexWrap:'wrap', alignItems:'center', gap:8,
        boxShadow:'0 1px 3px rgba(0,0,0,0.06)', flexShrink:0,
      }}>
        <div
          data-tour-reports="filters"
          style={{ display:'flex', flexWrap:'wrap', alignItems:'center', gap:8 }}
        >
          <span style={{ fontSize:12, color:'#595959', fontWeight:500 }}>Период:</span>

          <Select placeholder="Год" value={selYear}
            onChange={v => { setSelYear(v); setSelWeek(null); }}
            allowClear style={{ width: isMobile ? 70 : 90 }} options={YEAR_OPTIONS} size="small"
          />
          <Select placeholder="Месяц" value={selMonth} onChange={setSelMonth}
            allowClear style={{ width: isMobile ? 90 : 120 }} options={MONTH_OPTIONS} size="small"
          />
          <Select placeholder="Неделя" value={selWeek} onChange={setSelWeek}
            allowClear style={{ width: isMobile ? '100%' : 260 }} options={weekOptions}
            showSearch optionFilterProp="label" size="small"
          />
          <RangePicker value={dateRange} onChange={setDateRange} format="DD.MM.YYYY"
            placeholder={['Начало','Конец']} style={{ width: isMobile ? '100%' : 230 }} size="small"
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
            style={{ width: isMobile ? '100%' : 180 }}
          />

          <Button type="primary" size="small"
            onClick={() => { setCurPage(1); fetchData({ page:1 }); }}>
            Применить
          </Button>

          <Checkbox
            checked={onlyActiveWork}
            onChange={e => {
              const val = e.target.checked;
              setOnlyActiveWork(val);
              setCurPage(1);
              fetchData({ page: 1, oaw: val });
            }}
            style={{ fontSize: 12, whiteSpace: 'nowrap', userSelect: 'none', marginLeft: 4 }}
          >
            Только с движениями за период
          </Checkbox>
        </div>

        <Button size="small" icon={<ClearOutlined />} onClick={handleReset}
          disabled={!hasTopFilters && !sortedInfo?.order && activeTableFiltersCount === 0}
          data-tour-reports="reset-btn">
          Сбросить всё
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
          onClick={() => { setExportOnlyActive(onlyActiveWork); setExportModal(true); }}>
          Экспорт
        </Button>
      </div>

      {/* ── Таблица ── */}
      <div data-tour-reports="table" style={{ flex:1, overflow:'hidden', background:'var(--card-bg)', borderRadius:6 }}>
        {/* Строка активных фильтров столбцов */}
        {activeTableFiltersCount > 0 && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            padding: '5px 12px',
            background: 'var(--layout-bg)',
            borderBottom: '1px solid var(--border-color)',
            borderRadius: '6px 6px 0 0',
          }}>
            <FilterOutlined style={{ color: 'var(--text-color)', fontSize: 13 }} />
            <span style={{ fontSize: 12, color: 'var(--text-color)', fontWeight: 500 }}>
              Активных фильтров по столбцам: {activeTableFiltersCount}
            </span>
            <Button
              size="small"
              type="link"
              danger
              icon={<ClearOutlined />}
              onClick={handleResetTableFilters}
              style={{ marginLeft: 4, padding: '0 6px', fontSize: 12, height: 22 }}
            >
              Сбросить фильтры столбцов
            </Button>
          </div>
        )}
        <Table
          components={{
            header: {
              cell: ResizableHeaderCell,
            },
          }}
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
          scroll={{ x: tableWidth, y: 'calc(100vh - 350px)' }}
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
        width={isMobile ? '95vw' : 440}
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
        <div style={{ marginBottom:16 }}>
          <Checkbox
            checked={exportOnlyActive}
            onChange={e => setExportOnlyActive(e.target.checked)}
          >
            Только вакансии с движениями за период
          </Checkbox>
        </div>
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
import { tokenStorage } from '../tokenStorage';
import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Button, Select, Space, Modal, Form, Input,
  InputNumber, DatePicker, message, Drawer, Divider, Checkbox, Row, Col
} from 'antd';
import { PlusOutlined, CheckCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { api } from '../App';
import VacancyTable from './VacancyTable';

dayjs.extend(isoWeek);

const { RangePicker } = DatePicker;

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';
const EXPORT_PERIODS = [
  { value: 'current_week', label: 'За текущую неделю' },
  { value: 'current_month', label: 'За текущий месяц' },
  { value: 'current_year', label: 'За текущий год' },
  { value: 'all_time', label: 'За всё время' },
  { value: 'custom', label: 'Произвольный период' },
];

const generateWeekOptions = () => {
  const options = [];
  const currentWeek = dayjs().isoWeek();
  const currentYear = dayjs().year();
  
  for (let w = currentWeek; w >= 1; w--) {
    const weekStart = dayjs().year(currentYear).isoWeek(w).startOf('isoWeek');
    const weekEnd = weekStart.add(6, 'day');
    options.push({
      value: `${currentYear}-${w}`,
      label: `Неделя ${w} (${weekStart.format('DD.MM')} - ${weekEnd.format('DD.MM.YY')})`,
      week: w,
      year: currentYear,
    });
  }
  
  return options;
};


const HighlightFormItem = (props) => {
  return (
    <Form.Item noStyle dependencies={[props.name]}>
      {({ getFieldValue }) => {
        const val = getFieldValue(props.name);
        const isEmpty = val === undefined || val === null || val === '' || (Array.isArray(val) && val.length === 0);
        return (
          <Form.Item 
            {...props} 
            className={`${props.className || ''} ${props.editing && isEmpty ? 'highlight-empty-field' : ''}`}
          >
            {props.children}
          </Form.Item>
        );
      }}
    </Form.Item>
  );
};

const DashboardPage = () => {

  const actionRef = useRef();
  const [form] = Form.useForm();
  const [reportForm] = Form.useForm();

  const [dictionaries, setDictionaries] = useState({});
  const [users, setUsers] = useState([]);
  const [drawerVisible, setDrawerVisible] = useState(false);
  const [editingVacancy, setEditingVacancy] = useState(null);
  const [loading, setLoading] = useState(false);
  const [tableKey, setTableKey] = useState(0);
  

  const [tableState, setTableState] = useState({ filters: {}, sorter: {} });
  

  const [exportModalVisible, setExportModalVisible] = useState(false);
  const [exportPeriod, setExportPeriod] = useState('all_time');
  const [exportCustomDates, setExportCustomDates] = useState(null);
  const [exportWithFilters, setExportWithFilters] = useState(true);
  const [exportLoading, setExportLoading] = useState(false);
  

  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportVacancy, setReportVacancy] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [weekOptions] = useState(generateWeekOptions());

  const [editingReportId, setEditingReportId] = useState(null);

  const [user, setUser] = useState(() => tokenStorage.getUser() || {});
  const isRecruiter = user?.role === 'recruiter';

  const excludedStatuses = isRecruiter ? (dictionaries.vacancy_status || [])
    .filter(d => d.value === 'Закрыта' || d.value === 'Отмена')
    .map(d => d.id) : [];

  console.log("DEBUG DashboardPage:", {
    user_role: user?.role,
    isRecruiter,
    vacancy_status_exists: !!dictionaries.vacancy_status,
    vacancy_status_len: dictionaries.vacancy_status ? dictionaries.vacancy_status.length : 0,
    excludedStatuses
  });

  const handleVacanciesTourComplete = useCallback(async () => {
    try {
      const { completeTour } = await import('../api');
      const updatedUser = await completeTour('vacancies');
      setUser(updatedUser);
      tokenStorage.setUser(updatedUser);
    } catch (err) {
      console.error('[Tour] Не удалось сохранить флаг тура:', err);
    }
  }, []);

  useEffect(() => {
    loadDictionaries();
    loadUsers();
  }, []);

  const loadDictionaries = async () => {
    try {
      const types = [
        'specialist_level', 'vacancy_status', 'it_role', 'project',
        'source', 'employment_type', 'replacement_type', 'feasibility',
        'block', 'admin_manager', 'internal_transfer'
      ];
      const results = {};
      for (const type of types) {
        try {
          const response = await api.get(`/dictionaries/by-type/${type}`);
          results[type] = response.data;
        } catch (e) {
          results[type] = [];
        }
      }
      setDictionaries(results);
    } catch (error) {
      console.error('Failed to load dictionaries:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await api.get('/users?limit=100');
      setUsers(response.data.items || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const handleCreate = () => {
    setEditingVacancy(null);
    form.resetFields();
    if (isRecruiter && user?.id) {
      form.setFieldsValue({ recruiter_id: user.id });
    }
    setDrawerVisible(true);
  };

  const handleEdit = (record) => {
    setEditingVacancy(record);

    form.setFieldsValue({
      ...record,
      open_date: record.open_date ? dayjs(record.open_date) : null,
      close_date: record.close_date ? dayjs(record.close_date) : null,
      status_changed_at: record.status_changed_at ? dayjs(record.status_changed_at) : null,

      resume_at_customer: record.resume_at_customer || 0,
      resume_approved:    record.resume_approved    || 0,
      interviews_fact:    record.interviews_fact    || 0,
      interviews_plan:    record.interviews_plan    || 0,
      offer_made:         record.offer_made         || 0,
    });
    setDrawerVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const payload = {
        ...values,
        open_date: values.open_date?.format('YYYY-MM-DD'),
        close_date: values.close_date?.format('YYYY-MM-DD'),
        status_changed_at: values.status_changed_at?.format('YYYY-MM-DD'),
      };
      if (editingVacancy) {
        await api.patch(`/vacancies/${editingVacancy.id}`, payload);
        message.success('Вакансия обновлена');
      } else {
        await api.post('/vacancies', payload);
        message.success('Вакансия создана');
      }
      setDrawerVisible(false);
      actionRef.current?.reload();
    } catch (error) {
      console.error('Save error:', error);
      message.error(error.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = (id) => {
    Modal.confirm({
      title: 'Удалить вакансию?',
      content: 'Это действие нельзя отменить.',
      okText: 'Удалить',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: async () => {
        try {
          await api.delete(`/vacancies/${id}`);
          message.success('Вакансия удалена');
          actionRef.current?.reload();
        } catch (error) {
          message.error(error.response?.data?.detail || 'Ошибка удаления');
        }
      },
    });
  };
  
  const handleTableStateChange = useCallback((state) => {
    setTableState(state);
  }, []);

  const handleResetRequest = useCallback(() => {
    setTableKey(k => k + 1);
  }, []);
  
  const hasActiveFilters = tableState.filters && 
    Object.values(tableState.filters).some(v => v && v.length > 0);

  const handleExport = async () => {
    setExportLoading(true);
    try {
      const token = tokenStorage.getAccess();
      const params = new URLSearchParams();
      params.append('period', exportPeriod);
      if (excludedStatuses && excludedStatuses.length > 0) {
        excludedStatuses.forEach(id => params.append('exclude_status_id', id));
      }

      if (exportPeriod === 'custom' && exportCustomDates && exportCustomDates.length === 2) {
        params.append('start_date', exportCustomDates[0].format('YYYY-MM-DD'));
        params.append('end_date', exportCustomDates[1].format('YYYY-MM-DD'));
      }

      if (exportWithFilters && hasActiveFilters) {
        const filters = tableState.filters;
        const filterKeys = [
          'status_id', 'project_id', 'recruiter_id', 'it_role_id',
          'level_id', 'source_id', 'block_id',
          'employment_type_id', 'feasibility_id', 'replacement_type_id',
          'admin_manager_id', 'internal_transfer_id',
        ];
        for (const key of filterKeys) {
          if (filters[key]?.length) {
            for (const val of filters[key]) {
              params.append(key, val);
            }
          }
        }
        const textKeys = [
          'vacancy_id', 'position_name', 'candidate_name', 'candidate_company',
          'ex_employee_name', 'unit_id', 'salary_gross', 'iqhr_link',
          'city_text', 'team_lead_text',
        ];
        for (const key of textKeys) {
          if (filters[key]?.[0]) {
            params.append(`search_${key}`, filters[key][0]);
          }
        }
      }

      const url = `${API_BASE}/export/vacancies?${params.toString()}`;
      const response = await fetch(url, {
        method: 'GET',
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (!response.ok) throw new Error(`Export failed: ${response.status}`);

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;

      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = 'vacancies_export.xlsx';
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?(.+?)"?$/);
        if (match && match[1]) filename = match[1];
      }

      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      window.URL.revokeObjectURL(downloadUrl);

      setExportModalVisible(false);
      message.success('Экспорт завершен');
    } catch (error) {
      console.error('Export error:', error);
      message.error('Ошибка экспорта');
    } finally {
      setExportLoading(false);
    }
  };

  const handleReportClick = async (vacancy) => {
    setReportVacancy(vacancy);
    setEditingReportId(null);
    const currentWeek = dayjs().isoWeek();
    const currentYear = dayjs().year();
    const weekPeriod = `${currentYear}-${currentWeek}`;

    reportForm.resetFields();
    reportForm.setFieldsValue({
      week_period: weekPeriod,
      resumes_sent: 0,
      candidates_agreed: 0,
      interviews_planned: 0,
      interviews_conducted: 0,
      offer_made: 0,
    });
    setReportModalVisible(true);

    try {
      const res = await api.get(`/reports/vacancy/${vacancy.id}`);
      const reports = res.data.items || [];
      const existing = reports.find(r => r.week_number === currentWeek && r.year === currentYear);
      if (existing) {
        setEditingReportId(existing.id);
        reportForm.setFieldsValue({
          resumes_sent: existing.resumes_sent || 0,
          candidates_agreed: existing.candidates_agreed || 0,
          interviews_planned: existing.interviews_planned || 0,
          interviews_conducted: existing.interviews_conducted || 0,
          offer_made: existing.offer_made || 0,
        });
      }
    } catch {

    }
  };

  const handleWeekPeriodChange = async (value) => {
    if (!reportVacancy || !value) return;
    try {
      const [year, week] = value.split('-').map(Number);
      const res = await api.get(`/reports/vacancy/${reportVacancy.id}`);
      const reports = res.data.items || [];
      const existing = reports.find(r => r.week_number === week && r.year === year);
      if (existing) {
        setEditingReportId(existing.id);
        reportForm.setFieldsValue({
          resumes_sent: existing.resumes_sent || 0,
          candidates_agreed: existing.candidates_agreed || 0,
          interviews_planned: existing.interviews_planned || 0,
          interviews_conducted: existing.interviews_conducted || 0,
          offer_made: existing.offer_made || 0,
        });
        message.info('Найден существующий отчёт за эту неделю — данные загружены для редактирования');
      } else {
        setEditingReportId(null);
        reportForm.setFieldsValue({
          resumes_sent: 0,
          candidates_agreed: 0,
          interviews_planned: 0,
          interviews_conducted: 0,
          offer_made: 0,
        });
      }
    } catch {

    }
  };

  const handleReportSave = async () => {
    try {
      const values = await reportForm.validateFields();
      setReportLoading(true);
      
      const [year, week] = values.week_period.split('-').map(Number);
      
      const payload = {
        resumes_sent: values.resumes_sent || 0,
        candidates_agreed: values.candidates_agreed || 0,
        interviews_planned: values.interviews_planned || 0,
        interviews_conducted: values.interviews_conducted || 0,
        offer_made: values.offer_made || 0,
      };

      if (editingReportId) {

        await api.patch(`/reports/${editingReportId}`, payload);
        message.success('Отчёт обновлён.');
      } else {

        await api.post('/reports', {
          vacancy_id: reportVacancy.id,
          week_number: week,
          year: year,
          ...payload,
        });
        message.success('Отчёт сохранён.');
      }

      setReportModalVisible(false);
      setEditingReportId(null);

      actionRef.current?.reload();
    } catch (error) {
      console.error('Report save error:', error);
      message.error(error.response?.data?.detail || 'Ошибка сохранения отчёта');
    } finally {
      setReportLoading(false);
    }
  };

  return (
    <div data-testid="dashboard-page" className="vacancy-table-container">
      <VacancyTable
        excludeStatusIds={excludedStatuses}
        actionRef={actionRef}
        tableKey={tableKey}
        dictionaries={dictionaries}
        users={users}
        user={user}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onCreate={handleCreate}
        onReportClick={handleReportClick}
        onExportClick={() => setExportModalVisible(true)}
        onTableStateChange={handleTableStateChange}
        onResetRequest={handleResetRequest}
        onTourComplete={handleVacanciesTourComplete}
      />

      {}
      <Modal
        title="Экспорт вакансий в Excel"
        open={exportModalVisible}
        onCancel={() => setExportModalVisible(false)}
        onOk={handleExport}
        okText="Скачать"
        cancelText="Отмена"
        confirmLoading={exportLoading}
        width={480}
        data-testid="export-modal"
      >
        <div style={{ marginBottom: 20 }}>
          <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Выберите период:</label>
          <Select
            value={exportPeriod}
            onChange={(val) => {
              setExportPeriod(val);
              if (val !== 'custom') setExportCustomDates(null);
            }}
            options={EXPORT_PERIODS}
            style={{ width: '100%' }}
            data-testid="export-period-select"
          />
        </div>

        {}
        {exportPeriod === 'custom' && (
          <div style={{ marginBottom: 20 }}>
            <label style={{ display: 'block', marginBottom: 8, fontWeight: 500 }}>Выберите даты:</label>
            <RangePicker
              value={exportCustomDates}
              onChange={setExportCustomDates}
              format="DD.MM.YYYY"
              style={{ width: '100%' }}
              data-testid="export-custom-dates"
              placeholder={['Дата начала', 'Дата конца']}
            />
          </div>
        )}

        <div style={{
          padding: 16,
          border: '1px solid #91D5FF',
          borderRadius: 6,
          background: '#F0F8FF',
          marginBottom: 16,
        }}>
          <Checkbox
            checked={exportWithFilters}
            onChange={e => setExportWithFilters(e.target.checked)}
            data-testid="export-with-filters-checkbox"
          >
            <span style={{ fontWeight: 500 }}>Выгрузить с учетом текущих фильтров</span>
          </Checkbox>
          {hasActiveFilters && exportWithFilters && (
            <div style={{ marginTop: 8, fontSize: 13, color: '#0050B3' }}>
              <CheckCircleOutlined style={{ marginRight: 4 }} />
              Обнаружены активные фильтры в таблице. При включенной опции в Excel попадут только отфильтрованные записи.
            </div>
          )}
          {!hasActiveFilters && exportWithFilters && (
            <div style={{ marginTop: 8, fontSize: 13, color: '#8C8C8C' }}>
              Активных фильтров нет. Будут экспортированы все записи за период.
            </div>
          )}
        </div>

        <p style={{ color: '#8c8c8c', fontSize: 12 }}>
          Вакансии фильтруются по дате открытия в указанном периоде.
        </p>
      </Modal>

      {}
      <Modal
        title={editingReportId ? 'Редактировать отчёт' : 'Добавить отчёт'}
        open={reportModalVisible}
        onCancel={() => { setReportModalVisible(false); setEditingReportId(null); }}
        onOk={handleReportSave}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={reportLoading}
        width={480}
        data-testid="report-modal"
      >
        {reportVacancy && (
          <>
            <div style={{ marginBottom: 16, padding: 12, background: '#f5f5f5', borderRadius: 4 }}>
              <div style={{ fontWeight: 500, marginBottom: 4 }}>{reportVacancy.position_name}</div>
              <div style={{ fontSize: 12, color: '#8c8c8c' }}>
                Заказчик: {reportVacancy.admin_manager?.value || reportVacancy.project?.value || '-'}
              </div>
            </div>
            
            <Form form={reportForm} layout="vertical">
              <Form.Item
                name="week_period"
                label="Период (неделя)"
                rules={[{ required: true, message: 'Выберите неделю' }]}
              >
                <Select
                  options={weekOptions}
                  style={{ width: '100%' }}
                  data-testid="report-week-select"
                  showSearch
                  optionFilterProp="label"
                  onChange={handleWeekPeriodChange}
                />
              </Form.Item>
              
              {editingReportId && (
                <div style={{ marginBottom: 12, padding: '6px 10px', background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 4, fontSize: 13, color: '#ad6800' }}>
                  ✏️ Редактирование существующего отчёта за эту неделю
                </div>
              )}
              
              <Space style={{ display: 'flex', flexWrap: 'wrap' }} size={[16, 8]}>
                <Form.Item name="resumes_sent" label="Передано заказчику" style={{ width: 160 }}>
                  <InputNumber min={0} style={{ width: '100%' }} data-testid="report-resumes-sent" />
                </Form.Item>
                <Form.Item name="candidates_agreed" label="Резюме одобрено" style={{ width: 160 }}>
                  <InputNumber min={0} style={{ width: '100%' }} data-testid="report-candidates-agreed" />
                </Form.Item>
              </Space>

              <Space style={{ display: 'flex', flexWrap: 'wrap' }} size={[16, 8]}>
                <Form.Item name="interviews_conducted" label="Собеседования факт (эта неделя)" style={{ width: 200 }}>
                  <InputNumber min={0} style={{ width: '100%' }} data-testid="report-interviews-conducted" />
                </Form.Item>
                <Form.Item name="interviews_planned" label="Собеседования план (след. неделя)" style={{ width: 210 }}>
                  <InputNumber min={0} style={{ width: '100%' }} data-testid="report-interviews-planned" />
                </Form.Item>
              </Space>
              
              {}
              <Form.Item name="offer_made" label="Сделан оффер" style={{ width: 140 }}>
                <InputNumber min={0} style={{ width: '100%' }} data-testid="report-offer-made" />
              </Form.Item>
            </Form>
          </>
        )}
      </Modal>

      {}
      <Drawer
        title={editingVacancy ? 'Редактирование вакансии' : 'Новая вакансия'}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        width={800}
        extra={
          <Space>
            <Button onClick={() => setDrawerVisible(false)}>Отмена</Button>
            <Button type="primary" onClick={handleSave} loading={loading} data-testid="save-vacancy-button">
              Сохранить
            </Button>
          </Space>
        }
      >
        <Form form={form} layout="vertical">
          <div className="form-section">
            <div className="form-section-title">Основная информация</div>
            <Row gutter={16}>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="vacancy_id" label="ID вакансии">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="position_name" label="Вакансия" rules={[{ required: true }]}>
                  <Input data-testid="vacancy-position" />
                </HighlightFormItem>
              </Col>
              <Col span={4}>
                <HighlightFormItem editing={!!editingVacancy} name="quantity" label="Кол-во" initialValue={1}>
                  <InputNumber min={1} style={{ width: '100%' }} />
                </HighlightFormItem>
              </Col>
              {}
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Справочники</div>
            <Row gutter={16}>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="level_id" label="Уровень">
                  <Select options={(dictionaries.specialist_level || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="status_id" label="Статус">
                  <Select options={(dictionaries.vacancy_status || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="it_role_id" label="ИТ Роль">
                  <Select options={(dictionaries.it_role || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="project_id" label="Проект">
                  <Select options={(dictionaries.project || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="source_id" label="Источник">
                  <Select options={(dictionaries.source || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="city_text" label="Город">
                  <Input allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="employment_type_id" label="Вид занятости">
                  <Select options={(dictionaries.employment_type || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="replacement_type_id" label="Новая/Замена">
                  <Select options={(dictionaries.replacement_type || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="internal_transfer_id" label="Внутр. перевод">
                  <Select options={(dictionaries.internal_transfer || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="block_id" label="Блок">
                  <Select options={(dictionaries.block || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="feasibility_id" label="ТЭО">
                  <Select options={(dictionaries.feasibility || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Люди</div>
            <Row gutter={16}>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="admin_manager_id" label="Адм. руководитель">
                  <Select options={(dictionaries.admin_manager || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="team_lead_text" label="Тимлид">
                  <Input allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="recruiter_id" label="Рекрутер">
                  <Select 
                    options={users.map(u => ({ value: u.id, label: u.full_name }))} 
                    allowClear={!isRecruiter}
                    showSearch 
                    optionFilterProp="label"
                    disabled={isRecruiter && !editingVacancy}
                    placeholder={isRecruiter ? user?.full_name : 'Выберите рекрутера'}
                  />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="candidate_name" label="ФИО кандидата">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="candidate_company" label="Компания кандидата">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="ex_employee_name" label="ФИО бывшего сотр.">
                  <Input />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Даты</div>
            <Row gutter={16}>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="open_date" label="Дата открытия">
                  <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="close_date" label="Дата закрытия">
                  <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="status_changed_at" label="Дата изм. статуса">
                  <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                </HighlightFormItem>
              </Col>
              <Col span={6}>
                <HighlightFormItem editing={!!editingVacancy} name="hold_days" label="Дни в холде" initialValue={0}>
                  <InputNumber min={0} style={{ width: '100%' }} data-testid="vacancy-hold-days" />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Дополнительно</div>
            <Row gutter={16}>
              <Col span={8}>
                <HighlightFormItem editing={!!editingVacancy} name="unit_id" label="ID ШЕ">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={16}>
                <HighlightFormItem editing={!!editingVacancy} name="iqhr_link" label="Ссылка IQHR">
                  <Input />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={8}>
                {}
                <HighlightFormItem editing={!!editingVacancy} name="salary_gross" label="Cовокупный доход финального кандидата, gross">
                  <InputNumber min={0} style={{ width: '100%' }} placeholder="руб." />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>
        </Form>
      </Drawer>
    </div>
  );
};

export default DashboardPage;
import { tokenStorage } from '../tokenStorage';
import React, { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import {
  Button, Select, Space, Modal, Form, Input,
  InputNumber, DatePicker, message, Drawer, Divider, Checkbox, Row, Col, Spin, theme
} from 'antd';
import { PlusOutlined, CheckCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import { api } from '../App';
import VacancyTable from './VacancyTable';
import useIsMobile from '../hooks/useIsMobile';

dayjs.extend(isoWeek);

const { RangePicker } = DatePicker;

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';
const API_BASE = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';
const EXPORT_PERIODS = [
  { value: 'all_time', label: 'За всё время' },
  { value: 'current_year', label: 'За текущий год' },
  { value: 'current_month', label: 'За текущий месяц' },
  { value: 'current_week', label: 'За текущую неделю' },
  { value: 'custom', label: 'Произвольный период' },
];

export const OFFER_REJECTION_REASONS = [
  { value: 'Контроффер от текущего работодателя', label: 'Контроффер от текущего работодателя' },
  { value: 'Не устроила заработная плата / условия', label: 'Не устроила заработная плата / условия' },
  { value: 'Не подошел проект / стек технологий', label: 'Не подошел проект / стек технологий' },
  { value: 'Личные / семейные обстоятельства', label: 'Личные / семейные обстоятельства' },
  { value: 'Выбрал другое предложение', label: 'Выбрал другое предложение' },
  { value: 'Не подошел формат работы (удаленка/офис)', label: 'Не подошел формат работы (удаленка/офис)' },
  { value: 'Отказ без объяснения причин', label: 'Отказ без объяснения причин' },
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


/**
 * CreatableDictSelect — Select с возможностью добавить новое значение в словарь.
 * При вводе текста, которого нет в списке, показывает кнопку «Добавить».
 * После создания нового значения через API — добавляет его в локальный список и выбирает.
 *
 * Props:
 *  - options: [{ value: id, label: string }]
 *  - dictType: строка типа словаря (напр. 'feasibility')
 *  - onNewOption: fn(newOption: { value: id, label: string }) — callback после создания
 *  - value, onChange — стандартные props от Form.Item
 *  - ...rest — остальные props передаются в Select
 */
const CreatableDictSelect = ({ options = [], dictType, onNewOption, value, onChange, ...rest }) => {
  const [searchText, setSearchText] = useState('');
  const [adding, setAdding] = useState(false);

  const exactMatch = options.some(
    o => o.label.toLowerCase() === searchText.trim().toLowerCase()
  );
  const showAddBtn = searchText.trim().length > 0 && !exactMatch;

  const handleAdd = async () => {
    if (!searchText.trim()) return;
    setAdding(true);
    try {
      const res = await api.post('/dictionaries/add-value', {
        type: dictType,
        value: searchText.trim(),
      });
      const newOpt = { value: res.data.id, label: res.data.value };
      if (onNewOption) onNewOption(newOpt);
      onChange?.(res.data.id);
      setSearchText('');
      message.success(`Значение «${res.data.value}» добавлено в справочник`);
    } catch (e) {
      message.error('Не удалось добавить значение: ' + (e.response?.data?.detail || e.message));
    } finally {
      setAdding(false);
    }
  };

  const dropdownRender = (menu) => (
    <>
      {menu}
      {showAddBtn && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            padding: '4px 8px',
            borderTop: '1px solid #f0f0f0',
            gap: 8,
          }}
        >
          {adding ? (
            <Spin size="small" />
          ) : (
            <Button
              type="link"
              size="small"
              icon={<PlusOutlined />}
              onMouseDown={(e) => e.preventDefault()}
              onClick={handleAdd}
              style={{ padding: 0 }}
            >
              Добавить «{searchText.trim()}»
            </Button>
          )}
        </div>
      )}
    </>
  );

  return (
    <Select
      {...rest}
      popupMatchSelectWidth={false}
      value={value}
      onChange={(val) => {
        onChange?.(val);
        setSearchText('');
      }}
      showSearch
      allowClear
      onSearch={setSearchText}
      filterOption={(input, option) =>
        (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
      }
      options={options}
      dropdownRender={dropdownRender}
    />
  );
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
            className={`${props.className || ''} ${isEmpty ? 'highlight-empty-field' : ''}`}
          >
            {props.children}
          </Form.Item>
        );
      }}
    </Form.Item>
  );
};

const DashboardPage = () => {
  const { token } = theme.useToken();
  const isMobile = useIsMobile();
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

  const [reportModalVisible, setReportModalVisible] = useState(false);
  const [reportVacancy, setReportVacancy] = useState(null);
  const [reportLoading, setReportLoading] = useState(false);
  const [weekOptions] = useState(generateWeekOptions());
  const [isReportWeekEditable, setIsReportWeekEditable] = useState(true);

  const [editingReportId, setEditingReportId] = useState(null);

  const [user, setUser] = useState(() => tokenStorage.getUser() || {});
  const isRecruiter = user?.role === 'recruiter';

  const checkWeekEditable = useCallback((weekPeriod) => {
    if (!isRecruiter || !weekPeriod) return true;
    const currentWeek = dayjs().isoWeek();
    const currentYear = dayjs().year();
    const [year, week] = weekPeriod.split('-').map(Number);
    const selectedStart = dayjs().year(year).isoWeek(week).startOf('isoWeek');
    const currentStart = dayjs().year(currentYear).isoWeek(currentWeek).startOf('isoWeek');
    const diffDays = currentStart.diff(selectedStart, 'day');
    return diffDays <= 7;
  }, [isRecruiter]);

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
        'block', 'admin_manager', 'internal_transfer', 'offer_rejection_reason'
      ];
      const responses = await Promise.all(
        types.map(t => api.get(`/dictionaries/by-type/${t}`).catch(() => ({ data: [] })))
      );
      const results = {};
      types.forEach((type, idx) => {
        results[type] = responses[idx]?.data || [];
      });
      setDictionaries(results);
    } catch (error) {
      console.error('Failed to load dictionaries:', error);
    }
  };

  const loadUsers = async () => {
    try {
      const response = await api.get('/users?limit=1000');
      setUsers(response.data.items || []);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const rejectionReasonOptions = useMemo(() => {
    const fromDict = (dictionaries.offer_rejection_reason || []).map((d) => ({
      value: d.value,
      label: d.value,
    }));
    if (fromDict.length > 0) return fromDict;
    return OFFER_REJECTION_REASONS;
  }, [dictionaries.offer_rejection_reason]);

  const handleCreate = () => {
    setEditingVacancy(null);
    form.resetFields();
    if (isRecruiter && user?.id) {
      form.setFieldsValue({ recruiter_id: user.id });
    }
    setDrawerVisible(true);
  };

  const handleStatusChange = (val) => {
    form.setFieldsValue({
      status_id: val,
    });
  };

  const handleEdit = (record) => {
    setEditingVacancy(record);

    let rejectionReasons = [];
    if (record.offer_rejection_reason) {
      if (Array.isArray(record.offer_rejection_reason)) {
        rejectionReasons = record.offer_rejection_reason;
      } else {
        rejectionReasons = String(record.offer_rejection_reason)
          .split(',')
          .map(s => s.trim())
          .filter(Boolean);
      }
    }

    form.setFieldsValue({
      ...record,
      open_date: record.open_date ? dayjs(record.open_date) : null,
      close_date: record.close_date ? dayjs(record.close_date) : null,

      resume_at_customer: record.resume_at_customer || 0,
      resume_approved:    record.resume_approved    || 0,
      interviews_fact:    record.interviews_fact    || 0,
      interviews_plan:    record.interviews_plan    || 0,
      offer_made:         record.offer_made         || 0,
      offer_accepted:     record.offer_accepted     || record.offer_accepted_cnt || 0,
      offer_rejection_reason: rejectionReasons,
      comment:            record.comment || '',
      feasibility_id:     record.feasibility_id || record.feasibility?.id || (
        (dictionaries.feasibility || []).find(d => 
          record.feasibility_text && d.value?.trim().toLowerCase() === record.feasibility_text.trim().toLowerCase()
        )?.id
      ) || null,
    });
    setDrawerVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);
      const payload = {
        ...values,
        open_date: values.open_date ? values.open_date.format('YYYY-MM-DD') : null,
        close_date: values.close_date ? values.close_date.format('YYYY-MM-DD') : null,
      };
      delete payload.vacancy_id;

      if (Array.isArray(payload.offer_rejection_reason)) {
        payload.offer_rejection_reason = payload.offer_rejection_reason.length > 0
          ? payload.offer_rejection_reason.join(', ')
          : null;
      }

      if (isRecruiter) {
        if (editingVacancy) {
          delete payload.recruiter_id;
        } else {
          payload.recruiter_id = user?.id;
        }
      }
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
      let detail = error.response?.data?.detail;
      if (Array.isArray(detail)) {
        detail = detail.map(d => d.msg || JSON.stringify(d)).join(', ');
      } else if (typeof detail === 'object' && detail !== null) {
        detail = JSON.stringify(detail);
      }
      message.error(detail || error.message || 'Ошибка сохранения');
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

  const handleReportClick = async (vacancy) => {
    setReportVacancy(vacancy);
    setEditingReportId(null);
    const currentWeek = dayjs().isoWeek();
    const currentYear = dayjs().year();
    const weekPeriod = `${currentYear}-${currentWeek}`;
    setIsReportWeekEditable(checkWeekEditable(weekPeriod));

    reportForm.resetFields();
    reportForm.setFieldsValue({
      week_period: weekPeriod,
      resumes_sent: 0,
      candidates_agreed: 0,
      interviews_planned: 0,
      interviews_conducted: 0,
      offer_made: 0,
      offer_accepted: 0,
      offer_rejection_reason: null,
    });
    setReportModalVisible(true);

    const parseRejectionReasons = (val) => {
      if (!val) return [];
      if (Array.isArray(val)) return val;
      return String(val).split(',').map(s => s.trim()).filter(Boolean);
    };

    try {
      const res = await api.get(`/reports/vacancy/${vacancy.id}`);
      const reports = res.data.items || [];
      const existing = reports.find(r => r.week_number === currentWeek && r.year === currentYear && (!isRecruiter || !r.user_id || r.user_id === user?.id));
      if (existing) {
        setEditingReportId(existing.id);
        reportForm.setFieldsValue({
          resumes_sent: existing.resumes_sent || 0,
          candidates_agreed: existing.candidates_agreed || 0,
          interviews_planned: existing.interviews_planned || 0,
          interviews_conducted: existing.interviews_conducted || 0,
          offer_made: existing.offer_made || 0,
          offer_accepted: existing.offer_accepted || 0,
          offer_rejection_reason: parseRejectionReasons(existing.offer_rejection_reason),
        });
      }
    } catch {

    }
  };

  const handleWeekPeriodChange = async (value) => {
    if (!reportVacancy || !value) return;
    setIsReportWeekEditable(checkWeekEditable(value));
    const parseRejectionReasons = (val) => {
      if (!val) return [];
      if (Array.isArray(val)) return val;
      return String(val).split(',').map(s => s.trim()).filter(Boolean);
    };
    try {
      const [year, week] = value.split('-').map(Number);
      const res = await api.get(`/reports/vacancy/${reportVacancy.id}`);
      const reports = res.data.items || [];
      const existing = reports.find(r => r.week_number === week && r.year === year && (!isRecruiter || !r.user_id || r.user_id === user?.id));
      if (existing) {
        setEditingReportId(existing.id);
        reportForm.setFieldsValue({
          resumes_sent: existing.resumes_sent || 0,
          candidates_agreed: existing.candidates_agreed || 0,
          interviews_planned: existing.interviews_planned || 0,
          interviews_conducted: existing.interviews_conducted || 0,
          offer_made: existing.offer_made || 0,
          offer_accepted: existing.offer_accepted || 0,
          offer_rejection_reason: parseRejectionReasons(existing.offer_rejection_reason),
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
          offer_accepted: 0,
          offer_rejection_reason: [],
        });
      }
    } catch {

    }
  };

  const handleReportSave = async () => {
    try {
      if (!isReportWeekEditable) {
        message.warning('Рекрутер может редактировать отчеты только за текущую и предыдущую неделю');
        return;
      }
      const values = await reportForm.validateFields();
      setReportLoading(true);
      
      const [year, week] = values.week_period.split('-').map(Number);
      
      const formatRejectionReasons = (val) => {
        if (Array.isArray(val)) {
          return val.length > 0 ? val.join(', ') : null;
        }
        return val || null;
      };

      const payload = {
        resumes_sent: values.resumes_sent || 0,
        candidates_agreed: values.candidates_agreed || 0,
        interviews_planned: values.interviews_planned || 0,
        interviews_conducted: values.interviews_conducted || 0,
        offer_made: values.offer_made || 0,
        offer_accepted: values.offer_accepted || 0,
        offer_rejection_reason: formatRejectionReasons(values.offer_rejection_reason),
      };

      if (editingReportId) {

        await api.patch(`/reports/${editingReportId}`, payload);
        message.success('Отчёт обновлён.');
      } else {

        await api.post('/reports', {
          vacancy_id: reportVacancy.id,
          week_number: week,
          year: year,
          user_id: user?.id,
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
        onTableStateChange={handleTableStateChange}
        onResetRequest={handleResetRequest}
        onTourComplete={handleVacanciesTourComplete}
      />

      {}
      <Modal
        title={editingReportId ? 'Редактировать отчёт' : 'Добавить отчёт'}
        open={reportModalVisible}
        onCancel={() => { setReportModalVisible(false); setEditingReportId(null); }}
        onOk={handleReportSave}
        okText="Сохранить"
        cancelText="Отмена"
        confirmLoading={reportLoading}
        okButtonProps={{ disabled: !isReportWeekEditable }}
        width={isMobile ? '95vw' : 520}
        data-testid="report-modal"
      >
        {reportVacancy && (
          <>
            <div style={{ marginBottom: 16, padding: 12, background: token.colorFillAlter, borderRadius: 4 }}>
              <div style={{ fontWeight: 500, marginBottom: 4 }}>{reportVacancy.position_name}</div>
              <div style={{ fontSize: 12, color: token.colorTextSecondary }}>
                Адм. руководитель: {reportVacancy.admin_manager?.value || '-'}
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

              {!isReportWeekEditable && (
                <div style={{ marginBottom: 12, padding: '6px 10px', background: token.colorErrorBg, border: `1px solid ${token.colorErrorBorder}`, borderRadius: 4, fontSize: 13, color: token.colorErrorText }}>
                  🔒 В роли Рекрутера отчёты старше предыдущей недели доступны только для просмотра.
                </div>
              )}
              
              {editingReportId && isReportWeekEditable && (
                <div style={{ marginBottom: 12, padding: '6px 10px', background: token.colorWarningBg, border: `1px solid ${token.colorWarningBorder}`, borderRadius: 4, fontSize: 13, color: token.colorWarning }}>
                  ✏️ Редактирование существующего отчёта за эту неделю
                </div>
              )}
              
              <Space style={{ display: 'flex', flexWrap: 'wrap' }} size={[16, 8]}>
                <Form.Item name="resumes_sent" label="Передано заказчику" style={{ width: 160 }}>
                  <InputNumber min={0} disabled={!isReportWeekEditable} style={{ width: '100%' }} data-testid="report-resumes-sent" />
                </Form.Item>
                <Form.Item name="candidates_agreed" label="Резюме одобрено" style={{ width: 160 }}>
                  <InputNumber min={0} disabled={!isReportWeekEditable} style={{ width: '100%' }} data-testid="report-candidates-agreed" />
                </Form.Item>
              </Space>

              <Space style={{ display: 'flex', flexWrap: 'wrap' }} size={[16, 8]}>
                <Form.Item name="interviews_conducted" label="Собеседования факт (эта неделя)" style={{ width: 220 }}>
                  <InputNumber min={0} disabled={!isReportWeekEditable} style={{ width: '100%' }} data-testid="report-interviews-conducted" />
                </Form.Item>
                <Form.Item name="interviews_planned" label="Собеседования план (след. неделя)" style={{ width: 220 }}>
                  <InputNumber min={0} disabled={!isReportWeekEditable} style={{ width: '100%' }} data-testid="report-interviews-planned" />
                </Form.Item>
              </Space>
              
              <Space style={{ display: 'flex', flexWrap: 'wrap' }} size={[16, 8]}>
                <Form.Item name="offer_made" label="Оффер сделан" style={{ width: 160 }}>
                  <InputNumber min={0} disabled={!isReportWeekEditable} style={{ width: '100%' }} data-testid="report-offer-made" />
                </Form.Item>
                <Form.Item name="offer_accepted" label="Оффер принят" style={{ width: 160 }}>
                  <InputNumber min={0} disabled={!isReportWeekEditable} style={{ width: '100%' }} data-testid="report-offer-accepted" />
                </Form.Item>
              </Space>

              <Form.Item name="offer_rejection_reason" label="Причина отказа от Оффера">
                <Select
                  mode="multiple"
                  disabled={!isReportWeekEditable}
                  allowClear
                  showSearch
                  placeholder="Выберите причину(ы) отказа от оффера"
                  options={rejectionReasonOptions}
                  filterOption={(input, option) =>
                    (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                  }
                />
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
        width={isMobile ? '100%' : 980}
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
              <Col span={isMobile ? 24 : 6}>
              <HighlightFormItem editing={!!editingVacancy} name="vacancy_id" label="ID вакансии">
                  <Input disabled placeholder={editingVacancy ? undefined : 'Автоматически'} />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 8}>
                <HighlightFormItem editing={!!editingVacancy} name="position_name" label="Вакансия" rules={[{ required: true }]}>
                  <Input data-testid="vacancy-position" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 4}>
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
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="level_id" label="Уровень">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.specialist_level || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="status_id" label="Статус">
                  <Select popupMatchSelectWidth={false} onChange={handleStatusChange} options={(dictionaries.vacancy_status || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="it_role_id" label="ИТ Роль">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.it_role || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="project_id" label="Проект">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.project || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="source_id" label="Источник">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.source || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="city_text" label="Город">
                  <Input allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="employment_type_id" label="Вид занятости">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.employment_type || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="replacement_type_id" label="Новая/Замена">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.replacement_type || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="internal_transfer_id" label="Внутр. перевод">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.internal_transfer || []).map(d => ({ value: d.id, label: d.value }))} allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="block_id" label="Блок">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.block || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 12 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="feasibility_id" label="ТЭО проекта">
                  <CreatableDictSelect
                    options={(dictionaries.feasibility || []).map(d => ({ value: d.id, label: d.value }))}
                    dictType="feasibility"
                    onNewOption={(newOpt) => {
                      setDictionaries(prev => ({
                        ...prev,
                        feasibility: [...(prev.feasibility || []), { id: newOpt.value, value: newOpt.label }],
                      }));
                    }}
                  />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Люди</div>
            <Row gutter={16}>
              <Col span={isMobile ? 24 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="admin_manager_id" label="Адм. руководитель">
                  <Select popupMatchSelectWidth={false} options={(dictionaries.admin_manager || []).map(d => ({ value: d.id, label: d.value }))} allowClear showSearch optionFilterProp="label" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="team_lead_text" label="Тимлид">
                  <Input allowClear />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="recruiter_id" label="Рекрутер">
                  <Select 
                    popupMatchSelectWidth={false}
                    options={users.map(u => ({ value: u.id, label: u.full_name }))} 
                    allowClear={!isRecruiter}
                    showSearch 
                    optionFilterProp="label"
                    disabled={isRecruiter}
                    placeholder={isRecruiter ? (user?.full_name || 'Рекрутер') : 'Выберите рекрутера'}
                  />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 6}>
                <HighlightFormItem editing={!!editingVacancy} name="co_recruiter_id" label={<span style={{ whiteSpace: 'nowrap' }} title="Дополнительный рекрутер">Дополнительный рекрутер</span>}>
                  <Select 
                    popupMatchSelectWidth={false}
                    options={users.map(u => ({ value: u.id, label: u.full_name }))} 
                    allowClear
                    showSearch 
                    optionFilterProp="label"
                    placeholder="Выберите доп. рекрутера"
                  />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={isMobile ? 24 : 8}>
                <HighlightFormItem editing={!!editingVacancy} name="candidate_name" label="ФИО кандидата">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 8}>
                <HighlightFormItem editing={!!editingVacancy} name="candidate_company" label="Компания кандидата">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 8}>
                <HighlightFormItem editing={!!editingVacancy} name="ex_employee_name" label="ФИО бывшего сотр.">
                  <Input />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={24}>
                <HighlightFormItem editing={!!editingVacancy} name="offer_rejection_reason" label="Причина отказа от Оффера">
                  <Select
                    mode="multiple"
                    allowClear
                    showSearch
                    placeholder="Выберите причину(ы) отказа от оффера"
                    options={rejectionReasonOptions}
                    filterOption={(input, option) =>
                      (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
                    }
                  />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={24}>
                <HighlightFormItem editing={!!editingVacancy} name="comment" label="Комментарий">
                  <Input.TextArea autoSize={{ minRows: 2, maxRows: 4 }} placeholder="Комментарий по кандидату / вакансии" />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Даты</div>
            <Row gutter={16}>
              <Col span={isMobile ? 24 : 12}>
                <HighlightFormItem editing={!!editingVacancy} name="open_date" label="Дата открытия">
                  <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 12}>
                <HighlightFormItem editing={!!editingVacancy} name="close_date" label="Дата закрытия">
                  <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                </HighlightFormItem>
              </Col>
            </Row>
          </div>

          <Divider />

          <div className="form-section">
            <div className="form-section-title">Дополнительно</div>
            <Row gutter={16}>
              <Col span={isMobile ? 24 : 8}>
                <HighlightFormItem editing={!!editingVacancy} name="unit_id" label="ID ШЕ">
                  <Input />
                </HighlightFormItem>
              </Col>
              <Col span={isMobile ? 24 : 16}>
                <HighlightFormItem editing={!!editingVacancy} name="iqhr_link" label="Ссылка IQHR">
                  <Input />
                </HighlightFormItem>
              </Col>
            </Row>
            <Row gutter={16}>
              <Col span={isMobile ? 24 : 8}>
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
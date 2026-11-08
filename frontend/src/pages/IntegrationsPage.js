import React, { useState, useEffect, useContext, useCallback } from 'react';
import {
  Table,
  Button,
  Tag,
  Switch,
  Modal,
  Form,
  Input,
  Space,
  Typography,
  message,
  Popconfirm,
  Tooltip,
  Tabs,
  Alert,
} from 'antd';
import {
  PlusOutlined,
  CopyOutlined,
  DeleteOutlined,
  ReloadOutlined,
  BookOutlined,
} from '@ant-design/icons';
import { api, ThemeContext } from '../App';

const { Text } = Typography;

export default function IntegrationsPage() {
  const { isDarkMode } = useContext(ThemeContext);

  const [tokens, setTokens] = useState([]);
  const [loading, setLoading] = useState(false);
  const [createModalVisible, setCreateModalVisible] = useState(false);
  const [createdTokenData, setCreatedTokenData] = useState(null);
  const [fieldsSpec, setFieldsSpec] = useState([]);
  const [specLoading, setSpecLoading] = useState(false);
  const [fieldsFilter, setFieldsFilter] = useState('');

  const [form] = Form.useForm();

  const originUrl = window.location.origin;
  const originHost = window.location.hostname;
  const isHttps = window.location.protocol === 'https:';
  const defaultPort = isHttps ? 443 : (window.location.port || 80);
  const sslParam = isHttps ? ', Новый ЗащищенноеСоединениеOpenSSL()' : '';

  // Load tokens list
  const loadTokens = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/integration/tokens');
      setTokens(res.data.items || []);
    } catch (err) {
      console.error('Failed to load integration tokens', err);
      message.error('Ошибка загрузки списка токенов');
    } finally {
      setLoading(false);
    }
  }, []);

  // Load fields specification
  const loadFieldsSpec = useCallback(async () => {
    setSpecLoading(true);
    try {
      const res = await api.get('/integration/fields');
      setFieldsSpec(res.data.fields || []);
    } catch (err) {
      console.error('Failed to load fields spec', err);
    } finally {
      setSpecLoading(false);
    }
  }, []);

  useEffect(() => {
    loadTokens();
    loadFieldsSpec();
  }, [loadTokens, loadFieldsSpec]);

  // Copy token to clipboard
  const handleCopy = (text, label = 'Токен') => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      message.success(`${label} скопирован в буфер обмена`);
    } else {
      const el = document.createElement('textarea');
      el.value = text;
      document.body.appendChild(el);
      el.select();
      document.execCommand('copy');
      document.body.removeChild(el);
      message.success(`${label} скопирован в буфер обмена`);
    }
  };

  // Toggle token active/inactive
  const handleToggle = async (id) => {
    try {
      const res = await api.patch(`/integration/tokens/${id}/toggle`);
      message.success(res.data.message || 'Статус токена обновлен');
      loadTokens();
    } catch (err) {
      console.error('Failed to toggle token', err);
      message.error('Ошибка изменения статуса токена');
    }
  };

  // Delete token
  const handleDelete = async (id) => {
    try {
      await api.delete(`/integration/tokens/${id}`);
      message.success('Токен успешно удален');
      loadTokens();
    } catch (err) {
      console.error('Failed to delete token', err);
      message.error('Ошибка удаления токена');
    }
  };

  // Create token
  const handleCreateSubmit = async (values) => {
    try {
      const res = await api.post('/integration/tokens', values);
      setCreatedTokenData(res.data.item);
      form.resetFields();
      loadTokens();
    } catch (err) {
      console.error('Failed to create token', err);
      message.error(err.response?.data?.detail || 'Ошибка создания токена');
    }
  };

  const sampleToken = tokens[0]?.token || 'rms_live_sample_token_abcdef123456';

  const tokenColumns = [
    {
      title: 'Система',
      dataIndex: 'name',
      key: 'name',
      render: (text, record) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          {record.description && (
            <div style={{ fontSize: 13, color: '#8c8c8c', marginTop: 2 }}>
              {record.description}
            </div>
          )}
        </div>
      ),
    },
    {
      title: 'API Токен',
      dataIndex: 'token',
      key: 'token',
      width: 270,
      render: (tok) => (
        <Space size={6}>
          <code style={{
            fontSize: 13,
            background: isDarkMode ? '#1e242c' : '#f1f5f9',
            padding: '3px 7px',
            borderRadius: 4,
            border: `1px solid ${isDarkMode ? '#30363d' : '#e2e8f0'}`,
          }}>
            {tok.substring(0, 12)}...{tok.substring(tok.length - 6)}
          </code>
          <Tooltip title="Скопировать">
            <Button
              type="text"
              size="small"
              icon={<CopyOutlined />}
              onClick={() => handleCopy(tok, 'API токен')}
            />
          </Tooltip>
        </Space>
      ),
    },
    {
      title: 'Статус',
      dataIndex: 'is_active',
      key: 'is_active',
      width: 80,
      align: 'center',
      render: (isActive, record) => (
        <Switch
          checked={isActive}
          onChange={() => handleToggle(record.id)}
          size="small"
        />
      ),
    },
    {
      title: 'Создал',
      dataIndex: 'created_by',
      key: 'created_by',
      width: 160,
      render: (text) => <span style={{ color: '#8c8c8c' }}>{text || '—'}</span>,
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      key: 'created_at',
      width: 120,
      render: (dt) => (
        <span style={{ color: '#8c8c8c' }}>
          {dt ? new Date(dt).toLocaleDateString('ru-RU') : '—'}
        </span>
      ),
    },
    {
      title: 'Посл. запрос',
      dataIndex: 'last_used_at',
      key: 'last_used_at',
      width: 170,
      render: (dt) => {
        if (!dt) return <span style={{ color: '#8c8c8c' }}>—</span>;
        return (
          <span style={{ color: '#8c8c8c' }}>
            {new Date(dt).toLocaleString('ru-RU', {
              day: '2-digit',
              month: '2-digit',
              year: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        );
      },
    },
    {
      title: '',
      key: 'actions',
      width: 60,
      align: 'center',
      render: (_, record) => (
        <Popconfirm
          title={`Удалить токен «${record.name}»?`}
          onConfirm={() => handleDelete(record.id)}
          okText="Удалить"
          okType="danger"
          cancelText="Отмена"
        >
          <Button type="text" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const filteredFields = fieldsSpec.filter((f) => {
    if (!fieldsFilter.trim()) return true;
    const q = fieldsFilter.toLowerCase();
    return (
      f.field.toLowerCase().includes(q) ||
      f.type.toLowerCase().includes(q) ||
      f.description.toLowerCase().includes(q)
    );
  });

  const fieldsColumns = [
    {
      title: '№',
      key: 'index',
      width: 60,
      align: 'center',
      render: (_, __, idx) => <span style={{ color: '#8c8c8c' }}>{idx + 1}</span>,
    },
    {
      title: 'Поле в API',
      dataIndex: 'field',
      key: 'field',
      width: 260,
      render: (text) => <span style={{ fontWeight: 500 }}>{text}</span>,
    },
    {
      title: 'Тип',
      dataIndex: 'type',
      key: 'type',
      width: 140,
      render: (t) => {
        let color = 'blue';
        if (t.includes('целое')) color = 'purple';
        if (t.includes('дата')) color = 'green';
        return <Tag color={color}>{t}</Tag>;
      },
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      key: 'description',
    },
  ];

  return (
    <div data-testid="integrations-page" style={{ padding: 24 }}>
      {/* Page Header */}
      <div className="page-header">
        <h1>Интеграции API</h1>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={loadTokens}
            loading={loading}
          >
            Обновить
          </Button>
          <Button
            icon={<BookOutlined />}
            onClick={() => window.open(`${originUrl}/api/docs`, '_blank')}
          >
            Swagger
          </Button>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setCreatedTokenData(null);
              setCreateModalVisible(true);
            }}
          >
            Создать токен
          </Button>
        </Space>
      </div>

      {/* Tabs */}
      <Tabs
        defaultActiveKey="tokens"
        items={[
          {
            key: 'tokens',
            label: `Токены (${tokens.length})`,
            children: (
              <Table
                columns={tokenColumns}
                dataSource={tokens}
                rowKey="id"
                loading={loading}
                pagination={false}
                bordered
                size="middle"
                locale={{ emptyText: 'Токены не созданы' }}
              />
            ),
          },
          {
            key: 'code_examples',
            label: 'Примеры запросов',
            children: (
              <div style={{ maxWidth: 1050 }}>
                {/* Endpoints table */}
                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>Эндпоинты</div>
                  <div style={{
                    background: isDarkMode ? '#161b22' : '#f8fafc',
                    padding: '14px 18px',
                    borderRadius: 6,
                    border: `1px solid ${isDarkMode ? '#30363d' : '#e2e8f0'}`,
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
                      <span style={{ fontSize: 14 }}>
                        <Tag color="green" style={{ fontSize: 13, padding: '2px 8px' }}>GET</Tag>
                        <code style={{ fontSize: 14 }}>{originUrl}/api/integration/vacancies</code>
                        <span style={{ marginLeft: 10, color: '#8c8c8c' }}>— выгрузка вакансий</span>
                      </span>
                      <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(`${originUrl}/api/integration/vacancies`, 'URL')}>
                        Копировать
                      </Button>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: 14 }}>
                        <Tag color="green" style={{ fontSize: 13, padding: '2px 8px' }}>GET</Tag>
                        <code style={{ fontSize: 14 }}>{originUrl}/api/integration/vacancies/{'{id}'}</code>
                        <span style={{ marginLeft: 10, color: '#8c8c8c' }}>— вакансия по ID</span>
                      </span>
                    </div>
                  </div>
                </div>

                {/* Parameters */}
                <div style={{ marginBottom: 24 }}>
                  <div style={{ fontWeight: 600, fontSize: 15, marginBottom: 10 }}>Параметры</div>
                  <div style={{ fontSize: 14, lineHeight: '2.1', color: isDarkMode ? '#c9d1d9' : '#334155' }}>
                    <div><code style={{ fontSize: 14 }}>limit</code> — количество записей (по умолчанию 1000, максимум 5000)</div>
                    <div><code style={{ fontSize: 14 }}>offset</code> — смещение для пагинации</div>
                    <div><code style={{ fontSize: 14 }}>status</code> — фильтрация по статусу вакансии</div>
                    <div><code style={{ fontSize: 14 }}>updated_after</code> — инкрементальная выгрузка (измененные после даты в ISO формате)</div>
                    <div><code style={{ fontSize: 14 }}>format</code> — формат выгрузки: <code>json</code>, <code>excel</code>, <code>csv</code></div>
                  </div>
                </div>

                {/* cURL */}
                <div style={{ marginBottom: 24 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 15 }}>cURL</Text>
                    <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(`curl -X GET "${originUrl}/api/integration/vacancies?limit=500" \\\n  -H "X-API-Key: ${sampleToken}"`, 'cURL')}>
                      Копировать
                    </Button>
                  </div>
                  <pre style={{
                    background: isDarkMode ? '#161b22' : '#f8fafc',
                    padding: 16,
                    borderRadius: 6,
                    border: `1px solid ${isDarkMode ? '#30363d' : '#e2e8f0'}`,
                    fontSize: 14,
                    lineHeight: 1.6,
                    margin: 0,
                    overflowX: 'auto',
                  }}>
{`curl -X GET "${originUrl}/api/integration/vacancies?limit=500" \\
  -H "X-API-Key: ${sampleToken}"`}
                  </pre>
                </div>

                {/* Python */}
                <div style={{ marginBottom: 24 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 15 }}>Python</Text>
                    <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(`import requests\n\nheaders = {"X-API-Key": "${sampleToken}"}\nresponse = requests.get("${originUrl}/api/integration/vacancies", headers=headers)\ndata = response.json()\n\nprint(f"Всего вакансий: {data['total']}")\nfor item in data['items']:\n    print(item['ID вакансии'], item['Вакансия'], item['Статус вакансии'])`, 'Python')}>
                      Копировать
                    </Button>
                  </div>
                  <pre style={{
                    background: isDarkMode ? '#161b22' : '#f8fafc',
                    padding: 16,
                    borderRadius: 6,
                    border: `1px solid ${isDarkMode ? '#30363d' : '#e2e8f0'}`,
                    fontSize: 14,
                    lineHeight: 1.6,
                    margin: 0,
                    overflowX: 'auto',
                  }}>
{`import requests

headers = {"X-API-Key": "${sampleToken}"}
response = requests.get("${originUrl}/api/integration/vacancies", headers=headers)
data = response.json()

print(f"Всего вакансий: {data['total']}")
for item in data['items']:
    print(item['ID вакансии'], item['Вакансия'], item['Статус вакансии'])`}
                  </pre>
                </div>

                {/* 1С */}
                <div style={{ marginBottom: 24 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
                    <Text strong style={{ fontSize: 15 }}>1С:Предприятие</Text>
                    <Button size="small" icon={<CopyOutlined />} onClick={() => handleCopy(`Сервер = "${originHost}";\nHTTPСоединение = Новый HTTPСоединение(Сервер, ${defaultPort},,,,,${sslParam});\nHTTPЗапрос = Новый HTTPЗапрос("/api/integration/vacancies");\nHTTPЗапрос.Заголовки.Вставить("X-API-Key", "${sampleToken}");\nОтвет = HTTPСоединение.Получить(HTTPЗапрос);\nЕсли Ответ.КодСостояния = 200 Тогда\n    ЧтениеJSON = Новый ЧтениеJSON;\n    ЧтениеJSON.УстановитьСтроку(Ответ.ПолучитьТелоКакСтроку());\n    Данные = ПрочитатьJSON(ЧтениеJSON);\nКонецЕсли;`, '1С')}>
                      Копировать
                    </Button>
                  </div>
                  <pre style={{
                    background: isDarkMode ? '#161b22' : '#f8fafc',
                    padding: 16,
                    borderRadius: 6,
                    border: `1px solid ${isDarkMode ? '#30363d' : '#e2e8f0'}`,
                    fontSize: 14,
                    lineHeight: 1.6,
                    margin: 0,
                    overflowX: 'auto',
                  }}>
{`Сервер = "${originHost}";
HTTPСоединение = Новый HTTPСоединение(Сервер, ${defaultPort},,,,,${sslParam});
HTTPЗапрос = Новый HTTPЗапрос("/api/integration/vacancies");
HTTPЗапрос.Заголовки.Вставить("X-API-Key", "${sampleToken}");
Ответ = HTTPСоединение.Получить(HTTPЗапрос);
Если Ответ.КодСостояния = 200 Тогда
    ЧтениеJSON = Новый ЧтениеJSON;
    ЧтениеJSON.УстановитьСтроку(Ответ.ПолучитьТелоКакСтроку());
    Данные = ПрочитатьJSON(ЧтениеJSON);
КонецЕсли;`}
                  </pre>
                </div>
              </div>
            ),
          },
          {
            key: 'fields',
            label: 'Спецификация полей (38)',
            children: (
              <div>
                <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
                  <Input.Search
                    placeholder="Поиск по полям..."
                    value={fieldsFilter}
                    onChange={(e) => setFieldsFilter(e.target.value)}
                    style={{ width: 280 }}
                    allowClear
                  />
                </div>

                <Table
                  columns={fieldsColumns}
                  dataSource={filteredFields}
                  rowKey="field"
                  loading={specLoading}
                  pagination={false}
                  bordered
                  size="middle"
                />
              </div>
            ),
          },
        ]}
      />

      {/* Modal: Create Token */}
      <Modal
        title="Создать токен"
        open={createModalVisible}
        onCancel={() => {
          setCreateModalVisible(false);
          setCreatedTokenData(null);
          form.resetFields();
        }}
        footer={null}
        destroyOnClose
      >
        {!createdTokenData ? (
          <Form
            form={form}
            layout="vertical"
            onFinish={handleCreateSubmit}
            style={{ marginTop: 16 }}
          >
            <Form.Item
              name="name"
              label="Название системы"
              rules={[{ required: true, message: 'Укажите название' }]}
            >
              <Input placeholder="Например, 1С:ЗУП" autoFocus />
            </Form.Item>

            <Form.Item
              name="description"
              label="Описание"
            >
              <Input.TextArea
                rows={2}
                placeholder="Необязательно"
              />
            </Form.Item>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 24 }}>
              <Button onClick={() => setCreateModalVisible(false)}>
                Отмена
              </Button>
              <Button type="primary" htmlType="submit">
                Создать
              </Button>
            </div>
          </Form>
        ) : (
          <div style={{ marginTop: 16 }}>
            <Alert
              type="info"
              showIcon
              message="Токен создан. Вы можете скопировать его сейчас или позже из таблицы."
              style={{ marginBottom: 16 }}
            />

            <div style={{
              display: 'flex',
              gap: 8,
              alignItems: 'center',
              background: isDarkMode ? '#161b22' : '#f8fafc',
              padding: '8px 12px',
              borderRadius: 6,
              border: `1px solid ${isDarkMode ? '#30363d' : '#e2e8f0'}`,
              marginBottom: 20,
            }}>
              <code style={{ fontSize: 13, wordBreak: 'break-all', flex: 1, fontWeight: 600 }}>
                {createdTokenData.token}
              </code>
              <Button
                type="primary"
                icon={<CopyOutlined />}
                onClick={() => handleCopy(createdTokenData.token, 'Токен')}
              >
                Скопировать
              </Button>
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
              <Button
                type="primary"
                onClick={() => {
                  setCreateModalVisible(false);
                  setCreatedTokenData(null);
                }}
              >
                Готово
              </Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}

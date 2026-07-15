import { tokenStorage } from '../tokenStorage';
import React, { useState, useRef } from 'react';
import { Table, Button, Select, Space, Tag, Modal, Form, Input, InputNumber, message, Popconfirm, Alert } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, LockOutlined } from '@ant-design/icons';
import { api } from '../App';

const DICTIONARY_TYPES = [
  { value: 'specialist_level', label: 'Уровень специалиста' },
  { value: 'vacancy_status', label: 'Статус вакансии' },
  { value: 'it_role', label: 'IT роль' },
  { value: 'project', label: 'Проект' },
  { value: 'source', label: 'Источник' },
  { value: 'employment_type', label: 'Вид занятости' },
  { value: 'replacement_type', label: 'Тип замены' },
  { value: 'feasibility', label: 'ТЭО проекта' },
  { value: 'block', label: 'Блок' },
  { value: 'admin_manager', label: 'Административный руководитель' },
  { value: 'internal_transfer', label: 'Внутренний перевод' },
];

const DictionaryPage = () => {
  const [form] = Form.useForm();
  
  const [selectedType, setSelectedType] = useState('specialist_level');
  const [modalVisible, setModalVisible] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);
  const [tableLoading, setTableLoading] = useState(false);

  const user = tokenStorage.getUser() || {};
  const isAdmin = user.role === 'admin' || user.role === 'superadmin';

  React.useEffect(() => {
    loadData();
  }, [selectedType]);

  const loadData = async () => {
    setTableLoading(true);
    try {
      const response = await api.get('/dictionaries', {
        params: {
          type: selectedType,
          skip: 0,
          limit: 500,
          is_active: null,
        },
      });
      setData(response.data.items || []);
    } catch (error) {
      console.error('Failed to fetch dictionaries:', error);
      message.error('Ошибка загрузки справочника');
    } finally {
      setTableLoading(false);
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      width: 60,
    },
    {
      title: 'Значение',
      dataIndex: 'value',
      width: 300,
    },
    {
      title: 'Описание',
      dataIndex: 'description',
      ellipsis: true,
    },
    {
      title: 'Порядок',
      dataIndex: 'sort_order',
      width: 80,
      align: 'center',
    },
    {
      title: 'Активен',
      dataIndex: 'is_active',
      width: 80,
      align: 'center',
      render: (val) => (
        <Tag color={val ? 'success' : 'default'}>
          {val ? 'Да' : 'Нет'}
        </Tag>
      ),
    },
  ];

  if (isAdmin) {
    columns.push({
      title: 'Действия',
      width: 100,
      align: 'center',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            data-testid={`edit-dict-${record.id}`}
          />
          <Popconfirm
            title="Деактивировать элемент?"
            onConfirm={() => handleDelete(record.id)}
            okText="Да"
            cancelText="Нет"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              data-testid={`delete-dict-${record.id}`}
            />
          </Popconfirm>
        </Space>
      ),
    });
  }

  const handleCreate = () => {
    if (!isAdmin) {
      message.warning('Только администраторы могут добавлять элементы справочника');
      return;
    }
    setEditingItem(null);
    form.resetFields();
    form.setFieldsValue({ type: selectedType, sort_order: 0 });
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    if (!isAdmin) {
      message.warning('Только администраторы могут редактировать справочники');
      return;
    }
    setEditingItem(record);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    if (!isAdmin) {
      message.error('Недостаточно прав');
      return;
    }
    
    try {
      const values = await form.validateFields();
      setLoading(true);

      if (editingItem) {
        await api.patch(`/dictionaries/${editingItem.id}`, {
          value: values.value,
          description: values.description,
          sort_order: values.sort_order,
        });
        message.success('Элемент обновлен');
      } else {
        await api.post('/dictionaries', values);
        message.success('Элемент создан');
      }

      setModalVisible(false);
      loadData();
    } catch (error) {
      console.error('Save error:', error);
      if (error.response?.status === 403) {
        message.error('Недостаточно прав для выполнения операции');
      } else {
        message.error(error.response?.data?.detail || 'Ошибка сохранения');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!isAdmin) {
      message.error('Недостаточно прав');
      return;
    }
    
    try {
      await api.delete(`/dictionaries/${id}`);
      message.success('Элемент деактивирован');
      loadData();
    } catch (error) {
      if (error.response?.status === 403) {
        message.error('Недостаточно прав для выполнения операции');
      } else {
        message.error('Ошибка удаления');
      }
    }
  };

  const getCurrentTypeLabel = () => {
    const type = DICTIONARY_TYPES.find(t => t.value === selectedType);
    return type?.label || selectedType;
  };

  return (
    <div data-testid="dictionary-page">
      <div className="page-header">
        <h1>Справочники</h1>
        <Space>
          <span>Тип:</span>
          <Select
            value={selectedType}
            onChange={setSelectedType}
            options={DICTIONARY_TYPES}
            style={{ width: 250 }}
            data-testid="dictionary-type-selector"
          />
          {isAdmin && (
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleCreate}
              data-testid="create-dictionary-button"
            >
              Добавить
            </Button>
          )}
        </Space>
      </div>

      {!isAdmin && (
        <Alert
          message="Режим просмотра"
          description="Только администраторы могут добавлять и редактировать справочники."
          type="info"
          showIcon
          icon={<LockOutlined />}
          style={{ marginBottom: 16 }}
        />
      )}

      {}
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        size="small"
        bordered
        loading={tableLoading}
        pagination={false}
        scroll={{ y: 600 }}
        title={() => <strong>{getCurrentTypeLabel()}</strong>}
      />

      <Modal
        title={editingItem ? 'Редактирование элемента' : 'Новый элемент'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        confirmLoading={loading}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          <Form.Item
            name="type"
            label="Тип"
            rules={[{ required: true }]}
          >
            <Select options={DICTIONARY_TYPES} disabled={!!editingItem} />
          </Form.Item>
          <Form.Item
            name="value"
            label="Значение"
            rules={[{ required: true, message: 'Введите значение' }]}
          >
            <Input placeholder="Введите значение" data-testid="dictionary-value-input" />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={3} placeholder="Описание (необязательно)" />
          </Form.Item>
          <Form.Item name="sort_order" label="Порядок сортировки" initialValue={0}>
            <InputNumber min={0} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
};

export default DictionaryPage;
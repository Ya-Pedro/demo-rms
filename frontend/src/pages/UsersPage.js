import { tokenStorage } from '../tokenStorage';
import React, { useState, useEffect, useMemo } from 'react';
import { Table, Button, Space, Tag, Modal, Form, Input, Select, message, Popconfirm } from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined } from '@ant-design/icons';
import { api } from '../App';
import useIsMobile from '../hooks/useIsMobile';

const ALL_ROLES = [
  { value: 'superadmin', label: 'Суперадминистратор' },
  { value: 'admin', label: 'Администратор' },
  { value: 'recruiter', label: 'Рекрутер' },
];

const ADMIN_ROLES = [
  { value: 'admin', label: 'Администратор' },
  { value: 'recruiter', label: 'Рекрутер' },
];

const UsersPage = () => {
  const [form] = Form.useForm();
  const isMobile = useIsMobile();
  
  const [data, setData] = useState([]);
  const [tableLoading, setTableLoading] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [loading, setLoading] = useState(false);
  

  const currentUser = tokenStorage.getUser() || {};
  const isSuperadmin = currentUser?.role === 'superadmin';

  const availableRoles = useMemo(() => {

    if (isSuperadmin) {
      return ALL_ROLES;
    }

    return ADMIN_ROLES;
  }, [isSuperadmin]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setTableLoading(true);
    try {
      const response = await api.get('/users', {
        params: {
          skip: 0,
          limit: 1000,
        },
      });
      setData(response.data.items || []);
    } catch (error) {
      console.error('Failed to fetch users:', error);
      message.error('Ошибка загрузки пользователей');
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
      title: 'ФИО',
      dataIndex: 'full_name',
      width: 250,
    },
    {
      title: 'Email',
      dataIndex: 'email',
      width: 250,
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      width: 150,
      render: (role) => {
        const colors = {
          superadmin: 'red',
          admin: 'blue',
          recruiter: 'green',
        };
        const labels = {
          superadmin: 'Суперадмин',
          admin: 'Админ',
          recruiter: 'Рекрутер',
        };
        return <Tag color={colors[role]}>{labels[role] || role}</Tag>;
      },
    },
    {
      title: 'Активен',
      dataIndex: 'is_active',
      width: 100,
      align: 'center',
      render: (val) => (
        <Tag color={val ? 'success' : 'default'}>
          {val ? 'Да' : 'Нет'}
        </Tag>
      ),
    },
    {
      title: 'Действия',
      width: 120,
      align: 'center',
      render: (_, record) => (
        <Space size="small">
          <Button
            type="text"
            size="small"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            data-testid={`edit-user-${record.id}`}
          />
          <Popconfirm
            title="Удалить пользователя?"
            description="Это действие нельзя отменить."
            onConfirm={() => handleDelete(record.id)}
            okText="Удалить"
            cancelText="Отмена"
          >
            <Button
              type="text"
              size="small"
              danger
              icon={<DeleteOutlined />}
              data-testid={`delete-user-${record.id}`}
            />
          </Popconfirm>
        </Space>
      ),
    },
  ];

  const [newPasswordResult, setNewPasswordResult] = useState(null);

  const handleGeneratePassword = async () => {
    if (!editingUser) return;
    try {
      setLoading(true);
      const res = await api.post(`/users/${editingUser.id}/reset-password-admin`);
      setNewPasswordResult(res.data.new_password);
      message.success('Новый временный пароль сгенерирован');
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка генерации пароля');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = () => {
    setEditingUser(null);
    setNewPasswordResult(null);
    form.resetFields();
    form.setFieldsValue({ role: 'recruiter' });
    setModalVisible(true);
  };

  const handleEdit = (record) => {
    setEditingUser(record);
    setNewPasswordResult(null);
    form.setFieldsValue(record);
    setModalVisible(true);
  };

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      setLoading(true);

      if (editingUser) {
        await api.patch(`/users/${editingUser.id}`, {
          full_name: values.full_name,
          role: values.role,
          is_active: values.is_active,
        });
        message.success('Пользователь обновлен');
      } else {
        await api.post('/users', {
          email: values.email,
          full_name: values.full_name,
          role: values.role,
          password: values.password || null,
        });
        message.success('Пользователь создан. Данные отправлены на email (или в консоль).');
      }

      setModalVisible(false);
      loadData();
    } catch (error) {
      console.error('Save error:', error);
      message.error(error.response?.data?.detail || 'Ошибка сохранения');
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/users/${id}`);
      message.success('Пользователь удален');
      loadData();
    } catch (error) {
      message.error(error.response?.data?.detail || 'Ошибка удаления');
    }
  };
  

  const getEditRoles = (editingRecord) => {

    if (isSuperadmin) {
      return ALL_ROLES;
    }

    if (editingRecord?.role === 'superadmin') {
      return [{ value: 'superadmin', label: 'Суперадминистратор' }];
    }

    return ADMIN_ROLES;
  };

  return (
    <div data-testid="users-page">
      <div className="page-header">
        <h1>Пользователи</h1>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={handleCreate}
          data-testid="create-user-button"
        >
          Создать пользователя
        </Button>
      </div>

      {}
      <Table
        columns={columns}
        dataSource={data}
        rowKey="id"
        size="small"
        bordered
        loading={tableLoading}
        pagination={false}
        scroll={{ x: isMobile ? 900 : undefined, y: 'calc(100vh - 300px)' }}
      />

      <Modal
        title={editingUser ? 'Редактирование пользователя' : 'Новый пользователь'}
        open={modalVisible}
        onCancel={() => setModalVisible(false)}
        onOk={handleSave}
        confirmLoading={loading}
        okText="Сохранить"
        cancelText="Отмена"
        width={isMobile ? '95vw' : 500}
      >
        <Form form={form} layout="vertical" style={{ marginTop: 16 }}>
          {!editingUser && (
            <Form.Item
              name="email"
              label="Email"
              rules={[
                { required: true, message: 'Введите email' },
                { type: 'email', message: 'Неверный формат email' },
              ]}
            >
              <Input placeholder="user@company.ru" data-testid="user-email-input" />
            </Form.Item>
          )}
          <Form.Item
            name="full_name"
            label="ФИО"
            rules={[{ required: true, message: 'Введите ФИО' }]}
          >
            <Input placeholder="Иванов Иван Иванович" data-testid="user-name-input" />
          </Form.Item>
          <Form.Item
            name="role"
            label="Роль"
            rules={[{ required: true, message: 'Выберите роль' }]}
          >
            <Select 
              options={editingUser ? getEditRoles(editingUser) : availableRoles} 
              data-testid="user-role-select" 
            />
          </Form.Item>
          
          {!editingUser && (
            <Form.Item
              name="password"
              label="Временный пароль"
              rules={[
                { required: true, message: 'Введите временный пароль' },
                { min: 6, message: 'Минимум 6 символов' }
              ]}
            >
              <Input.Password placeholder="Укажите пароль (минимум 6 символов)" data-testid="user-password-input" />
            </Form.Item>
          )}
          
          {editingUser && (
            <Form.Item name="is_active" label="Активен">
              <Select
                options={[
                  { value: true, label: 'Да' },
                  { value: false, label: 'Нет' },
                ]}
              />
            </Form.Item>
          )}
        </Form>

        {editingUser && isSuperadmin && (
          <div style={{ marginTop: 24, paddingTop: 16, borderTop: '1px solid var(--border-color)' }}>
            <h4>Сброс пароля</h4>
            <p style={{ fontSize: 13, color: 'var(--text-color-secondary)' }}>
              Если пользователь забыл пароль, вы можете сгенерировать для него новый временный пароль.
            </p>
            <Button 
              onClick={handleGeneratePassword} 
              loading={loading}
              type="default"
              danger
            >
              Сгенерировать новый пароль
            </Button>
            
            {newPasswordResult && (
              <div style={{ 
                marginTop: 16, 
                padding: 12, 
                background: '#f6ffed', 
                border: '1px solid #b7eb8f',
                borderRadius: 4,
                fontSize: 14,
              }}>
                <strong>Новый временный пароль: </strong> 
                <span style={{ fontSize: 16, letterSpacing: 1, fontFamily: 'monospace' }}>{newPasswordResult}</span>
                <p style={{ marginTop: 8, marginBottom: 0, fontSize: 12, color: '#595959' }}>
                  Скопируйте и передайте этот пароль пользователю. При следующем входе система потребует его изменить.
                </p>
              </div>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
};

export default UsersPage;
import React from 'react';
import { Button, Checkbox, DatePicker, Input, Space } from 'antd';
import { SearchOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const getPopupContainer = () => document.body;

/**
 * Date range filter dropdown with "Только пустые (без даты)" support.
 */
export const DateRangeFilterDropdown = ({ setSelectedKeys, selectedKeys, confirm, clearFilters }) => {
  const isEmptySelected = selectedKeys?.[0] === 'empty' || selectedKeys?.[0] === '__empty__';

  const parseRange = (keys) => {
    if (!keys || keys.length === 0 || isEmptySelected) return [null, null];
    const [from, to] = (keys[0] || '').split('|');
    const d1 = from && dayjs(from, 'DD.MM.YY', true).isValid() ? dayjs(from, 'DD.MM.YY') : null;
    const d2 = to && dayjs(to, 'DD.MM.YY', true).isValid() ? dayjs(to, 'DD.MM.YY') : null;
    return [d1, d2];
  };

  const handleCheckboxChange = (e) => {
    setSelectedKeys(e.target.checked ? ['empty'] : []);
  };

  const handleDateChange = (dates) => {
    if (dates && dates[0] && dates[1]) {
      setSelectedKeys([`${dates[0].format('DD.MM.YY')}|${dates[1].format('DD.MM.YY')}`]);
    } else {
      setSelectedKeys([]);
    }
  };

  return (
    <div style={{ padding: '12px 16px', minWidth: 280 }}>
      <div style={{ marginBottom: 8, fontWeight: 500, fontSize: 13, color: 'var(--text-color)' }}>
        Выберите период
      </div>
      <DatePicker.RangePicker
        format="DD.MM.YYYY"
        placeholder={['Дата от', 'Дата до']}
        value={parseRange(selectedKeys)}
        disabled={isEmptySelected}
        getPopupContainer={getPopupContainer}
        style={{ width: '100%', marginBottom: 10 }}
        onChange={handleDateChange}
        allowClear
      />
      <div style={{ marginBottom: 12 }}>
        <Checkbox checked={isEmptySelected} onChange={handleCheckboxChange}>
          <span
            style={{
              fontSize: 13,
              color: isEmptySelected ? '#1677ff' : 'inherit',
              fontWeight: isEmptySelected ? 600 : 400,
            }}
          >
            Только пустые (без даты)
          </span>
        </Checkbox>
      </div>
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: 80 }}>
          Найти
        </Button>
        <Button onClick={() => { clearFilters(); confirm(); }} size="small" style={{ width: 80 }}>
          Сброс
        </Button>
      </Space>
    </div>
  );
};

const EmptyAwareInputFilterDropdown = ({
  setSelectedKeys,
  selectedKeys,
  confirm,
  clearFilters,
  placeholder = 'Поиск...',
  inputType,
  inputWidth = 188,
  buttonWidth = 90,
}) => {
  const isEmptySelected = selectedKeys?.[0] === '__empty__';

  return (
    <div style={{ padding: 8 }}>
      <Input
        type={inputType}
        autoFocus
        disabled={isEmptySelected}
        placeholder={placeholder}
        value={isEmptySelected ? '' : (selectedKeys?.[0] ?? '')}
        onChange={e => setSelectedKeys(e.target.value !== '' ? [e.target.value] : [])}
        onPressEnter={() => confirm()}
        style={{ width: inputWidth, marginBottom: 8, display: 'block' }}
      />
      <div style={{ marginBottom: 8 }}>
        <Checkbox
          checked={isEmptySelected}
          onChange={e => setSelectedKeys(e.target.checked ? ['__empty__'] : [])}
        >
          <span
            style={{
              fontSize: 12,
              color: isEmptySelected ? '#1677ff' : 'inherit',
              fontWeight: isEmptySelected ? 600 : 400,
            }}
          >
            Только пустые
          </span>
        </Checkbox>
      </div>
      <Space>
        <Button type="primary" onClick={() => confirm()} size="small" style={{ width: buttonWidth }}>
          Найти
        </Button>
        <Button
          onClick={() => { clearFilters(); confirm(); }}
          size="small"
          style={{ width: buttonWidth }}
        >
          Сброс
        </Button>
      </Space>
    </div>
  );
};

export const createDateFilterDropdown = () => ({
  filterDropdown: (props) => <DateRangeFilterDropdown {...props} />,
  filterDropdownProps: { getPopupContainer },
});

export const createTextFilterDropdown = ({ width = 188, buttonWidth = 90, showSearchIcon = false } = {}) => ({
  filterDropdown: (props) => (
    <EmptyAwareInputFilterDropdown
      {...props}
      placeholder="Поиск..."
      inputWidth={width}
      buttonWidth={buttonWidth}
    />
  ),
  filterDropdownProps: { getPopupContainer },
  ...(showSearchIcon ? { filterIcon: filtered => <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} /> } : {}),
});

export const createNumberFilterDropdown = ({
  width = 188,
  buttonWidth = 90,
  placeholder = 'Число...',
  inputType,
  showSearchIcon = false,
} = {}) => ({
  filterDropdown: (props) => (
    <EmptyAwareInputFilterDropdown
      {...props}
      placeholder={placeholder}
      inputType={inputType}
      inputWidth={width}
      buttonWidth={buttonWidth}
    />
  ),
  filterDropdownProps: { getPopupContainer },
  ...(showSearchIcon ? { filterIcon: filtered => <SearchOutlined style={{ color: filtered ? '#1890ff' : undefined }} /> } : {}),
});

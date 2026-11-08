import React, { useState, useEffect, useMemo, useCallback, useContext } from 'react';
import {
  Table,
  Button,
  Input,
  Space,
  Tabs,
  Modal,
  Popconfirm,
  Tooltip,
  Typography,
  Card,
  message,
  Tour,
  Tag,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  EditOutlined,
  FileExcelOutlined,
  SearchOutlined,
  DownloadOutlined,
  ReloadOutlined,
  CopyOutlined,
  QuestionCircleOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from '@ant-design/icons';
import { ThemeContext, api } from '../App';
import { tokenStorage } from '../tokenStorage';

const { Text, Title, Paragraph } = Typography;

function tourStep(selector, title, description) {
  return {
    target: () => document.querySelector(`[data-tour-notes="${selector}"]`) ?? null,
    title: <Text strong style={{ fontSize: 14 }}>{title}</Text>,
    description: (
      <Paragraph style={{ margin: 0, fontSize: 13, color: '#4b5563', lineHeight: '1.6' }}>
        {description}
      </Paragraph>
    ),
  };
}

const NOTES_TOUR_STEPS = [
  tourStep('tabs', '📑 Листы заметок', 'Переключайтесь между листами, создавайте новые с помощью кнопки «+» или закрывайте ненужные. На каждом листе своя независимая таблица.'),
  tourStep('search', '🔍 Поиск', 'Быстрый полнотекстовый поиск по всем колонкам и строкам текущего листа.'),
  tourStep('add-row', '➕ Добавить строку', 'Создает новую строку в таблице. Заполняйте данные по кандидатам или задачам.'),
  tourStep('add-col', '📊 Добавить столбец', 'Позволяет добавить новую пользовательскую колонку с любым названием.'),
  tourStep('rename-sheet', '✏️ Переименовать лист', 'Измените название текущего листа рабочей таблицы.'),
  tourStep('export-csv', '📥 Экспорт в Excel / CSV', 'Скачайте текущий лист рабочей таблицы в формате CSV для Excel с поддержкой кириллицы.'),
  tourStep('table', '📝 Редактирование ячеек', 'Нажмите на любую ячейку, чтобы ввести или отредактировать текст. Данные автоматически сохраняются.'),
  tourStep('tour-btn', '🎓 Обучение завершено!', 'Вы можете повторно запустить обучение по разделу Заметки в любой момент.'),
];

const LEGACY_STORAGE_KEY = 'rms_recruiter_notes_sheets_v1';
const SHARED_ADMIN_STORAGE_KEY = 'rms_notes_sheets_shared_admin';

const getNotesStorageKey = (user) => {
  if (user?.role === 'admin' || user?.role === 'superadmin') {
    return SHARED_ADMIN_STORAGE_KEY;
  }
  return user?.id ? `rms_notes_sheets_u_${user.id}` : LEGACY_STORAGE_KEY;
};

const DEFAULT_SHEETS = [
  {
    id: 'sheet_candidates',
    name: 'Кандидаты на рассмотрении',
    columns: [
      { key: 'col_fio', title: 'ФИО кандидата', width: 220 },
      { key: 'col_vacancy', title: 'Вакансия / Роль', width: 200 },
      { key: 'col_status', title: 'Статус / Этап', width: 160 },
      { key: 'col_salary', title: 'Ожидания (руб.)', width: 150 },
      { key: 'col_contacts', title: 'Контакты / ТГ', width: 180 },
      { key: 'col_notes', title: 'Заметки / Комментарий', width: 320 },
    ],
    rows: [
      {
        id: 'r_1',
        col_fio: 'Иванов Иван Иванович',
        col_vacancy: 'Senior Python Developer',
        col_status: 'Ожидает ТС',
        col_salary: '320 000 net',
        col_contacts: '@ivan_tg',
        col_notes: 'Хороший бэкграунд в fintech, готов на удаленку',
      },
      {
        id: 'r_2',
        col_fio: 'Смирнова Анна Сергеевна',
        col_vacancy: 'QA Automation Lead',
        col_status: 'Оффер согласован',
        col_salary: '280 000 gross',
        col_contacts: '+7 (999) 123-45-67',
        col_notes: 'Выход планируется со следующего месяца',
      },
    ],
  },
  {
    id: 'sheet_plan',
    name: 'План работы на неделю',
    columns: [
      { key: 'col_task', title: 'Задача / Приоритет', width: 250 },
      { key: 'col_deadline', title: 'Дедлайн', width: 140 },
      { key: 'col_status', title: 'Статус', width: 150 },
      { key: 'col_details', title: 'Детали', width: 350 },
    ],
    rows: [
      {
        id: 'r_plan_1',
        col_task: 'Скрининг по вакансии DevOps',
        col_deadline: 'Четверг',
        col_status: 'В работе',
        col_details: 'Нужно отобрать 5 релевантных резюме в IQHR',
      },
    ],
  },
];

// Dedicated isolated component for editable cell to eliminate table lag on typing
const EditableCell = React.memo(function EditableCell({
  value,
  onSave,
  isDarkMode,
  onEditingChange,
}) {
  const [editing, setEditing] = useState(false);
  const [currentVal, setCurrentVal] = useState(value ?? '');

  useEffect(() => {
    if (!editing) {
      setCurrentVal(value ?? '');
    }
  }, [value, editing]);

  const handleStartEditing = () => {
    setEditing(true);
    if (onEditingChange) onEditingChange(true);
  };

  const handleSave = () => {
    setEditing(false);
    if (onEditingChange) onEditingChange(false);
    if (currentVal !== (value ?? '')) {
      onSave(currentVal);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSave();
    } else if (e.key === 'Escape') {
      setCurrentVal(value ?? '');
      setEditing(false);
      if (onEditingChange) onEditingChange(false);
    }
  };

  if (editing) {
    return (
      <Input.TextArea
        autoFocus
        autoSize={{ minRows: 1, maxRows: 5 }}
        value={currentVal}
        onChange={(e) => setCurrentVal(e.target.value)}
        onBlur={handleSave}
        onKeyDown={handleKeyDown}
        style={{ padding: '2px 6px', fontSize: 13 }}
      />
    );
  }

  const text = value ?? '';

  return (
    <div
      onClick={handleStartEditing}
      style={{
        cursor: 'pointer',
        minHeight: 28,
        padding: '4px 6px',
        borderRadius: 4,
        backgroundColor: isDarkMode ? 'transparent' : '#ffffff',
        border: '1px dashed transparent',
        transition: 'border-color 0.15s ease',
        wordBreak: 'break-word',
        whiteSpace: 'pre-wrap',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#1890ff';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = 'transparent';
      }}
      title="Нажмите для ввода или редактирования"
    >
      {text ? (
        <span>{text}</span>
      ) : (
        <span style={{ color: '#bfbfbf', fontStyle: 'italic', fontSize: 12 }}>
          (клик для ввода)
        </span>
      )}
    </div>
  );
});

const RowDragContext = React.createContext({
  draggingId: null,
  dragOverState: null,
  activeHandleRowId: null,
  isDarkMode: false,
  handleDragStart: () => {},
  handleDragOver: () => {},
  handleDragLeave: () => {},
  handleDrop: () => {},
  handleDragEnd: () => {},
});

const DraggableRow = React.memo(function DraggableRow({ children, className, style, ...restProps }) {
  const {
    draggingId,
    dragOverState,
    activeHandleRowId,
    isDarkMode,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleDragEnd,
  } = useContext(RowDragContext);

  const rowId = restProps['data-row-id'];
  const isDragging = draggingId === rowId;
  const isOver = dragOverState?.id === rowId;
  const pos = isOver ? dragOverState.position : null;

  const rowStyle = {
    ...style,
    transition: 'background-color 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease',
  };

  if (isDragging) {
    rowStyle.opacity = 0.45;
    rowStyle.backgroundColor = isDarkMode ? '#1f242c' : '#f0f5ff';
  } else if (isOver) {
    rowStyle.backgroundColor = isDarkMode ? 'rgba(22, 119, 255, 0.12)' : '#f0f7ff';
    if (pos === 'top') {
      rowStyle.boxShadow = 'inset 0 3px 0 0 #1677ff';
    } else if (pos === 'bottom') {
      rowStyle.boxShadow = 'inset 0 -3px 0 0 #1677ff';
    }
  }

  return (
    <tr
      {...restProps}
      className={className}
      style={rowStyle}
      draggable={activeHandleRowId === rowId}
      onDragStart={(e) => handleDragStart(e, rowId)}
      onDragOver={(e) => handleDragOver(e, rowId)}
      onDragLeave={(e) => handleDragLeave(e, rowId)}
      onDrop={(e) => handleDrop(e, rowId)}
      onDragEnd={handleDragEnd}
    >
      {children}
    </tr>
  );
});

const TABLE_COMPONENTS = {
  body: {
    row: DraggableRow,
  },
};
const normalizeSheet = (s, idx = 0) => {
  if (!s || typeof s !== 'object') {
    return {
      id: `sheet_${idx + 1}`,
      name: `Лист ${idx + 1}`,
      columns: [
        { key: 'col_1', title: 'Столбец 1', width: 200 },
        { key: 'col_notes', title: 'Заметки', width: 300 },
      ],
      rows: [
        { id: `r_init_${idx}`, col_1: '', col_notes: '' },
      ],
    };
  }

  const id = s.id || `sheet_${idx + 1}`;
  const name = s.name || `Лист ${idx + 1}`;
  let columns = Array.isArray(s.columns) ? s.columns : null;
  let rows = Array.isArray(s.rows) ? s.rows : null;

  // If sheet was saved as a matrix (data: [[...], [...]])
  if ((!columns || !rows) && Array.isArray(s.data) && s.data.length > 0) {
    const headers = s.data[0] || [];
    columns = headers.map((h, ci) => ({
      key: `col_${ci + 1}`,
      title: String(h || `Столбец ${ci + 1}`),
      width: 200,
    }));
    rows = s.data.slice(1).map((row, ri) => {
      const rObj = { id: `r_${ri + 1}` };
      columns.forEach((c, ci) => {
        rObj[c.key] = row[ci] !== undefined ? String(row[ci]) : '';
      });
      return rObj;
    });
  }

  if (!columns || columns.length === 0) {
    columns = [
      { key: 'col_1', title: 'Столбец 1', width: 200 },
      { key: 'col_notes', title: 'Заметки', width: 300 },
    ];
  }
  if (!rows) {
    rows = [];
  }

  return { id, name, columns, rows };
};

const normalizeSheets = (sheetsList) => {
  if (!Array.isArray(sheetsList) || sheetsList.length === 0) {
    return DEFAULT_SHEETS;
  }
  return sheetsList.map((s, idx) => normalizeSheet(s, idx));
};

export default function NotesPage() {
  const { isDarkMode } = useContext(ThemeContext);

  const user = tokenStorage.getUser();
  const userId = user?.id || null;
  const isAdminRole = user?.role === 'admin' || user?.role === 'superadmin';
  const isRecruiter = user?.role === 'recruiter';
  const notesStorageKey = getNotesStorageKey(user);

  const loadInitialSheets = useCallback(() => {
    try {
      const savedUser = localStorage.getItem(notesStorageKey);
      if (savedUser) {
        const parsed = JSON.parse(savedUser);
        if (Array.isArray(parsed) && parsed.length > 0) return normalizeSheets(parsed);
      }
      // Migration fallback: if admin/superadmin had personal notes before shared migration
      if (isAdminRole && userId) {
        const savedPersonal = localStorage.getItem(`rms_notes_sheets_u_${userId}`);
        if (savedPersonal) {
          const parsed = JSON.parse(savedPersonal);
          if (Array.isArray(parsed) && parsed.length > 0) return normalizeSheets(parsed);
        }
      }
      // Fallback / migration from legacy key if user storage is empty
      const savedLegacy = localStorage.getItem(LEGACY_STORAGE_KEY);
      if (savedLegacy) {
        const parsed = JSON.parse(savedLegacy);
        if (Array.isArray(parsed) && parsed.length > 0) return normalizeSheets(parsed);
      }
    } catch (e) {
      console.error('Failed to load notes from localStorage', e);
    }
    return DEFAULT_SHEETS;
  }, [notesStorageKey, isAdminRole, userId]);

  const [sheets, setSheets] = useState(loadInitialSheets);
  const [activeSheetId, setActiveSheetId] = useState(() => {
    return sheets[0]?.id || 'sheet_candidates';
  });

  const [syncStatus, setSyncStatus] = useState('idle'); // 'idle' | 'syncing' | 'saved' | 'error'
  const [lastUpdatedInfo, setLastUpdatedInfo] = useState(null);
  const [refreshLoading, setRefreshLoading] = useState(false);

  const isInitialLoadedRef = React.useRef(false);
  const isRemoteUpdateRef = React.useRef(false);
  const isEditingCellRef = React.useRef(false);
  const saveTimeoutRef = React.useRef(null);
  const latestSheetsRef = React.useRef(sheets);
  latestSheetsRef.current = sheets;
  const lastSyncedJsonRef = React.useRef('');

  const saveToServer = useCallback(async (sheetsToSave) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
    const jsonStr = JSON.stringify(sheetsToSave);
    if (jsonStr === lastSyncedJsonRef.current) {
      setSyncStatus('saved');
      return;
    }

    setSyncStatus('syncing');
    try {
      const res = await api.put('/notes', { sheets: sheetsToSave });
      lastSyncedJsonRef.current = jsonStr;
      setSyncStatus('saved');
      if (res?.data?.updated_at || res?.data?.updated_by_name) {
        setLastUpdatedInfo({
          at: res.data.updated_at,
          by: res.data.updated_by_name,
        });
      }
    } catch (err) {
      console.error('Failed to save notes to backend', err);
      setSyncStatus('error');
    }
  }, []);

  const debouncedSave = useCallback((sheetsToSave) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    setSyncStatus('syncing');
    saveTimeoutRef.current = setTimeout(() => {
      saveToServer(sheetsToSave);
    }, 400);
  }, [saveToServer]);

  const fetchNotes = useCallback(async (isManual = false) => {
    if (isManual) setRefreshLoading(true);
    try {
      const res = await api.get('/notes');
      if (res?.data) {
        const rawSheets = res.data.sheets;
        if (Array.isArray(rawSheets) && rawSheets.length > 0) {
          const serverSheets = normalizeSheets(rawSheets);
          const serverJson = JSON.stringify(serverSheets);

          if (!isEditingCellRef.current) {
            const localJson = JSON.stringify(latestSheetsRef.current);
            if (serverJson !== localJson) {
              isRemoteUpdateRef.current = true;
              setSheets(serverSheets);
              lastSyncedJsonRef.current = serverJson;
              try {
                localStorage.setItem(notesStorageKey, serverJson);
              } catch (e) {}

              setActiveSheetId((currActive) => {
                if (serverSheets.some((s) => s.id === currActive)) {
                  return currActive;
                }
                return serverSheets[0]?.id || 'sheet_candidates';
              });
            }
          }
        } else if (!isInitialLoadedRef.current) {
          // If server has no sheets yet on initial load, seed with initial local/default sheets
          const localSheets = normalizeSheets(loadInitialSheets());
          isRemoteUpdateRef.current = true;
          setSheets(localSheets);
          lastSyncedJsonRef.current = JSON.stringify(localSheets);
          try {
            localStorage.setItem(notesStorageKey, JSON.stringify(localSheets));
          } catch (e) {}
          saveToServer(localSheets);
        }

        if (res.data.updated_at || res.data.updated_by_name) {
          setLastUpdatedInfo({
            at: res.data.updated_at,
            by: res.data.updated_by_name,
          });
        }
        setSyncStatus('saved');
        if (isManual) {
          message.success('Заметки успешно обновлены');
        }
      }
    } catch (err) {
      console.error('Failed to fetch notes from backend', err);
      if (isManual) {
        message.error('Ошибка загрузки заметок с сервера');
      }
    } finally {
      isInitialLoadedRef.current = true;
      if (isManual) setRefreshLoading(false);
    }
  }, [notesStorageKey, loadInitialSheets, saveToServer]);

  // Initial load on mount or key change
  useEffect(() => {
    isInitialLoadedRef.current = false;
    fetchNotes(false);
  }, [fetchNotes]);

  // Periodic background sync (every 4 seconds when tab is active and not syncing or editing) + on window focus
  useEffect(() => {
    const onFocus = () => {
      if (document.visibilityState === 'visible' && syncStatus !== 'syncing' && !isEditingCellRef.current) {
        fetchNotes(false);
      }
    };
    window.addEventListener('focus', onFocus);

    const interval = setInterval(() => {
      if (document.visibilityState === 'visible' && syncStatus !== 'syncing' && !isEditingCellRef.current) {
        fetchNotes(false);
      }
    }, 4000);

    return () => {
      window.removeEventListener('focus', onFocus);
      clearInterval(interval);
    };
  }, [fetchNotes, syncStatus]);

  // Persist to localStorage and sync to backend with debounce
  useEffect(() => {
    try {
      localStorage.setItem(notesStorageKey, JSON.stringify(sheets));
    } catch (e) {
      console.error('Failed to save notes to localStorage', e);
    }

    if (!isInitialLoadedRef.current) {
      return;
    }

    if (isRemoteUpdateRef.current) {
      isRemoteUpdateRef.current = false;
      return;
    }

    debouncedSave(sheets);
  }, [sheets, notesStorageKey, debouncedSave]);

  const [searchFilter, setSearchFilter] = useState('');
  const [columnSearch, setColumnSearch] = useState({});

  // Row Drag-and-Drop state and pagination
  const [draggingId, setDraggingId] = useState(null);
  const [dragOverState, setDragOverState] = useState(null); // { id: string, position: 'top' | 'bottom' }
  const [activeHandleRowId, setActiveHandleRowId] = useState(null);
  const [pagination, setPagination] = useState({ current: 1, pageSize: 25 });

  useEffect(() => {
    const handleWindowMouseUp = () => {
      setActiveHandleRowId(null);
    };
    window.addEventListener('mouseup', handleWindowMouseUp);
    return () => window.removeEventListener('mouseup', handleWindowMouseUp);
  }, []);

  // Column management modal
  const [colModalVisible, setColModalVisible] = useState(false);
  const [newColTitle, setNewColTitle] = useState('');

  // Column rename modal
  const [renameColModalVisible, setRenameColModalVisible] = useState(false);
  const [editingColKey, setEditingColKey] = useState(null);
  const [renameColTitle, setRenameColTitle] = useState('');

  // Sheet rename modal
  const [renameModalVisible, setRenameModalVisible] = useState(false);
  const [renameSheetTitle, setRenameSheetTitle] = useState('');

  // Tour state - only for recruiter role (hidden for admin and superadmin)
  const tourKey = `rms_notes_tour_completed_${userId || 'default'}`;
  const [tourOpen, setTourOpen] = useState(false);

  useEffect(() => {
    if (isRecruiter && !localStorage.getItem(tourKey)) {
      setTourOpen(true);
    }
  }, [isRecruiter, tourKey]);

  const handleTourClose = () => {
    setTourOpen(false);
    localStorage.setItem(tourKey, 'true');
  };

  const activeSheet = useMemo(() => {
    const raw = sheets.find((s) => s.id === activeSheetId) || sheets[0] || null;
    if (!raw) return null;
    return {
      ...raw,
      columns: Array.isArray(raw.columns) ? raw.columns : [],
      rows: Array.isArray(raw.rows) ? raw.rows : [],
    };
  }, [sheets, activeSheetId]);

  // Handle active sheet update
  const updateActiveSheet = useCallback((updater) => {
    setSheets((prev) =>
      prev.map((s) => {
        if (s.id === activeSheetId) {
          const safeSheet = {
            ...s,
            columns: Array.isArray(s.columns) ? s.columns : [],
            rows: Array.isArray(s.rows) ? s.rows : [],
          };
          const updated = updater(safeSheet);
          return {
            ...updated,
            columns: Array.isArray(updated.columns) ? updated.columns : [],
            rows: Array.isArray(updated.rows) ? updated.rows : [],
          };
        }
        return s;
      })
    );
  }, [activeSheetId]);

  // Add sheet
  const handleAddSheet = useCallback(() => {
    const newId = `sheet_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const currentList = latestSheetsRef.current || [];
    const newSheet = {
      id: newId,
      name: `Лист ${currentList.length + 1}`,
      columns: [
        { key: `col_1`, title: 'Столбец 1', width: 200 },
        { key: `col_2`, title: 'Столбец 2', width: 200 },
        { key: `col_notes`, title: 'Заметки', width: 300 },
      ],
      rows: [
        { id: `r_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`, col_1: '', col_2: '', col_notes: '' },
      ],
    };
    const updated = [...currentList, newSheet];
    setSheets(updated);
    setActiveSheetId(newId);
    saveToServer(updated);
    message.success(`Создан лист "${newSheet.name}"`);
  }, [saveToServer]);

  // Delete sheet
  const handleDeleteSheet = useCallback((targetId) => {
    const currentList = latestSheetsRef.current || [];
    if (currentList.length <= 1) {
      message.warning('Нельзя удалить единственный лист');
      return;
    }
    const targetSheet = currentList.find((s) => s.id === targetId);
    const sheetName = targetSheet?.name || 'Лист';

    Modal.confirm({
      title: `Удалить лист «${sheetName}»?`,
      content: 'Все данные на этом листе будут удалены безвозвратно. Вы уверены, что хотите продолжить?',
      okText: 'Удалить безвозвратно',
      okType: 'danger',
      cancelText: 'Отмена',
      onOk: () => {
        const filtered = (latestSheetsRef.current || []).filter((s) => s.id !== targetId);
        setSheets(filtered);
        setActiveSheetId((currActive) => {
          if (currActive === targetId) {
            return filtered[0]?.id || 'sheet_candidates';
          }
          return currActive;
        });
        saveToServer(filtered);
        message.success(`Лист «${sheetName}» удален`);
      },
    });
  }, [saveToServer]);

  // Rename sheet
  const handleOpenRename = useCallback(() => {
    if (!activeSheet) return;
    setRenameSheetTitle(activeSheet.name);
    setRenameModalVisible(true);
  }, [activeSheet]);

  const handleSaveRename = useCallback(() => {
    if (!renameSheetTitle.trim()) {
      message.warning('Название листа не может быть пустым');
      return;
    }
    const newTitle = renameSheetTitle.trim();
    const updated = (latestSheetsRef.current || []).map((s) =>
      s.id === activeSheetId ? { ...s, name: newTitle } : s
    );
    setSheets(updated);
    saveToServer(updated);
    setRenameModalVisible(false);
    message.success('Лист переименован');
  }, [renameSheetTitle, activeSheetId, saveToServer]);

  // Add row
  const handleAddRow = useCallback(() => {
    if (!activeSheet) return;
    const newRow = { id: `r_${Date.now()}_${Math.random().toString(36).substring(2, 7)}` };
    activeSheet.columns.forEach((c) => {
      newRow[c.key] = '';
    });
    updateActiveSheet((s) => ({
      ...s,
      rows: [newRow, ...s.rows],
    }));
    message.success('Строка добавлена');
  }, [activeSheet, updateActiveSheet]);

  // Duplicate row
  const handleDuplicateRow = useCallback((record) => {
    if (!activeSheet) return;
    const newId = `r_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
    const duplicated = { ...record, id: newId };
    updateActiveSheet((s) => {
      const idx = s.rows.findIndex((r) => r.id === record.id);
      const newRows = [...s.rows];
      if (idx >= 0) {
        newRows.splice(idx + 1, 0, duplicated);
      } else {
        newRows.unshift(duplicated);
      }
      return { ...s, rows: newRows };
    });
    message.success('Строка продублирована');
  }, [activeSheet, updateActiveSheet]);

  // Delete row
  const handleDeleteRow = useCallback((rowId) => {
    updateActiveSheet((s) => ({
      ...s,
      rows: s.rows.filter((r) => r.id !== rowId),
    }));
    message.success('Строка удалена');
  }, [updateActiveSheet]);

  // Add column
  const handleAddColumn = useCallback(() => {
    if (!newColTitle.trim()) {
      message.warning('Введите название столбца');
      return;
    }
    const newColKey = `col_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
    const newCol = {
      key: newColKey,
      title: newColTitle.trim(),
      width: 180,
    };
    updateActiveSheet((s) => ({
      ...s,
      columns: [...s.columns, newCol],
      rows: s.rows.map((r) => ({ ...r, [newColKey]: '' })),
    }));
    setNewColTitle('');
    setColModalVisible(false);
    message.success(`Столбец "${newCol.title}" добавлен`);
  }, [newColTitle, updateActiveSheet]);

  // Rename column
  const handleOpenRenameCol = useCallback((colKey, currentTitle) => {
    setEditingColKey(colKey);
    setRenameColTitle(currentTitle);
    setRenameColModalVisible(true);
  }, []);

  const handleSaveRenameCol = useCallback(() => {
    if (!renameColTitle.trim()) {
      message.warning('Название столбца не может быть пустым');
      return;
    }
    updateActiveSheet((s) => ({
      ...s,
      columns: s.columns.map((c) =>
        c.key === editingColKey ? { ...c, title: renameColTitle.trim() } : c
      ),
    }));
    setRenameColModalVisible(false);
    setEditingColKey(null);
    message.success('Столбец переименован');
  }, [renameColTitle, editingColKey, updateActiveSheet]);

  // Delete column
  const handleDeleteColumn = useCallback((colKey) => {
    if (!activeSheet) return;
    if (activeSheet.columns.length <= 1) {
      message.warning('В таблице должен оставаться хотя бы один столбец');
      return;
    }
    updateActiveSheet((s) => ({
      ...s,
      columns: s.columns.filter((c) => c.key !== colKey),
    }));
    setColumnSearch((prev) => {
      const next = { ...prev };
      delete next[colKey];
      return next;
    });
    message.success('Столбец удален');
  }, [activeSheet, updateActiveSheet]);

  // Cell save callback
  const handleCellSave = useCallback((rowId, colKey, newVal) => {
    updateActiveSheet((s) => ({
      ...s,
      rows: s.rows.map((r) =>
        r.id === rowId ? { ...r, [colKey]: newVal } : r
      ),
    }));
  }, [updateActiveSheet]);

  // Filtered rows
  const filteredRows = useMemo(() => {
    if (!activeSheet || !Array.isArray(activeSheet.rows)) return [];
    const cols = Array.isArray(activeSheet.columns) ? activeSheet.columns : [];
    return activeSheet.rows.filter((row) => {
      if (!row) return false;
      // Global search
      if (searchFilter.trim()) {
        const needle = searchFilter.toLowerCase();
        const matchesGlobal = cols.some((col) => {
          const val = (row[col.key] ?? '').toString().toLowerCase();
          return val.includes(needle);
        });
        if (!matchesGlobal) return false;
      }
      // Per-column search
      for (const [colKey, query] of Object.entries(columnSearch)) {
        if (query && query.trim()) {
          const val = (row[colKey] ?? '').toString().toLowerCase();
          if (!val.includes(query.toLowerCase().trim())) {
            return false;
          }
        }
      }
      return true;
    });
  }, [activeSheet, searchFilter, columnSearch]);

  const hasFilter = searchFilter.trim() !== '' || Object.values(columnSearch).some((v) => v && v.trim() !== '');

  const handleResetFilters = useCallback(() => {
    setSearchFilter('');
    setColumnSearch({});
  }, []);

  // Export current sheet to CSV with BOM and semicolon (Excel format)
  const handleExportCSV = useCallback(() => {
    if (!activeSheet || !Array.isArray(activeSheet.columns) || !Array.isArray(activeSheet.rows)) return;
    const rowsToExport = filteredRows.length > 0 ? filteredRows : activeSheet.rows;

    const headerRow = activeSheet.columns.map((c) => `"${(c.title || '').replace(/"/g, '""')}"`).join(';');
    const dataRows = rowsToExport.map((r) =>
      activeSheet.columns
        .map((c) => `"${(r[c.key] ?? '').toString().replace(/"/g, '""')}"`)
        .join(';')
    );
    const csvContent = '\uFEFF' + [headerRow, ...dataRows].join('\r\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const safeSheetName = (activeSheet.name || 'Лист').replace(/[/\\?%*:|"<>]/g, '_');
    link.setAttribute('download', `${safeSheetName}_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    message.success(`Экспортировано ${rowsToExport.length} строк в формате CSV`);
  }, [activeSheet, filteredRows]);

  // Move row via drag and drop
  const handleMoveRow = useCallback((sourceId, targetId, position = 'before') => {
    if (sourceId === targetId) return;
    updateActiveSheet((sheet) => {
      const rows = [...sheet.rows];
      const sourceIndex = rows.findIndex((r) => r.id === sourceId);
      if (sourceIndex === -1) return sheet;

      const [movedRow] = rows.splice(sourceIndex, 1);
      const targetIndex = rows.findIndex((r) => r.id === targetId);
      if (targetIndex === -1) {
        rows.push(movedRow);
      } else {
        const insertIndex = position === 'after' ? targetIndex + 1 : targetIndex;
        rows.splice(insertIndex, 0, movedRow);
      }
      return { ...sheet, rows };
    });
    message.success('Порядок строк изменен');
  }, [updateActiveSheet]);

  // Move row one step up or down
  const handleMoveRowStep = useCallback((rowId, direction) => {
    updateActiveSheet((sheet) => {
      const rows = [...sheet.rows];
      if (hasFilter) {
        const filteredIdx = filteredRows.findIndex((r) => r.id === rowId);
        if (filteredIdx === -1) return sheet;
        const targetFilteredIdx = direction === 'up' ? filteredIdx - 1 : filteredIdx + 1;
        if (targetFilteredIdx < 0 || targetFilteredIdx >= filteredRows.length) return sheet;
        const targetNeighbor = filteredRows[targetFilteredIdx];

        const sourceIndex = rows.findIndex((r) => r.id === rowId);
        if (sourceIndex === -1) return sheet;
        const [moved] = rows.splice(sourceIndex, 1);

        const targetIndex = rows.findIndex((r) => r.id === targetNeighbor.id);
        if (targetIndex === -1) {
          rows.push(moved);
        } else {
          const insertIndex = direction === 'up' ? targetIndex : targetIndex + 1;
          rows.splice(insertIndex, 0, moved);
        }
        return { ...sheet, rows };
      }

      const index = rows.findIndex((r) => r.id === rowId);
      if (index === -1) return sheet;
      const targetIndex = direction === 'up' ? index - 1 : index + 1;
      if (targetIndex < 0 || targetIndex >= rows.length) return sheet;

      const temp = rows[index];
      rows[index] = rows[targetIndex];
      rows[targetIndex] = temp;

      return { ...sheet, rows };
    });
  }, [updateActiveSheet, hasFilter, filteredRows]);

  const handleDragStart = useCallback((e, rowId) => {
    e.stopPropagation();
    setDraggingId(rowId);
    e.dataTransfer.setData('text/plain', rowId);
    e.dataTransfer.effectAllowed = 'move';
  }, []);

  const handleDragOver = useCallback((e, rowId) => {
    e.preventDefault();
    e.stopPropagation();
    e.dataTransfer.dropEffect = 'move';
    if (!draggingId || draggingId === rowId) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const isTop = e.clientY < rect.top + rect.height / 2;
    const position = isTop ? 'top' : 'bottom';

    setDragOverState((prev) => {
      if (prev?.id === rowId && prev?.position === position) return prev;
      return { id: rowId, position };
    });
  }, [draggingId]);

  const handleDragLeave = useCallback((e, rowId) => {
    e.stopPropagation();
    if (e.currentTarget.contains(e.relatedTarget)) return;
    setDragOverState((prev) => (prev?.id === rowId ? null : prev));
  }, []);

  const handleDrop = useCallback((e, targetRowId) => {
    e.preventDefault();
    e.stopPropagation();
    const sourceId = draggingId || e.dataTransfer.getData('text/plain');
    if (sourceId && targetRowId && sourceId !== targetRowId) {
      const position = dragOverState?.position === 'top' ? 'before' : 'after';
      handleMoveRow(sourceId, targetRowId, position);
    }
    setDraggingId(null);
    setDragOverState(null);
    setActiveHandleRowId(null);
  }, [draggingId, dragOverState, handleMoveRow]);

  const handleDragEnd = useCallback(() => {
    setDraggingId(null);
    setDragOverState(null);
    setActiveHandleRowId(null);
  }, []);

  const dragContextValue = useMemo(() => ({
    draggingId,
    dragOverState,
    activeHandleRowId,
    isDarkMode,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleDragEnd,
  }), [
    draggingId,
    dragOverState,
    activeHandleRowId,
    isDarkMode,
    handleDragStart,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleDragEnd,
  ]);

  // Dynamic table columns configuration
  const tableColumns = useMemo(() => {
    if (!activeSheet || !Array.isArray(activeSheet.columns)) return [];
    const cols = activeSheet.columns.map((c) => ({
      title: (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span style={{ fontWeight: 600 }}>{c.title}</span>
            <Space size={2}>
              <Tooltip title="Переименовать столбец">
                <Button
                  type="text"
                  size="small"
                  icon={<EditOutlined style={{ fontSize: 12, color: '#1890ff' }} />}
                  style={{ width: 20, height: 20, padding: 0 }}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleOpenRenameCol(c.key, c.title);
                  }}
                />
              </Tooltip>
              <Popconfirm
                title={`Удалить столбец "${c.title}"?`}
                onConfirm={() => handleDeleteColumn(c.key)}
                okText="Да"
                cancelText="Нет"
              >
                <Tooltip title="Удалить этот столбец">
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined style={{ fontSize: 12, color: '#ff4d4f' }} />}
                    style={{ width: 20, height: 20, padding: 0 }}
                  />
                </Tooltip>
              </Popconfirm>
            </Space>
          </div>
          <Input
            size="small"
            placeholder="Фильтр..."
            prefix={<SearchOutlined style={{ fontSize: 11, color: '#8c8c8c' }} />}
            value={columnSearch[c.key] || ''}
            onChange={(e) =>
              setColumnSearch((prev) => ({
                ...prev,
                [c.key]: e.target.value,
              }))
            }
            allowClear
            style={{ fontSize: 12 }}
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      ),
      dataIndex: c.key,
      key: c.key,
      width: c.width || 200,
      render: (text, record) => (
        <EditableCell
          value={text}
          onSave={(newVal) => handleCellSave(record.id, c.key, newVal)}
          onEditingChange={(isEditing) => {
            isEditingCellRef.current = isEditing;
          }}
          isDarkMode={isDarkMode}
        />
      ),
    }));

    // Row order column (compact static column for row number)
    cols.unshift({
      title: '№',
      key: '_row_order',
      width: 52,
      minWidth: 52,
      maxWidth: 52,
      fixed: 'left',
      align: 'center',
      className: 'static-row-num-col',
      render: (_, record, index) => {
        const rowNumber = (pagination.current - 1) * pagination.pageSize + index + 1;
        return (
          <span
            style={{
              color: isDarkMode ? '#8b949e' : '#64748b',
              fontWeight: 500,
              fontVariantNumeric: 'tabular-nums',
              whiteSpace: 'nowrap',
              display: 'inline-block',
            }}
          >
            {rowNumber}
          </span>
        );
      },
    });

    // Actions column
    cols.push({
      title: 'Действия',
      key: 'actions',
      width: 136,
      fixed: 'right',
      align: 'center',
      render: (_, record, index) => {
        const globalIndex = (pagination.current - 1) * pagination.pageSize + index;
        const isFirst = globalIndex === 0;
        const isLast = globalIndex === (filteredRows.length - 1);
        return (
          <Space size={2}>
            <Tooltip title="Переместить выше">
              <Button
                type="text"
                size="small"
                icon={<ArrowUpOutlined style={{ fontSize: 12 }} />}
                disabled={isFirst}
                onClick={() => handleMoveRowStep(record.id, 'up')}
                style={{ width: 24, height: 24, padding: 0 }}
              />
            </Tooltip>
            <Tooltip title="Переместить ниже">
              <Button
                type="text"
                size="small"
                icon={<ArrowDownOutlined style={{ fontSize: 12 }} />}
                disabled={isLast}
                onClick={() => handleMoveRowStep(record.id, 'down')}
                style={{ width: 24, height: 24, padding: 0 }}
              />
            </Tooltip>
            <Tooltip title="Дублировать строку">
              <Button
                type="text"
                icon={<CopyOutlined style={{ color: '#1890ff', fontSize: 12 }} />}
                size="small"
                onClick={() => handleDuplicateRow(record)}
                style={{ width: 24, height: 24, padding: 0 }}
              />
            </Tooltip>
            <Popconfirm
              title="Удалить эту строку?"
              onConfirm={() => handleDeleteRow(record.id)}
              okText="Да"
              cancelText="Нет"
            >
              <Tooltip title="Удалить строку">
                <Button
                  type="text"
                  danger
                  icon={<DeleteOutlined style={{ fontSize: 12 }} />}
                  size="small"
                  style={{ width: 24, height: 24, padding: 0 }}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        );
      },
    });

    return cols;
  }, [
    activeSheet,
    columnSearch,
    isDarkMode,
    pagination,
    filteredRows,
    handleOpenRenameCol,
    handleDeleteColumn,
    handleCellSave,
    handleDuplicateRow,
    handleDeleteRow,
    handleMoveRowStep,
  ]);

  const tabItems = sheets.map((s) => ({
    key: s.id,
    label: (
      <span>
        <FileExcelOutlined style={{ marginRight: 6, color: '#107c41' }} />
        {s.name}
      </span>
    ),
    closable: sheets.length > 1,
  }));

  return (
    <div style={{ padding: 24 }}>
      {/* Header card */}
      <Card
        style={{
          marginBottom: 16,
          background: isDarkMode ? '#161b22' : '#ffffff',
          borderRadius: 12,
        }}
        bodyStyle={{
          padding: '16px 20px',
        }}
      >
        {/* Top row: Title, status tags, and last updated info */}
        <div>
          <Space align="center" wrap size={10}>
            <Title level={4} style={{ margin: 0 }}>
              Рабочие заметки
            </Title>
            {!isAdminRole && (
              <Tag color="default" style={{ margin: 0, fontWeight: 500, borderRadius: 4 }}>
                Личные заметки
              </Tag>
            )}
            {syncStatus === 'syncing' && (
              <Tag icon={<SyncOutlined spin />} color="processing" style={{ margin: 0, borderRadius: 4 }}>
                Сохранение...
              </Tag>
            )}
            {syncStatus === 'saved' && (
              <Tag icon={<CheckCircleOutlined />} color="success" style={{ margin: 0, borderRadius: 4 }}>
                Сохранено
              </Tag>
            )}
            {syncStatus === 'error' && (
              <Tag color="error" style={{ margin: 0, borderRadius: 4 }}>
                Ошибка сохранения
              </Tag>
            )}
            {lastUpdatedInfo?.by && (
              <span style={{ fontSize: 13, color: isDarkMode ? '#8b949e' : '#64748b', fontStyle: 'italic' }}>
                (посл. изменение: {lastUpdatedInfo.by}
                {lastUpdatedInfo.at
                  ? `, ${new Date(lastUpdatedInfo.at).toLocaleDateString('ru-RU', {
                      day: '2-digit',
                      month: '2-digit',
                      hour: '2-digit',
                      minute: '2-digit',
                    })}`
                  : ''}
                )
              </span>
            )}
          </Space>
          {!isAdminRole && (
            <div style={{ marginTop: 4, color: isDarkMode ? '#8b949e' : '#64748b', fontSize: 13 }}>
              Персональная электронная таблица для ведения оперативных заметок, списков кандидатов и задач. Данные сохраняются автоматически.
            </div>
          )}
        </div>

        {/* Second row: Toolbar with search & actions starting under the title, and reload button at the far right */}
        <div
          style={{
            marginTop: 14,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 12,
          }}
        >
          {/* Left side actions (starts right under 'Рабочие заметки') */}
          <Space wrap size={8}>
            <Input
              placeholder="Поиск по всему листу..."
              prefix={<SearchOutlined />}
              value={searchFilter}
              onChange={(e) => setSearchFilter(e.target.value)}
              allowClear
              style={{ width: 240 }}
              data-tour-notes="search"
            />
            {hasFilter && (
              <Button
                icon={<ReloadOutlined />}
                onClick={handleResetFilters}
              >
                Сбросить поиск ({filteredRows.length} из {activeSheet?.rows?.length || 0})
              </Button>
            )}
            <Button
              type="primary"
              icon={<PlusOutlined />}
              onClick={handleAddRow}
              data-tour-notes="add-row"
            >
              Добавить строку
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={() => setColModalVisible(true)}
              data-tour-notes="add-col"
            >
              Добавить столбец
            </Button>
            <Button
              icon={<EditOutlined />}
              onClick={handleOpenRename}
              data-tour-notes="rename-sheet"
            >
              Переименовать лист
            </Button>
            <Button
              icon={<DownloadOutlined />}
              onClick={handleExportCSV}
              data-tour-notes="export-csv"
            >
              Экспорт CSV
            </Button>
          </Space>

          {/* Right side: Reload button at the far right end of this row */}
          <Space size={8}>
            <Tooltip title="Синхронизировать с сервером и загрузить актуальные данные">
              <Button
                icon={<ReloadOutlined spin={refreshLoading} />}
                loading={refreshLoading}
                onClick={() => fetchNotes(true)}
              >
                Обновить
              </Button>
            </Tooltip>
            {isRecruiter && (
              <Tooltip title="Обучение по работе с разделом Заметки">
                <Button
                  icon={<QuestionCircleOutlined style={{ fontSize: 16 }} />}
                  style={{ width: 32, height: 32, display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}
                  onClick={() => setTourOpen(true)}
                  data-testid="notes-tour-button"
                  data-tour-notes="tour-btn"
                />
              </Tooltip>
            )}
          </Space>
        </div>
      </Card>

      {/* Sheet Tabs */}
      <div
        style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 8 }}
        data-tour-notes="tabs"
      >
        <Tabs
          type="editable-card"
          activeKey={activeSheetId}
          onChange={(key) => {
            setActiveSheetId(key);
            setColumnSearch({});
          }}
          onEdit={(targetKey, action) => {
            if (action === 'add') {
              handleAddSheet();
            } else if (action === 'remove') {
              handleDeleteSheet(targetKey);
            }
          }}
          items={tabItems}
          style={{ flex: 1 }}
        />
      </div>

      {/* Spreadsheet Table */}
      <Card
        data-tour-notes="table"
        style={{
          background: isDarkMode ? '#161b22' : '#ffffff',
          borderRadius: 12,
          overflow: 'hidden',
        }}
        bodyStyle={{ padding: 0 }}
      >
        <RowDragContext.Provider value={dragContextValue}>
          <Table
            components={TABLE_COMPONENTS}
            onRow={(record, index) => ({
              'data-row-id': record.id,
              'data-row-index': index,
            })}
            dataSource={filteredRows}
            columns={tableColumns}
            rowKey="id"
            pagination={{
              current: pagination.current,
              pageSize: pagination.pageSize,
              showSizeChanger: true,
              pageSizeOptions: ['10', '25', '50', '100'],
              showTotal: (total) => `Всего строк: ${total}`,
              onChange: (page, pageSize) => setPagination({ current: page, pageSize }),
            }}
            scroll={{ x: 'max-content', y: 600 }}
            size="middle"
            bordered
          />
        </RowDragContext.Provider>
      </Card>

      {/* Modal: Add Column */}
      <Modal
        title="Добавить новый столбец"
        open={colModalVisible}
        onOk={handleAddColumn}
        onCancel={() => {
          setColModalVisible(false);
          setNewColTitle('');
        }}
        okText="Добавить"
        cancelText="Отмена"
      >
        <div style={{ marginTop: 12 }}>
          <Text strong>Название столбца:</Text>
          <Input
            autoFocus
            style={{ marginTop: 8 }}
            placeholder="Например: Источник резюме, Дата контакта..."
            value={newColTitle}
            onChange={(e) => setNewColTitle(e.target.value)}
            onPressEnter={handleAddColumn}
          />
        </div>
      </Modal>

      {/* Modal: Rename Column */}
      <Modal
        title="Переименовать столбец"
        open={renameColModalVisible}
        onOk={handleSaveRenameCol}
        onCancel={() => {
          setRenameColModalVisible(false);
          setEditingColKey(null);
        }}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <div style={{ marginTop: 12 }}>
          <Text strong>Новое название столбца:</Text>
          <Input
            autoFocus
            style={{ marginTop: 8 }}
            value={renameColTitle}
            onChange={(e) => setRenameColTitle(e.target.value)}
            onPressEnter={handleSaveRenameCol}
          />
        </div>
      </Modal>

      {/* Modal: Rename Sheet */}
      <Modal
        title="Переименовать лист"
        open={renameModalVisible}
        onOk={handleSaveRename}
        onCancel={() => setRenameModalVisible(false)}
        okText="Сохранить"
        cancelText="Отмена"
      >
        <div style={{ marginTop: 12 }}>
          <Text strong>Новое название листа:</Text>
          <Input
            autoFocus
            style={{ marginTop: 8 }}
            value={renameSheetTitle}
            onChange={(e) => setRenameSheetTitle(e.target.value)}
            onPressEnter={handleSaveRename}
          />
        </div>
      </Modal>

      {/* Onboarding Tour - only rendered for recruiters */}
      {isRecruiter && (
        <Tour
          open={tourOpen}
          onClose={handleTourClose}
          onFinish={handleTourClose}
          steps={NOTES_TOUR_STEPS}
          scrollIntoViewOptions={{ behavior: 'smooth', block: 'center' }}
          indicatorsRender={(current, total) => (
            <Text style={{ fontSize: 12, color: '#6b7280' }}>{current + 1} / {total}</Text>
          )}
        />
      )}
    </div>
  );
}

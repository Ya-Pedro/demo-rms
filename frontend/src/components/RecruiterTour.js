
import React, { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Tour, Typography } from 'antd';

const { Text, Paragraph } = Typography;

function step(selector, title, description) {
  return {
    target: () => document.querySelector(`[data-tour="${selector}"]`) ?? null,
    title: <Text strong style={{ fontSize: 14 }}>{title}</Text>,
    description: (
      <Paragraph style={{ margin: 0, fontSize: 13, color: '#4b5563', lineHeight: '1.6' }}>
        {description}
      </Paragraph>
    ),
  };
}

const STEPS = [
  step('create-btn',        '📋 Создание заявки',       'Здесь вы можете создать новую заявку на подбор персонала. Нажмите, чтобы открыть форму и заполнить все необходимые поля.'),
  step('reset-filters-btn', '🔍 Фильтры и сброс',       'Используйте фильтры в заголовках колонок для поиска нужных вакансий. Эта кнопка мгновенно сбросит все активные фильтры и сортировки.'),
  step('export-btn',        '📥 Экспорт в Excel',       'Выгружайте текущий список вакансий в Excel одним кликом. Экспортируются все видимые данные с учётом активных фильтров.'),
  step('report-btn',        '📝 Еженедельный отчёт',    'По этой кнопке вы добавляете отчёт по конкретной вакансии — передано резюме, одобрено, проведены собеседования, сделан оффер.'),
  step('edit-btn',          '✏️ Редактирование',        'Нажмите, чтобы изменить статус вакансии, обновить зарплату, даты или другие детали. Все изменения сохраняются в истории.'),
  step('delete-btn',        '🗑️ Удаление вакансии',    'Нажмите, чтобы удалить вакансию из системы. Будьте внимательны — это действие необратимо.'),
  step('reload-btn',        '🔄 Обновление данных',     'Загружает актуальные данные из базы без перезагрузки страницы.'),
  step('tour-btn',          '🎓 Обучение завершено!',   'Обучение на вкладке Вакансии завершено. Нажмите эту кнопку в любой момент для повторного запуска.'),
];

const RecruiterTour = forwardRef(function RecruiterTour({ user, onComplete }, ref) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    if (user.role !== 'recruiter') return;
    if (user.is_temporary_password !== false) return;
    if (user.is_vacancies_tour_completed !== false) return;

    setOpen(true);
  }, [user]);

  const start = useCallback(() => setOpen(true), []);

  useEffect(() => {
    if (!open) return;
    const block = (e) => {
      if (e.target.closest('[data-tour]')) {
        e.stopPropagation();
        e.preventDefault();
      }
    };
    document.addEventListener('click', block, true);
    return () => document.removeEventListener('click', block, true);
  }, [open]);

  const handleClose = useCallback(() => {
    setOpen(false);
    if (typeof onComplete === 'function') onComplete();
  }, [onComplete]);

  useImperativeHandle(ref, () => ({ start }), [start]);

  return (
    <Tour
      open={open}
      onClose={handleClose}
      onFinish={handleClose}
      steps={STEPS}
      scrollIntoViewOptions={{ behavior: 'smooth', block: 'center' }}
      indicatorsRender={(current, total) => (
        <Text style={{ fontSize: 12, color: '#6b7280' }}>{current + 1} / {total}</Text>
      )}
    />
  );
});

export default RecruiterTour;
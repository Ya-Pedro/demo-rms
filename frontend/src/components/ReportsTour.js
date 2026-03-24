
import React, { useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { Tour, Typography } from 'antd';

const { Text, Paragraph } = Typography;

function step(selector, title, description) {
  return {
    target: () => document.querySelector(`[data-tour-reports="${selector}"]`) ?? null,
    title: <Text strong style={{ fontSize: 14 }}>{title}</Text>,
    description: (
      <Paragraph style={{ margin: 0, fontSize: 13, color: '#4b5563', lineHeight: '1.6' }}>
        {description}
      </Paragraph>
    ),
  };
}

const STEPS = [
  step('filters',    '🔎 Фильтрация отчётов',  'Используйте эти поля для отбора отчётов по году, месяцу, неделе или произвольному диапазону дат. Также можно искать по ID вакансии. После выбора нажмите «Применить».'),
  step('reset-btn',  '🧹 Сброс фильтров',      'Нажмите, чтобы мгновенно очистить все активные фильтры и вернуться к полному списку отчётов.'),
  step('reload-btn', '🔄 Обновление таблицы',  'Кнопка перезагружает таблицу отчётов, загружая самые свежие данные из базы без перезагрузки страницы.'),
  step('table',      '📊 Таблица отчётов',     'Без фильтров по периодам числа в воронке — сумма за всё время. При выборе конкретной недели отображаются данные только за неё.'),
  step('tour-btn',   '🎓 Обучение завершено!', 'Обучение на вкладке Отчёты завершено. Нажмите эту кнопку в любой момент для повторного запуска.'),
];

const ReportsTour = forwardRef(function ReportsTour({ user, onComplete }, ref) {
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (!user) return;
    if (user.role !== 'recruiter') return;
    if (user.is_temporary_password !== false) return;
    if (user.is_reports_tour_completed !== false) return;

    setOpen(true);
  }, [user]);

  const start = useCallback(() => setOpen(true), []);

  useEffect(() => {
    if (!open) return;
    const block = (e) => {
      if (e.target.closest('[data-tour-reports]')) {
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

export default ReportsTour;
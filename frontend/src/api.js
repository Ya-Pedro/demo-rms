

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL || '';

import { tokenStorage } from './tokenStorage';

export const getAuthToken = () => {
  return tokenStorage.getAccess();
};

export const getApiUrl = () => {
  return BACKEND_URL ? `${BACKEND_URL}/api` : '/api';
};

export const exportVacancies = async (params = {}) => {
  const token = getAuthToken();
  

  const queryParams = new URLSearchParams();
  if (params.period) queryParams.append('period', params.period);
  if (params.start_date) queryParams.append('start_date', params.start_date);
  if (params.end_date) queryParams.append('end_date', params.end_date);
  if (params.status_id) queryParams.append('status_id', params.status_id);
  if (params.project_id) queryParams.append('project_id', params.project_id);
  if (params.recruiter_id) queryParams.append('recruiter_id', params.recruiter_id);
  if (params.it_role_id) queryParams.append('it_role_id', params.it_role_id);
  if (params.level_id) queryParams.append('level_id', params.level_id);
  
  const queryString = queryParams.toString();
  const base = BACKEND_URL ? `${BACKEND_URL}/api` : '/api';
  const url = `${base}/export/vacancies${queryString ? '?' + queryString : ''}`;
  
  try {
    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status} ${response.statusText}`);
    }
    
    const blob = await response.blob();
    downloadBlob(blob, response);
    return true;
  } catch (error) {
    console.error('Export error:', error);
    throw error;
  }
};

export const exportVacanciesSmart = async (params = {}) => {
  const token = getAuthToken();
  const url = `${BACKEND_URL}/api/export/vacancies/smart`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        period: params.period || 'all_time',
        start_date: params.start_date || null,
        end_date: params.end_date || null,
        apply_filters: params.apply_filters || false,
        filters: params.filters || null,
        sort_field: params.sort_field || null,
        sort_order: params.sort_order || 'desc',
        search: params.search || null,
      }),
    });
    
    if (!response.ok) {
      throw new Error(`Export failed: ${response.status} ${response.statusText}`);
    }
    
    const blob = await response.blob();
    downloadBlob(blob, response);
    return true;
  } catch (error) {
    console.error('Smart export error:', error);
    throw error;
  }
};

function downloadBlob(blob, response) {
  const downloadUrl = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = downloadUrl;
  

  const contentDisposition = response.headers.get('Content-Disposition');
  let filename = 'vacancies_export.xlsx';
  if (contentDisposition) {
    const match = contentDisposition.match(/filename=(.+)/);
    if (match && match[1]) {
      filename = match[1].replace(/"/g, '');
    }
  }
  
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  
  // Cleanup
  document.body.removeChild(link);
  window.URL.revokeObjectURL(downloadUrl);
}

export default {
  getAuthToken,
  getApiUrl,
  exportVacancies,
  exportVacanciesSmart,
};

/**
 * Помечает онбординг-тур как завершённый на бэкенде.
 * @param {'vacancies'|'reports'} tour
 * @returns {Promise<object>} обновлённый объект пользователя
 */
export async function completeTour(tour) {
  const apiClient = (await import('./apiClient')).default;
  const response = await apiClient.post('/users/complete-tour', { tour });
  return response.data;
}
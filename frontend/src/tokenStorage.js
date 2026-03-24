

const KEYS = {
  ACCESS:  'rms_token',
  REFRESH: 'rms_refresh_token',
  USER:    'rms_user',
};

const storage = sessionStorage;

export const tokenStorage = {

  getAccess:    ()      => storage.getItem(KEYS.ACCESS),
  setAccess:    (token) => storage.setItem(KEYS.ACCESS, token),
  removeAccess: ()      => storage.removeItem(KEYS.ACCESS),

  getRefresh:    ()      => storage.getItem(KEYS.REFRESH),
  setRefresh:    (token) => storage.setItem(KEYS.REFRESH, token),
  removeRefresh: ()      => storage.removeItem(KEYS.REFRESH),

  getUser:    ()     => { try { return JSON.parse(storage.getItem(KEYS.USER)); } catch { return null; } },
  setUser:    (user) => storage.setItem(KEYS.USER, JSON.stringify(user)),
  removeUser: ()     => storage.removeItem(KEYS.USER),

  clear: () => {
    storage.removeItem(KEYS.ACCESS);
    storage.removeItem(KEYS.REFRESH);
    storage.removeItem(KEYS.USER);
  },
};
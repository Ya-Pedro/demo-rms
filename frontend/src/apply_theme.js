const fs = require('fs');
const path = require('path');

const appJsPath = path.join(__dirname, 'App.js');
let appJs = fs.readFileSync(appJsPath, 'utf8');

const themeConfigString = `const themeConfig = {
  token: {
    colorPrimary: '#6366f1',
    colorInfo: '#3b82f6',
    colorSuccess: '#10b981',
    colorWarning: '#f59e0b',
    colorError: '#ef4444',
    colorTextBase: '#1e293b',
    colorBgBase: '#ffffff',
    colorBgLayout: '#f4f7fe',
    colorBorder: '#e2e8f0',
    fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
    borderRadius: 12,
    wireframe: false,
    boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05)',
  },
  components: {
    Layout: {
      siderBg: '#ffffff',
      headerBg: 'rgba(255, 255, 255, 0.8)',
    },
    Menu: {
      itemBg: 'transparent',
      itemSelectedBg: '#e0e7ff',
      itemSelectedColor: '#4f46e5',
      itemBorderRadius: 8,
      itemMarginInline: 12,
    },
    Table: {
      headerBg: '#f8fafc',
      headerColor: '#64748b',
      rowHoverBg: '#f1f5f9',
      cellPaddingBlock: 16,
      borderColor: '#f1f5f9',
    },
    Card: {
      borderRadius: 16,
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05)',
    },
    Button: {
      borderRadius: 8,
      controlHeight: 40,
      fontWeight: 500,
    },
    Input: {
      borderRadius: 8,
      controlHeight: 40,
      hoverBorderColor: '#6366f1',
      activeBorderColor: '#6366f1',
    },
    Select: {
      borderRadius: 8,
      controlHeight: 40,
    }
  },
};`;

appJs = appJs.replace(/const themeConfig = \{[\s\S]*?\n\};\n/, themeConfigString + '\n');
fs.writeFileSync(appJsPath, appJs);
console.log('App.js theme updated');

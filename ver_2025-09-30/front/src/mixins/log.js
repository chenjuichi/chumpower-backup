// 匯入 snackbar（視你目前的設計方式調整 import）
import { snackbar, snackbar_info, snackbar_color } from './crud.js';

// timestamp 格式
const getTimestamp = () => {
  return new Date().toISOString();
};

// console log
const logToConsole = (...args) => {
  console.log(`[Log ${getTimestamp()}]`, ...args);
};

// snackbar 顯示
const logToSnackbar = (message, color = 'info') => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};


// log 統一介面
const log = (message, options = {}) => {
  const { console = true, snackbar = false, color = 'info' } = options;

  if (console) {
    logToConsole(message);
  }

  if (snackbar) {
    logToSnackbar(message, color);
  }
};

export { log };
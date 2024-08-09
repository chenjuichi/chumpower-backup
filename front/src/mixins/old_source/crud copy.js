import axios from 'axios';
import { ref } from 'vue';

// 定義用於儲存部門資料及錯誤處理的變數
const departments = ref([]);

const snackbar = ref(false);
const snackbar_color = ref('red accent-2');
const snackbar_info = ref('');
const snackbar_icon_color = ref('#adadad');
const snackbar_timeout = ref(2000);

// 定義一個高階函式 apiOperation，用來處理不同的 API 操作
const apiOperation = (operation, path, options = {}) => {
  return () => {
    console.log(`${operation.toUpperCase()} ${path}...`);

    // 發送 Axios 請求，根據操作類型執行不同的方法（get 或 post）
    const request = axios[operation](path, options);

    return request
      .then((res) => {
        // 如果是 get 操作，更新部門資料
        if (operation === 'get') {
          departments.value = [...res.data.departments];
        }
        // 在這裡可以處理其他操作的回傳值
        //return res.data;
      })
      .catch((error) => {
        // 處理錯誤情況，並顯示 Snackbar 提示
        console.error(error);
        snackbar_info.value = '錯誤! API 連線問題...';
        snackbar.value = true;
        throw error; // 把錯誤繼續傳遞
      });
  };
};

// 導出具體的 API 操作函式
export const listDepartments = apiOperation('get', '/listDepartments');
export const addDepartment = apiOperation('post', '/addDepartment', { data: { /* 在這裡放入 post 方法需要的資料 */ } });
// 你可以在這裡定義更多的 API 操作

// 導出部門資料及 Snackbar 的相關變數，以便在 Vue 組件中使用
export { departments, snackbar_info, snackbar };

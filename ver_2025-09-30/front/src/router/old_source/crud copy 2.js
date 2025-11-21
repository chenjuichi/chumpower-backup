import axios from 'axios';
import { ref, reactive, watch } from 'vue';

// for listDepartments
export const departments = ref([]);

// for listUsers
export const loginEmpIDInput = ref(null);
export const temp_desserts = ref([]);
export const loginUser = reactive({
  loginEmpID: '',
  loginName: '',
  loginPassword: ''
});
const foundDessert = ref(null);
const list_table_is_ok = ref(false);

export const snackbar = ref(false);
//const snackbar_color = ref('red accent-2');
export const snackbar_info = ref('');
//const snackbar_icon_color = ref('#adadad');
//const snackbar_timeout = ref(2000);

// 定義 apiOperation，用來處理不同的 API 操作
export const apiOperation = (operation, path, options = {}) => {
  return () => {
    console.log(`${operation.toUpperCase()} ${path}...`);

    list_table_is_ok.value = false;

    // 發送 Axios 請求，根據操作類型執行不同的方法（get 或 post）
    const request = axios[operation](path, options);

    return request
      .then((res) => {
        // 如果是 get 操作，更新部門資料
        if (operation === 'get') {
          if (path === '/listDepartments') {
            departments.value = [...res.data.departments];
          }

          if (path === '/listUsers') {
            temp_desserts.value = res.data.users;
          }

          list_table_is_ok.value = true;
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

// 定義 watch
export const setupListUsersWatcher = () => {
  watch(list_table_is_ok, (val) => {
    if (val) {
      temp_desserts.value.sort((a, b) => a.emp_id - b.emp_id);  // 升冪排序
      list_table_is_ok.value = false;
    }
  });
};

// 定義 listUsers 函數
export const listUsers = apiOperation('get', '/listUsers');
/*
export const listUsers = () => {
list_table_is_ok.value = false;
const path = '/listUsers';
axios.get(path)
    .then((res) => {
    temp_desserts.value = res.data.users;
    console.log("GET ok, total records:", res.data.users.length);
    list_table_is_ok.value = true;
    })
    .catch((error) => {
    console.error(error);
    snackbar_info.value = '錯誤! API連線問題...';
    snackbar.value = true;
    });
};
*/
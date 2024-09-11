import axios from 'axios';
import { ref, reactive, watch } from 'vue';

//import { snackbar, snackbar_info, snackbar_color } from './snackbarStore';

// for listMaterials
export const materials = ref([]);

// for listDepartments
export const departments = ref([]);

// for listUsers
export const loginEmpIDInput = ref(null);
export const temp_desserts = ref([]);
export const desserts = ref([]);
export const loginUser = reactive({
  loginEmpID: '',
  loginName: '',
  loginPassword: ''
});

const foundDessert = ref(null);
const list_table_is_ok = ref(false);

export const snackbar = ref(false);
export const snackbar_info = ref('');
export const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

// 定義 apiOperation，用來處理不同的 API 操作
export const apiOperation = (operation, path, payload) => {
  return (payload) => {
    console.log(`${operation.toUpperCase()} ${path} with payload`, payload);

    list_table_is_ok.value = false;

    // GET   ：參數通常作為查詢字並串附加到 URL 之後。例如，axios.get('/api/path', { params: { key: 'value' } }) ,
    // 會生成一個請求 URL，如 /api/path?key=value。但 payload 若是{}, axios.get('/api/path', options)生成的請求 URL,
    // 將是：/api/path,  沒有附加任何查詢參數，因為 params 是一個空物件
    //POST ：參數通常作為請求體的一部分發送。例如，axios.post('/api/path', { key: 'value' }) ,
    //      會將 { key: 'value' } 作為請求發送。
    const options = {
      ...(operation === 'get' ? { params: payload } : payload)
    };

    const request = axios[operation](path, options);  // Axios 請求，根據操作類型執行不同的方法（get 或 post）

    return request
      .then((res) => {
        if (operation === 'get') {    // get 操作
          if (path == '/listDepartments') {
            //departments.value = [...res.data.departments];
            // 檢查 res.data 是否包含 'departments' 或 'data'
            if (res.data.departments) {
              departments.value = [...res.data.departments];
            //} else if (res.data.data) {
            } else {
              departments.value = [...res.data.data];
            }
          }

          if (path == '/listMaterials') {
            materials.value = [...res.data.materials];
          }

          if (path == '/listUsers') {
            temp_desserts.value = res.data.users;

            // 檢查每個對象的 dep_name，如果是 null、"NULL" 或 "Null"，則替換為空字符串
            temp_desserts.value = temp_desserts.value.map(user => {
              if (user.dep_name == null || user.dep_name.toLowerCase() === "null") {
                user.dep_name = ' '; // 替換為空字符串
              }
              return user;
            });

            desserts.value = [...temp_desserts.value];
            //console.log("/listUsers, desserts:", desserts.value)
            list_table_is_ok.value = true;
          }

          if (path == '/readAllExcelFiles') {
            console.log("get, path is", path)
            return res.data;
          }

          //list_table_is_ok.value = true;
        } else {    // post 操作
          console.log("post, path:", path)
          if (path == '/register' || path == '/updateUser' || path == '/removeUser' || path == '/updateSetting') {
            console.log("post, path is", path)
            return res.data.status;
          }

          if (path == '/login') {
            console.log("post, path is", path)
            return res.data;
          }
        }
        // 在這裡可以處理其他操作的回傳值
        //return res.data;
      })
      .catch((error) => {
        // 處理錯誤情況，並顯示 Snackbar 提示
        console.error(error);
        showSnackbar('錯誤! API 連線問題...', 'red accent-2');
        throw error; // 把錯誤繼續傳遞
      });
  };
};

// 定義 watch
export const setupListUsersWatcher = () => {
  watch(list_table_is_ok, (val) => {
    if (val) {
      temp_desserts.value.sort((a, b) => a.emp_id - b.emp_id);  // 升冪排序
      desserts.value = Object.assign([], temp_desserts.value);
      list_table_is_ok.value = false;
    }
  });
};

export const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color);

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};


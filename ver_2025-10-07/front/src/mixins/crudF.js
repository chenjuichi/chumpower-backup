import axios from 'axios';
import { ref } from 'vue';

// 定義 apiOperation，用來處理不同的 API 操作
export const apiOperationF = (operation, path) => {
  return (payload) => {
    if (payload !== undefined) {
      console.log(`${operation.toUpperCase()} ${path} with payload`, payload);
    } else {
      console.log(`${operation.toUpperCase()} ${path}`);
    }

    // 構建 Axios 的配置
    const options = {
      timeout: payload instanceof FormData ? 30000 : 10000, // 檔案上傳 30秒，其他 10秒
      headers: {
        //'Content-Type': 'multipart/form-data', // 設置檔案上傳標頭
      }
    };

    let request;

    if (operation === 'get') {
      request = axios.get(path, options);
    } else {
      // 如果是上傳檔案，需設定 multipart/form-data
      if (payload instanceof FormData) {
        options.headers['Content-Type'] = 'multipart/form-data';
      }
      //console.log("path:", path)
      request = axios.post(path, payload, options);
    }

    return request
    .then((res) => {
      return res.data;
    })
    .catch((error) => {
      // 處理錯誤情況，並顯示 Snackbar 提示
      console.error(error);
      showSnackbar('API 錯誤!', 'red accent-2');
      throw error; // 把錯誤繼續傳遞
    });
  };
};
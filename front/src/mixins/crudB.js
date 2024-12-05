import axios from 'axios';
import { ref } from 'vue';

// 定義 apiOperation，用來處理不同的 API 操作
export const apiOperationB = (operation, path) => {
  return (payload) => {
    if (payload != undefined)
      console.log(`${operation.toUpperCase()} ${path} with payload`, payload);
    else
      console.log(`${operation.toUpperCase()} ${path}`);

    // 構建 Axios 的配置
    const options = {
      ...(path === '/downloadFile' ? { responseType: 'blob' } : {}),  // 新增 responseType
    };

    // 根據請求類型處理
    if (operation === 'post') {
      // POST 請求的參數放在 `data`
      return axios.post(path, payload, options).then((res) => handleResponse(res, path));
    }
  };
};

// 處理回應
const handleResponse = (res, path) => {
  if (path === '/downloadFile') {
    if (res.data instanceof Blob) {
      console.log("Blob received from", path);
      return res; // 返回完整回應
    } else {
      console.warn("Response data is not a Blob:", res.data);
    }
  }

  if (path === '/saveFile') {
    if (res.data instanceof Blob) {
      console.log("Blob received from", path);

      fileName = 'NEW_FILE_NAME.pdf';
      console.log('儲存的檔案名稱:', fileName);

      const url = window.URL.createObjectURL(res.data);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      return true;  // 下載完成後返回成功狀態
    }
    return res.data; // 對於非 Blob 類型的操作，直接返回回應資料
  }

  return res.data; // 對於非特殊路徑，返回回應的資料部分
}



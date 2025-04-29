import axios from 'axios';
import { ref } from 'vue';

// 所有需要 blob 處理的 API 路徑（可擴充）
//const blobPaths = ['/downloadXlsxFile', '/saveFile', '/stampFile', '/downloadFile'];
const blobPaths = ['/downloadXlsxFile', '/downloadFile'];

// 定義 apiOperation，用來處理不同的 API 操作
export const apiOperationB = (operation, path) => {
  return (payload) => {
    if (payload !== undefined) {
      console.log(`${operation.toUpperCase()} ${path} with payload`, payload);
    } else {
      console.log(`${operation.toUpperCase()} ${path}`);
    }

    const isBlobPath = blobPaths.includes(path);

    // 構建 Axios 的配置
    const options = {
      responseType: isBlobPath ? 'blob' : 'json', // 自動判斷是否下載檔案
      headers: {
        'Accept': isBlobPath ? 'application/pdf' : 'application/json'
        /*
        'Accept': path.includes('download')
          ? 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
          : 'application/json'
        */
      }
    };

    // 根據請求類型處理
    if (operation === 'post') {
      return axios.post(path, payload, options).then((res) => handleResponse(res, path));
    }
  };
};

// 處理回應
const handleResponse = (res, path) => {
  if (path === '/downloadFile' || path === '/downloadXlsxFile') {
    if (res.data instanceof Blob) {
      console.log("Blob received from", path);
      return res; // 返回完整回應
    } else {
      console.warn("Response data is not a Blob:", res.data);
    }
  }
  /*
  if (path === '/saveFile') {
    if (res.data instanceof Blob) {
      console.log("Blob received from", path);

      const fileName = 'NEW_FILE_NAME.pdf';
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

  if (path === '/stampFile') {
    if (res.data instanceof Blob) {
      console.log("Blob received from", path);

      //const fileName = response.headers['x-file-name'] || 'STAMPED_FILE.pdf';
      const fileName = res.headers['x-file-name'] || 'STAMPED_FILE.pdf';
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
    //} else {
    //  console.error('Unexpected response data:', response.data);
    }
    return res.data; // 對於非 Blob 類型的操作，直接返回回應資料
  }
  */
  return res.data; // 對於非特殊路徑，返回回應的資料部分
}

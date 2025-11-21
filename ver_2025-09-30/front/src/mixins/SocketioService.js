import { io } from 'socket.io-client';
import { ref } from 'vue';
/*
import { log } from './log.js';
*/

/*
// 非同步讀取配置文件的函數
const loadServerConfig = async () => {
  const fixIp = '192.168.68.70';
  try {
    //const response = await fetch('/config.json');
    const response = await fetch(`/config.json?v=${Date.now()}`); // 在文件名後加入時間戳（需後端配合更新文件）
    if (!response.ok) throw new Error('Failed to load config');
    const config = await response.json();
    return config.serverIp || fixIp; // 默認值 fallback
  } catch (error) {
    console.error('Error loading server IP config:', error);
    return fixIp; // 確保即使失敗也有默認值
  }
};
*/


const getLocalIP = async () => {
  try {
    //const response = await fetch('/config.json');
    const response = await fetch(`/config.json?v=${Date.now()}`); //強制讓瀏覽器當成新請求、跳過快取
    const config = await response.json();
    const ip = config.serverIp || '192.168.68.56';
    console.log('讀取 config.json後，IP為', ip);
    /*
    // 傳給後端記錄 log
    await fetch('http://localhost:6500/log-ip', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ ip })
    });
    */
    return ip;
  } catch (e) {
    console.error('無法讀取 config.json，使用預設 IP', e);
    return '192.168.68.56';
  }
};

// 取得本機 IP 並初始化

export const useSocketio = (localIp, userId, clientAppName) => {
  console.log("hello, socket.....")

  const socket = ref(null);

  const setupSocketConnection = async () => {
    //return new Promise((resolve, reject) => {
    try {
      // 取得本機 IP 並初始化
      //let serverIp = '192.168.68.55';
      //const serverIp = await loadServerConfig(); // 動態讀取 IP
      let serverIp = await getLocalIP();
      console.log(`伺服器本機的IP為 ${serverIp}\n`);

      localIp = serverIp;

      console.log(`Attempting to connect to http://${localIp}:6500 with user_id ${userId}`);
      socket.value = io(`http://${localIp}:6500`, {
        transports: ['websocket'], // 強制使用 websocket 傳輸
        timeout: 10000, // 設定超時時間為 10 秒
        query: {
          userId: userId,
          existingSockId: '00.00.00.00', // 傳遞 existingSockId
          clientAPP: clientAppName
        }
      });

      return new Promise((resolve, reject) => {
        socket.value.on('connect', () => {
          console.log('Socket connected:', socket.value.id);
          resolve(socket.value);
        });

        socket.value.on('connect_error', (err) => {
          console.error('Socket connection error:', err);
          reject(err);
        });
      });
    } catch (error) {
      return Promise.reject(error);
    }
  };

  const ensureConnected = () => {
    return new Promise((resolve, reject) => {
      if (socket.value && socket.value.connected) {
        resolve(socket.value);
      } else {
        socket.value.once('connect', () => {
          resolve(socket.value);
        });
        socket.value.once('connect_error', (err) => {
          reject(err);
        });
      }
    });
  };

  return {
    socket,
    setupSocketConnection,
    ensureConnected
  };
};

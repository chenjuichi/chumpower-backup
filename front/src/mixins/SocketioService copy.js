import { io } from 'socket.io-client';
import { ref } from 'vue';

export const useSocketio = (localIp, userId, clientAppName) => {
  console.log("hello, socket.....")
  const socket = ref(null);

  const setupSocketConnection = () => {
    return new Promise((resolve, reject) => {

      let serverIp = '192.168.32.241';
      localIp = serverIp;

      console.log(`Attempting to connect to http://${localIp}:6500 with user_id ${userId}`);
      socket.value = io(`http://${localIp}:6500`, {
        transports: ['websocket'], // 強制使用 websocket 傳輸
        query: {
          userId: userId,
          existingSockId: '00.00.00.00', // 傳遞 existingSockId
          clientAPP: clientAppName
        }
      });

      socket.value.on('connect', () => {
        console.log('Socket connected:', socket.value.id);
        resolve(socket.value);
      });

      socket.value.on('connect_error', (err) => {
        console.error('Socket connection error:', err);
        reject(err);
      });
    });
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

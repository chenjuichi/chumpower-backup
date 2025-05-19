require('dotenv').config();

const readline = require('readline');
const express = require('express');
const cors = require('cors');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);
const os = require('os');

//const fs = require('fs');

// 開啟 CORS，允許所有來源
//app.use(cors());

// 解析 JSON POST 資料
app.use(express.json());

// 提供前端靜態頁面或資料，如 index.html, config.json
app.use(express.static('public'));    //for vue3 application, npm run serve
//app.use(express.static('dist'));      //for vue3 application, npm run build

//console.log("Step 1...");

const path = require('path');
const logDir = path.resolve(__dirname); // 如果 service.log 是放在當前目錄
const logFilePath = path.join(logDir, 'service.log');
console.log('\n📝 service.log 目前位於：', logFilePath);
const fs = require('fs');

const MAX_LOG_SIZE = 10 * 1024 * 1024; // 10MB

//console.log("Step 2...");

const net = require('net')
const waitingClients = new Set();

let client = new net.Socket();

const rooms = {};

let csharpReady = false;    // 用來標記是否成功連線 C# Server
let on_line = false;        // false: off line 模擬模式, true: on line 上線模式
let lastErrorMessage = '';

//console.log("Step 3...");

// 檢測本機 IP 地址
/*
const getLocalIP = async () => {
  try {
    const interfaces = os.networkInterfaces();
    for (const interfaceName in interfaces) {
      for (const iface of interfaces[interfaceName]) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;
        }
      }
    }
  } catch (error) {
    console.error('Error retrieving local IP:', error);
  }
  return 'localhost'; // 無法取得 IP 時返回 localhost
};
*/

/*
const getLocalIP = async () => {
  try {
    const interfaces = os.networkInterfaces();
    const wifiInterfaces = interfaces['Wi-Fi']; // 專門篩選 Wi-Fi 介面

    if (wifiInterfaces) {
      for (const iface of wifiInterfaces) {
        if (iface.family === 'IPv4' && !iface.internal) {
          return iface.address;                 // 返回 Wi-Fi 的 IPv4 地址
        }
      }
    }
  } catch (error) {
    console.error('Error retrieving local IP from Wi-Fi:', error);
  }
  return 'localhost';                         // 若無法取得 Wi-Fi 的 IP，返回 localhost
};
*/

// 取得本機 IP 並初始化
//let localIP = 'localhost';
//(async () => {
//  localIP = await getLocalIP();
//  console.log(`伺服器本機的IP為 ${localIP}\n`);
//})();

// HTTP API 和 WebSocket 共用同一個 Port 6500, 伺服器同時處理 HTTP 請求和 WebSocket 連線(協定不同)
const PORT = Number(process.env.PORT) || 6500;
// 針對 與C# TCP Server連線, 所使用的 Port 6400
const CSHARP_PORT = Number(process.env.CSHARP_PORT) || 6400;
// 針對 與C# TCP Server連線, 所使用的 IP
const CSHARP_SERVER_IP = process.env.CSHARP_SERVER_IP;

const SERVER_IP = process.env.SERVER_IP;
console.log(`\nSERVER_IP: ${SERVER_IP}`);
let RUN_MODE = false;
RUN_MODE = ['true', '1', 'yes'].includes(
  (process.env.RUN_MODE || '').toLowerCase()
);
console.log(`\nRUN_MODE: ${RUN_MODE}`)
//const online_mode= process.env.online_mode;
on_line = RUN_MODE;
let localIP = SERVER_IP;

const allowedOrigin = [`http://${localIP}:8080`, `http://${localIP}:8060`]; // 使用動態 localIP
app.use(cors({
  origin: allowedOrigin,
  credentials: true
}));

// 設定終端輸入介面
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
});

// 啟用鍵盤事件偵聽
readline.emitKeypressEvents(process.stdin);
if (process.stdin.isTTY) {
  process.stdin.setRawMode(true); // 設定為原始模式 (raw mode)，以便偵測單鍵輸入事件
}

//console.log("Step 4...");

/*
// 監聽鍵盤按鍵事件
process.stdin.on('keypress', (str, key) => {
  if (key.ctrl && key.name === 's') {
    console.log('檢測到 Ctrl+S，結束程式...');
    process.exit(); // 結束程式
  }
});
*/
// 監聽 Ctrl+C (SIGINT) 或應用程式結束
const shutdown = () => {
  console.log('Server shutting down...');

  // 通知所有 WebSocket 客戶端
  io.emit('server_shutdown', '伺服器即將關閉');   //廣播socket.io的所有client
  client.write('server_shutdown');              //發送至C#伺服器的訊息

  // 給點時間讓訊息發送後再關閉
  setTimeout(() => {
  //    io.close(() => console.log('Socket.io server closed.'));
  //    client.close(() => console.log('TCP server closed.'));
      process.exit(0);
  }, 1000);
};

// 監聽 `Ctrl+C` 事件
process.on('SIGINT', shutdown);

// 監聽 `process.exit`
process.on('exit', shutdown);

// 監聽 `Ctrl+C` 事件
process.on('SIGINT', shutdown);

// 監聽 `process.exit`
process.on('exit', shutdown);

//console.log("Step 5...");

// 包裝 rl.question 成為 Promise
function askQuestion(query) {
  return new Promise((resolve) => {
    rl.question(query, resolve);
  });
}

// 包裝 rl.question 成為 Promise，確認輸入為空字串 (即僅按下 Enter 鍵)
function askQuestionForReturn(query) {
  return new Promise((resolve) => {
    rl.question(query, (input) => {
      if (input.trim() === '') {  // 確認輸入為空
        resolve();
      } else {
        console.log("請僅按 Enter 鍵以繼續");
        resolve(askQuestion(query)); // 再次呼叫 askQuestion 直到僅按下 Enter
      }
    });
  });
}

function checkLogFileSize() {
  const logPath = 'service.log';
  if (fs.existsSync(logPath)) {
    const stats = fs.statSync(logPath);
    if (stats.size > MAX_LOG_SIZE) {
      const backupName = `service_${Date.now()}.log`;
      fs.renameSync(logPath, backupName); // 備份舊 log
      fs.writeFileSync(logPath, '');      // 建立新空檔案
      console.log(`📁 日誌檔案過大，已備份為 ${backupName}`);
    }
  }
}

// 確保 log 檔案存在，或建立空檔案（初始化）
function ensureLogFileExists() {
  if (!fs.existsSync(logFilePath)) {
    fs.writeFileSync(logFilePath, ''); // 建立空檔案
  }
}


// ==============================================================================


// 呼叫這個函式一次即可
ensureLogFileExists();

//let connectedPeers = [];
let connectedPeers = new Set();   //使用Set以確保socket.id唯一性

let resetRequested = false;       // 重置狀態

//console.log("Step 6...");

// Socket.IO 事件處理
io.on('connection', (socket) => {
  const clientAPP = socket.handshake.query.clientAPP;
  if (clientAPP) {
    console.log(`與 ${clientAPP} 已連線`);
  }
  console.log(`Client connected, socket id: ${socket.id}`);
  //connectedPeers.push(socket.id);
  connectedPeers.add(socket.id);

  //client.write('connection');     //發送至C#伺服器的訊息(B)
  socket.emit('connection');      //發送至所有client的訊息

  // 如果 C# server 沒連上，馬上通知 client
  if (!csharpReady) {
    waitingClients.add(socket);
    socket.emit('kuka_server_not_ready', {
      message: 'kuka端伺服器尚未準備好，請稍後再試。'
    });
  }

  socket.on('error', (err) => {
    console.error('WebSocket 發生錯誤:', err.message);
  });

  socket.on('station1_loading', async () => {
    console.log("收到 station1_loading 訊息...");

    //if (on_line) {
      client.write('station1_loading');
    //}
  });

  socket.on('station2_loading', async () => {
    console.log("收到 station2_loading 訊息...");

    //if (on_line) {
      client.write('station2_loading');
    //}
  });

  socket.on('station3_loading', async () => {
    console.log("收到 station3_loading 訊息...");

    //if (on_line) {
      client.write('station3_loading');
    //}
  });

  // station1_call 事件處理
  socket.on('station1_call', async (data) => {
    if (!socket.connected) {
      console.log('Socket disconnected, cannot proceed with station1_call');
      return;
    }
    //const { items, orderNums } = data;
    //console.log("收到 station1_call 訊息，內容：", data);
    console.log("收到 station1_call 訊息...");

    if (on_line) {
      client.write('station1_call');    //發送至C#伺服器的訊息(B)
      console.log("AGV 準備從裝卸站啟動...");
    } else {

      // 處理選擇的項目
      //if (items.length === 0) {
      //  console.log("沒有選擇任何 items");
      //} else {
      //  console.log(`處理 ${items.length} 個 selectedItems...`);
      //}

      // 處理選擇的訂單號碼
      //if (orderNums.length === 0) {
      //  console.log("沒有選擇任何 orderNums");
      //} else {
      //  console.log(`處理 ${orderNums.length} 個 selectedOrderNums...`);
      //}

      // 倒數中：3 秒
      let countdown = 3;
      await new Promise(resolve => {
        const countdownInterval = setInterval(() => {
          console.log(`倒數中: ${countdown} 秒`);
          countdown--;
          if (countdown < 0) {
            clearInterval(countdownInterval);
            resolve();
          }
        }, 1000);
      });

      //if (!socket.connected) return; // 確保連線有效
      console.log('AGV 已在備料區裝卸站...');
      socket.emit('station1_agv_ready');

      // 等待使用者按下 Enter 鍵以啟動 AGV
      //await askQuestionForReturn('請按下 Enter 鍵以啟動 AGV: ');
      //if (resetRequested) return; // 檢查是否要求重置
      console.log('\x1b[33m%s\x1b[0m', 'AGV 任務開始，press Start按鍵');
      socket.emit('station1_agv_start');

      // 倒數中：5 秒 (AGV 行進中)
      let agvCountdown = 5;
      await new Promise(resolve => {
        const agvInterval = setInterval(() => {
          console.log(`AGV行進中: ${agvCountdown} 秒`);
          agvCountdown--;
          if (agvCountdown < 0) {
            clearInterval(agvInterval);
            resolve();
          }
        }, 1000);
      });

      //if (resetRequested) return; // 檢查是否要求重置
      console.log('開始 AGV 運行(備料區)');
      socket.emit('station1_agv_begin');

      // 等待使用者按下 Enter 鍵以結束 AGV 任務
      //await askQuestion('請按任何鍵以結束 AGV 任務: ');
      //if (resetRequested) return; // 檢查是否要求重置
      console.log('\x1b[34m%s\x1b[0m', 'AGV 運行結束，已到達組裝區');
      //socket.emit('station2_agv_end', items,);
      socket.emit('station2_agv_end');
    }
  });

  // station2_call 事件處理
  socket.on('station2_call', async () => {
    if (!socket.connected) {
      console.log('Socket disconnected, cannot proceed with station2_call');
      return;
    }
    console.log('收到 station2_call 訊息');

    if (on_line) {
      client.write('station2_call');    //發送至C#伺服器的訊息(B)
      console.log("AGV 準備從裝卸站啟動...");
    } else {

      // 倒數中：3 秒
      let countdown = 3;
      await new Promise(resolve => {
        const countdownInterval = setInterval(() => {
          console.log(`倒數中: ${countdown} 秒`);
          countdown--;
          if (countdown < 0) {
            clearInterval(countdownInterval);
            resolve();
          }
        }, 1000);
      });

      if (!socket.connected) return; // 確保連線有效
      console.log('AGV 已在組裝區裝卸站...');
      socket.emit('station2_agv_ready');

      // 等待使用者按下 Enter 鍵以啟動 AGV
      //await askQuestionForReturn('請按下 Enter 鍵以啟動 AGV: ');
      //if (resetRequested) return; // 檢查是否要求重置
      console.log('\x1b[33m%s\x1b[0m', 'AGV 任務開始，press Start按鍵');
      socket.emit('station2_agv_start');

      // 倒數中：5 秒 (AGV 行進中)
      let agvCountdown = 5;
      await new Promise(resolve => {
        const agvInterval = setInterval(() => {
          console.log(`AGV運行中: ${agvCountdown} 秒`);
          agvCountdown--;
          if (agvCountdown < 0) {
            clearInterval(agvInterval);
            resolve();
          }
        }, 1000);
      });

      //if (resetRequested) return; // 檢查是否要求重置
      console.log('開始 AGV 運行(在組裝區)');
      socket.emit('station2_agv_begin');

      // 等待使用者按下 Enter 鍵以結束 AGV 任務
      //await askQuestion('請按任何鍵以結束 AGV 任務: ');
      // if (resetRequested) return; // 檢查是否要求重置
      console.log('\x1b[34m%s\x1b[0m', 'AGV 運行結束，已到達成品區');
      socket.emit('station3_agv_end');
    }
  });

  // agv_reset 事件處理
  socket.on('agv_reset', () => {
    console.log('收到 agv_reset 訊息，重置所有動作...');
    resetRequested = true;          // 設置重置請求為 true
    //socket.emit('agv_ack');       // 向客戶端確認收到重置請求
    client.write('agv_reset');      //發送至C#伺服器的訊息(B)
  });

  //begin for webRTC
  // 用戶斷線處理
  //socket.on('disconnect', () => {
  //  console.log(`Client disconnected: ${socket.id}`);
  //  //移除斷開連線的 socket.id
  //  connectedPeers = connectedPeers.filter(peer => peer !== socket.id);
  //});
  socket.on('disconnect', () => {
    console.log('\x1b[34m%s\x1b[0m', `用戶斷線(socket id): ${socket.id}`);

    waitingClients.delete(socket);

    //
    // 從所有房間中移除用戶
    Object.keys(rooms).forEach((roomId) => {
      if (rooms[roomId].has(socket.id)) {
        rooms[roomId].delete(socket.id);
        socket.to(roomId).emit('user-disconnected', socket.id);
      }
    });
    /*
    setTimeout(() => {
      if (!connectedPeers.has(socket.id)) {
        connectedPeers.delete(socket.id);
        console.log(`已清除未重新連線的用戶(socket id): ${socket.id}`);
      }
    }, 10000); // 10 秒內未重新連線則清除
    //
    console.log(`目前在線人數: ${connectedPeers.size}`);
    //io.emit('userDisconnected', socket.id); // 廣播用戶離線

    socket.broadcast.emit('user-disconnected', socket.id);  //for webRTC
    */
  });

  socket.on('join', (roomId) => {
    if (!rooms[roomId]) {
      rooms[roomId] = new Set();
    }

    // 檢查用戶是否已經加入過房間
    if (!rooms[roomId].has(socket.id)) {
      socket.join(roomId);
      rooms[roomId].add(socket.id);
      console.log('\x1b[34m%s\x1b[0m', `用戶 ${socket.id} 加入房間: ${roomId}`);
      console.log('\x1b[34m%s\x1b[0m', `目前房間內用戶: ${Array.from(rooms[roomId])}`);  // 確認房間內是否有人
      socket.to(roomId).emit('user-connected', socket.id);
    }

    //將當前的 socket（用戶連接）加入到指定的房間（roomId）
    //socket.join(roomId);
    //向指定房間（roomId）內的所有用戶（除了當前用戶）發送一個 user-connected 事件
    //socket.to(roomId).emit('user-connected', socket.id);
  });

  socket.on('offer', (id, offer) => {
    //發送一個 offer 的事件，並傳遞兩個參數,
    //socket.id：當前用戶的 socket.id，表示發送 offer 的用戶
    //offer：WebRTC 的 SDP Offer，處理 WebRTC 的 信令（Signaling） , 以用於建立連線
    console.log('\x1b[34m%s\x1b[0m', `收到 offer 來自: ${socket.id}，房間: ${id}`);
    //console.log("Offer SDP:", offer);
    socket.to(id).emit('offer', socket.id, offer);
  });

  socket.on('answer', (id, answer) => {
    console.log('\x1b[34m%s\x1b[0m', `收到 answer 來自: ${socket.id}`);

    socket.to(id).emit('answer', socket.id, answer);
  });

  socket.on('candidate', (id, candidate) => {
    console.log('\x1b[34m%s\x1b[0m', `接收到 ICE 候選人來自: ${socket.id}，房間: ${id}`);

    socket.to(id).emit('candidate', socket.id, candidate);
  });
  //end for webRTC

  // 使用 socket.onAny 監聽所有事件
  socket.onAny(async (eventName) => {
    let webRTC_message = ['candidate', 'answer', 'offer', 'join', 'disconnect', 'error'];

    //if (!socket.connected) {
    //  console.log('Socket disconnected, cannot proceed this socket');
    //  return;
    //}
    console.log(`收到來自網頁端 ${eventName} 訊息`);
    /*
    const match = eventName.match(/^test(\d+)_call$/); // 檢查是否符合 testX_call
    if (match) {
      const testId = match[1]; // 取得數字部分
      console.log(`接收到事件 ${eventName}，發送 testId: ${testId} 給 client`);

      // 確保 與 C#伺服器連線正常才發送(B)
      if (client && client.write) {
        try {
          await new Promise((resolve, reject) => {
            client.write(testId, (err) => {         //發送至C#伺服器的訊息(B)
              if (err) reject(err);
              else resolve();
            });
          });
        } catch (error) {
          console.error(`發送 testId ${testId} 失敗:`, error);
        }
      } else {
        console.error('client 連線未準備好，無法發送資料');
      }
    } else {
    */
    const subArr = webRTC_message.indexOf(eventName);
    //console.log(subArr);
    if(subArr==-1) {
      console.log(`發送 ${eventName} 訊息給C#伺服器!`);
      client.write(eventName);                        //發送至C#伺服器的訊息(B)
    }
    /*
    }
    */
  });
});
//

//=== 處理與C#溝通 , Socket 事件處理
function bindClientHandlers() {
  client.on('data', (data) => {
    const message = data.toString().trim();
    console.log('\x1b[33m%s\x1b[0m', `來自C#伺服器的訊息: ${message}`);

    // 檢查是否為 stationX_loading_ready 且包含 JSON 資料
    const match = message.match(/^(station\d+_loading_ready):(.+)$/);
    if (match) {
      const eventName = match[1]; // e.g., station1_loading_ready
      const jsonPart = match[2];
    /*
    // 檢查是否為 station_loading_ready 且包含 JSON 資料
    if (message.startsWith('station_loading_ready:')) {
    */
      try {
        /*const jsonPart = message.replace('station_loading_ready:', '');*/
        const parsedData = JSON.parse(jsonPart);

        console.log(`從kuka端收到裝卸站 ${eventName} 資料:`, parsedData);

        // 廣播事件與資料給前端
        io.emit(eventName, parsedData);
      } catch (err) {
        console.error('解析 ${eventName} JSON 失敗:', err.message);
      }
      return; // 處理完直接 return，避免後續 switch 再處理一次
    }

    let res = message.split("ACK: ").join("");
    console.log(`收到來自kuka端伺服器 ${res} 訊息`);
    switch (res) {
      case 'station1_agv_ready':
      case 'station1_agv_start':
      case 'station1_agv_begin':
      case 'station1_loading_ready':
      case 'station2_agv_end':
      case 'station2_agv_ready':
      case 'station2_agv_start':
      case 'station2_agv_begin':
      case 'station2_loading_ready':
      case 'station3_agv_end':
      case 'station3_loading_ready':
        io.emit(res);
        break;
      default:
        io.emit(res);
        break;
    }
  });

  client.on('end', () => {
    console.log('從C#伺服器接收到結束訊息，關閉連線!');
  });

  client.on('close', () => {
    console.log('與C#伺服器連線已關閉!');
  });

  client.on('error', (error) => {
    let errorMessage = `連線失敗: ${error.message}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}`;

    if (error.code === 'ECONNREFUSED') {
      console.error('❌ 無法連線至 C# 伺服器，將於 5 秒後重試...');
    } else {
      console.error('連線錯誤:', error.message);
    }

    csharpReady = false;
    io.emit('kuka_server_not_ready', {
      message: 'kuka端伺服器尚未準備好，請稍後再試。'
    });

    if (errorMessage !== lastErrorMessage) {
      //require('fs').appendFileSync('service.log', errorMessage + '\n');
      checkLogFileSize();
      fs.appendFileSync('service.log', errorMessage + '\n');
      lastErrorMessage = errorMessage;
    }
    //require('fs').appendFileSync('service.log', `連線失敗: ${error.message}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);

    setTimeout(() => {
      console.log('🔁 嘗試重新連線到 C# 伺服器...');
      client.destroy();
      client = new net.Socket(); // 建立新連線實體
      bindClientHandlers();
      connectToCSharp();
    }, 5000);
  });
}

function connectToCSharp(retryDelay = 5000) {
  client.connect(CSHARP_PORT, CSHARP_SERVER_IP, () => {
    console.log(`\n已連接到 C# 伺服器 (IP: ${CSHARP_SERVER_IP}, PORT: ${CSHARP_PORT})`);
    csharpReady = true;     // 伺服器狀態回復
    lastErrorMessage = '';  // 重設錯誤訊息過濾器

    // 通知等待的 client：C# 伺服ㄗ器已連線
    waitingClients.forEach(sock => {
      sock.emit('kuka_server_ready', {
        message: 'kuka伺服器已重新連線！'
      });
    });
    waitingClients.clear();

    //require('fs').appendFileSync('service.log', `連線時間: ${new Date()}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);
    checkLogFileSize();
    fs.appendFileSync('service.log', `連線時間: ${new Date()}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);
  });
}

bindClientHandlers();
connectToCSharp();

//console.log("Step 7...");

/*
client.connect(CSHARP_PORT, CSHARP_SERVER_IP, () => {
  console.log(`已經與C#伺服器連線(IP為 ${CSHARP_SERVER_IP} , port為 ${CSHARP_PORT})`);
  csharpReady = true;
  require('fs').appendFileSync('service.log', `連線時間: ${new Date()}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);
});
*/

/*
client.on('data', (data) => {
  const message = data.toString().trim();
  console.log('\x1b[33m%s\x1b[0m',   `來自C#伺服器的訊息: ${message}`);

  console.log(`目前狀態為 ${on_line}`)

  // 確保在處理完訊息後不要無意中關閉連接
  // 如有必要，在此處調用 client.end() 或 client.destroy() 來手動斷開連接

  // 處理來自C#伺服器的訊息邏輯...
  let res = message.split("ACK: ").join("");
  console.log(`收到來自kuka端 ${res} 訊息`);

  switch (res) {
  //switch (message) {
    case 'station1_agv_ready':
      console.log('收到 station1_agv_ready 訊息!');
      io.emit('station1_agv_ready');
      break;

    case 'station1_agv_start':
      console.log('收到 station1_agv_start 訊息!');
      io.emit('station1_agv_start');
      break;

    case 'station1_agv_begin':
      console.log('收到 station1_agv_begin 訊息!');
      io.emit('station1_agv_begin');
      break;

    case 'station2_agv_end':
      console.log('收到 station2_agv_end 訊息!');
      io.emit('station2_agv_end');
      break;

    case 'station2_agv_ready':
      console.log('收到 station2_agv_ready 訊息!');
      io.emit('station2_agv_ready');
      break;

    case 'station2_agv_start':
      console.log('收到 station2_agv_start 訊息!');
      io.emit('station2_agv_start');
      break;

    case 'station2_agv_begin':
      console.log('收到 station2_agv_begin 訊息!');
      io.emit('station2_agv_begin');
      break;

    case 'station3_agv_end':
      console.log('收到 station3_agv_end 訊息!');
      io.emit('station3_agv_end');
      break;

    default:
      console.log(`收到 ${res} 訊息!`);
      io.emit(res);
      break;
  }
});

// 處理錯誤
client.on('error', (error) => {
  if (error.code === 'ECONNREFUSED') {
    console.error('連線失敗: C#伺服器未開啟!');
  } else {
    console.error('連線錯誤:', error.message);
  }

  csharpReady = false;
  //waitingClients.add(socket);
  io.emit('kuka_server_not_ready', {
    message: 'kuka端伺服器尚未準備好，請稍後再試。'
  });


  require('fs').appendFileSync('service.log', `連線失敗: ${error.message}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);

  //client.destroy(); // 確保 socket 關閉

  // 等待後自動重連（防止 client 被破壞，要新建）
  setTimeout(() => {
    console.log('🔁 嘗試重新連線到 C# 伺服器...');
    // 需要重新 new 一個 net.Socket() 實體
    client.destroy();
    global.client = new net.Socket(); // 重新初始化 client
    bindClientHandlers();             // 重新綁定事件
    connectToCSharp();                // 嘗試連線
  }, 5000);
});

// 保持連接
client.on('end', () => {
  console.log('從C#伺服器接收到結束訊息，關閉連線!');
});

// 處理關閉
client.on('close', () => {
  console.log('與C#伺服器連線已關閉!');
});
*/

//===
/*
app.post('/log-ip', (req, res) => {
  const ip = req.body.ip;
  const logStr = `[${new Date().toISOString()}] Client reported IP: ${ip}\n`;

  fs.appendFile('ip-log.txt', logStr, (err) => {
    if (err) {
      console.error('寫入 log 失敗:', err);
      return res.status(500).send('Log failed');
    }
    console.log('成功寫入 IP 至 log:', ip);
    res.send('Log success');
  });
});
*/
http.listen(PORT, () => {
  console.log(`\n應用軟體已在 port ${PORT} 執行!` );
});

require('dotenv').config();

const readline = require('readline');
const express = require('express');
const cors = require('cors');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);
const os = require('os');


app.use(express.json());    // 解析 JSON POST 資料

// 提供前端靜態頁面或資料，如 index.html, config.json
app.use(express.static('public'));      //for vue3 application, npm run serve
//app.use(express.static('dist'));      //for vue3 application, npm run build

// 載入 Node.js 內建的 path 模組，用來處理檔案與目錄路徑（可以跨平台，不必自己手動處理 / 或 \）
const path = require('path');
const logFilePath = path.join(__dirname, 'service.log');  // 程式所在的資料夾路徑 和 service.log 組合成一個完整路徑

const fs = require('fs');

const MAX_LOG_SIZE = 10 * 1024 * 1024; // 10MB

const net = require('net')
const waitingClients = new Set();

let client = new net.Socket();

let csharpReady = false;    // 用來標記是否成功連線kuka伺服器
let on_line = false;        // false: off line 模擬模式, true: on line 上線模式
let on_line_move_mode = true;
let lastErrorMessage = '';

// HTTP API 和 WebSocket 共用同一個 Port 6500, 伺服器同時處理 HTTP 請求和 WebSocket 連線(協定不同)
const PORT = Number(process.env.PORT) || 6500;

// 針對 與kuka伺服器連線, 所使用的 Port 6600
const CSHARP_PORT = Number(process.env.CSHARP_PORT) || 6600;
// 針對 與kuka伺服器連線, 所使用的 IP
const CSHARP_SERVER_IP = process.env.CSHARP_SERVER_IP;
const SERVER_IP = process.env.SERVER_IP;
console.log(`\nSERVER_IP: ${SERVER_IP}`);

let RUN_MODE = false;   // true:上線模式, false:模擬模式
RUN_MODE = ['true', '1', 'yes'].includes((process.env.RUN_MODE || '').toLowerCase());
console.log(`\nRUN_MODE: ${RUN_MODE}`)

let MOVE_MODE = true;  // true: agv運輸, false: 堆高機運輸
MOVE_MODE = ['true', '1', 'yes'].includes((process.env.MOVE_MODE || '').toLowerCase());
console.log(`\nMOVE_MODE: ${MOVE_MODE}`)

//====
on_line = RUN_MODE;
on_line_move_mode = MOVE_MODE;
let localIP = SERVER_IP;
//===

/*
A.區分兩個服務的端口：
  主伺服器SERVER_IP（192.168.68.56）：Socket.IO 使用 6500 端口（HTTP/WebSocket）
  目標裝置CSHARP_SERVER_IP（192.168.68.53）：TCP Socket 使用 6600 端口（純 TCP，不涉及 CORS）

B.為什麼不需要為 TCP 端口（6600）設定 CORS？
CORS 是 HTTP/Web 協定的安全機制，僅適用於：
  瀏覽器發起的 HTTP/HTTPS 請求
  WebSocket 連線（如 Socket.IO）

TCP Socket（6600）是傳輸層協定：
  直接透過 net 模組通訊，不受瀏覽器 CORS 限制
  只需確保防火牆允許 6600 端口的連線。
*/
const allowedOrigin = [
  `http://${SERVER_IP}:6500`,   // 主伺服器自身, HTTP/WebSocket
  `http://${SERVER_IP}:8080`,   // 開發環境(如 Vue dev server)前端端口
  `http://${SERVER_IP}:8060`,   // 生產環境前端端口

  `http://192.168.17.167:8080`, // 有線網路 IP的前端端口(開發環境)
  `http://192.168.17.167:8060`, // 有線網路 IP的前端端口(生產環境)
];

app.use(cors({
  origin: allowedOrigin,
  credentials: true
}));

//// 設定終端輸入介面
//const rl = readline.createInterface({
//  input: process.stdin,
//  output: process.stdout,
//});

// 啟用鍵盤事件偵聽
readline.emitKeypressEvents(process.stdin);
if (process.stdin.isTTY) {
  process.stdin.setRawMode(true); // 設定為原始模式 (raw mode)，以便偵測單鍵輸入事件
}

// 監聽 Ctrl+C (SIGINT) 或應用程式結束
const shutdown = () => {
  console.log('Server shutting down...');

  // 通知所有 WebSocket 客戶端
  io.emit('server_shutdown', '伺服器即將關閉');  //廣播至前端瀏覽器
  client.write('server_shutdown');              //廣播至後端kuka伺服器

  // 給點時間讓訊息發送後再關閉
  setTimeout(() => { process.exit(0); }, 1000);
};

process.on('SIGINT', shutdown);   // 監聽 `Ctrl+C` 事件

process.on('exit', shutdown);     // 監聽 `process.exit`

function checkLogFileSize() {
  //const logPath = 'service.log';
  if (fs.existsSync(logFilePath)) {
    const stats = fs.statSync(logFilePath);
    if (stats.size > MAX_LOG_SIZE) {
      //const backupName = `service_${Date.now()}.log`;
      const backupName = path.join(__dirname, `service_${Date.now()}.log`);
      fs.renameSync(logFilePath, backupName);   // 備份舊 log
      fs.writeFileSync(logFilePath, '');      // 建立新空檔案
      //fs.promises.writeFile(logPath, '')
      //  .catch(err => console.error('初始化 log 檔失敗:', err));
      console.log(`📁 日誌檔案過大，已備份為 ${backupName}`);
    }
  }
}

// 確保 log 檔案存在，或建立空檔案（初始化）
function ensureLogFileExists() {
  if (!fs.existsSync(logFilePath)) {
    fs.writeFileSync(logFilePath, ''); // 建立空檔案
    //fs.promises.writeFile(logFilePath, '')
    //  .catch(err => console.error('初始化 log 檔失敗:', err));
  }
}


// ==============================================================================


// 呼叫這個函式一次即可
ensureLogFileExists();

let connectedPeers = new Set();   //使用Set以確保socket.id唯一性

let resetRequested = false;       // 重置狀態

// 儲存每個 socket 的 interval ID
//const readyIntervals = new Map();
let readyInterval_ready = null; // 用來存 setInterval 的 ID
let readyInterval_end = null;   // 用來存 setInterval 的 ID

// 瀏覽器 Socket.IO 事件處理
io.on('connection', (socket) => {
  const clientAPP = socket.handshake.query.clientAPP;
  if (clientAPP) {
    console.log(`與 ${clientAPP} 已連線`);
  }
  console.log(`Client connected, socket id: ${socket.id}`);

  connectedPeers.add(socket.id);

  //client.write('connection');     //發送至kuka伺服器的訊息(B)
  socket.emit('connected');         //發送至所有client的訊息

  // 如果沒有與kuka伺服器連上，馬上通知 client
  if (!csharpReady) {
    waitingClients.add(socket);
    socket.emit('kuka_server_not_ready', {
      message: 'kuka端伺服器尚未準備好，請稍後再試。'
    });
  }

  socket.on('error', (err) => {
    console.error('WebSocket 發生錯誤:', err.message);
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
      client.write('station1_call');    //廣播至後端kuka伺服器的訊息(B)
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

      console.log('\x1b[34m%s\x1b[0m', 'AGV 運行結束，已到達組裝區');
      //socket.emit('station2_agv_end', items,);
      socket.emit('station2_agv_end');
    }
  });

  // station2_call 事件處理
  socket.on('station2_call', async (data) => {
    if (!socket.connected) {
      console.log('Socket disconnected, cannot proceed with station2_call');
      return;
    }
    //const { items, orderNums } = data;
    //console.log("收到 station1_call 訊息，內容：", data);
    console.log('收到 station2_call 訊息');

    if (on_line) {
      client.write('station2_call');    //廣播至後端kuka伺服器的訊息(B)
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

      if (!socket.connected) return; // 確保連線有效
      console.log('AGV 已在組裝區裝卸站...');
      socket.emit('station2_agv_ready');

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

      console.log('\x1b[34m%s\x1b[0m', 'AGV 運行結束，已到達成品區');
      socket.emit('station3_agv_end');
    }
  });

  // agv_reset 事件處理
  socket.on('agv_reset', () => {
    console.log('收到 agv_reset 訊息，重置所有動作...');
    resetRequested = true;          // 設置重置請求為 true
    //socket.emit('agv_ack');       // 向客戶端確認收到重置請求
    client.write('agv_reset');      // 廣播至後端kuka伺服器的訊息(B)
  });

  socket.on('triggerLogout', (payload) => {
    console.log('📩 Received triggerLogout from:', payload.empID);

    // Broadcast 給其他所有 client（除了發送者）
    socket.broadcast.emit('triggerLogout', payload);
    //socket.emit('triggerLogout', payload);
  });

  socket.on('station2_trans_call', (payload) => {
    console.log('Received station2_trans by:', payload.empID , payload.empName);

    if (readyInterval_ready) {
      console.log('已在持續發送 station2_trans_ready， 忽略本次呼叫');
      return;
    }

    readyInterval_ready = setInterval(() => {
      io.emit('station2_trans_ready', payload); // 全部 client 收到
      console.log(`📤 Sent station2_trans_ready`);
    }, 2000);
  });

  // 當收到 station2_trans_begin 時，停止發送
  socket.on('station2_trans_begin', () => {
    console.log(`🛑 Received station2_trans_begin from ${socket.id}`);

     if (readyInterval_ready) {
      clearInterval(readyInterval_ready);
      readyInterval_ready = null;
    }

    if (readyInterval_end) {
      console.log('⏳ 已在持續發送 station2_trans_end， 忽略本次呼叫');
      return;
    }

    readyInterval_end = setInterval(() => {
      io.emit('station2_trans_end'); // 全部 client 收到
      console.log(`📤 Sent station2_trans_end`);
    }, 2000);
  });

  socket.on('station2_trans_over', () => {
    console.log(`Received station2_trans_over from ${socket.id}`);

     if (readyInterval_end) {
      clearInterval(readyInterval_end);
      readyInterval_end = null;
    }
  });

  socket.on('assemble-started', (payload) => {
    console.log('assemble-started with payload', payload);

    socket.broadcast.emit('assemble-started', payload);
  })

  socket.on('schedule_mode-ok', () => {
    console.log('schedule_mode-ok');

    socket.broadcast.emit('schedule_mode-ok');
  })

  socket.on('icon-disable', (payload) => {
    console.log('icon-disable with payload', payload);

    socket.broadcast.emit('icon-disable', payload);
  })

  socket.on('assemble-batch-released', (payload) => {
    console.log('assemble-batch-released with payload', payload);

    socket.broadcast.emit('assemble-batch-released', payload);
  })


  // 斷線時也清掉 interval
  //socket.on('disconnect', () => {
  //  if (readyIntervals.has(socket.id)) {
  //    clearInterval(readyIntervals.get(socket.id));
  //    readyIntervals.delete(socket.id);
  //  }
  //  connectedPeers.delete(socket.id);
  //  console.log(`❌ Client disconnected: ${socket.id}`);
  //});

  // 使用 socket.onAny 監聽所有事件
  socket.onAny(async (eventName) => {
    let webRTC_message = ['candidate', 'answer', 'offer', 'join', 'disconnect', 'error',
      'station2_trans_over', 'station2_trans_end', 'station2_trans_begin', 'station2_trans_call',
      'station3_trans_over', 'station3_trans_end', 'station3_trans_begin', 'station3_trans_call',
    ];
    //let webRTC_message = ['candidate', 'answer', 'offer', 'join', 'disconnect'];

    //if (!socket.connected) {
    //  console.log('Socket disconnected, cannot proceed this socket');
    //  return;
    //}

    console.log(`收到來自網頁端 ${eventName} 訊息`);
    const subArr = webRTC_message.indexOf(eventName);
    //console.log(subArr);
    if(subArr==-1 && on_line==true) {
      console.log(`發送 ${eventName} 訊息給kuka伺服器!`);
      client.write(eventName);                        //廣播至後端kuka伺服器的訊息(B)
    }
  });
});

// 處理與kuka端溝通 , Socket 事件處理
function bindClientHandlers() {
  client.on('data', (data) => {     //廣播至後端kuka伺服器
    const message = data.toString().trim();
    console.log('\x1b[33m%s\x1b[0m', `來自kuka端伺服器的訊息: ${message}`);

    const match = message.match(/^(station\d+_loading_ready)$/);
    if (match) {
      const eventName = message;      // 例如 station1_loading_ready 訊息
      //const jsonPart = match[2];

      try {
        //const parsedData = JSON.parse(jsonPart);

        console.log(`從kuka端收到裝卸站 ${eventName} 資料:`);

        // 廣播事件與資料給前端瀏覽器
        //io.emit(eventName, parsedData);
        io.emit(eventName); //廣播至前端瀏覽器
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
      case 'station1_error':
      case 'station2_error':
        console.log("send", res, "to socket io...");
        io.emit(res); //廣播至前端瀏覽器
        break;
      default:
        io.emit(res); //廣播至前端瀏覽器
        break;
    }
  });

  client.on('end', () => {
    console.log('從kuka伺服器接收到結束訊息，關閉連線!');
  });

  client.on('close', () => {
    console.log('與kuka伺服器連線已關閉!');
  });

  client.on('error', (error) => {
    let errorMessage = `連線失敗: ${error.message}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}`;

    if (error.code === 'ECONNREFUSED') {
      console.error('❌ 無法連線至kuka伺服器，將於 5 秒後重試...');
    } else {
      console.error('連線錯誤:', error.message);
    }

    csharpReady = false;
    io.emit('kuka_server_not_ready', {  //廣播至前端瀏覽器
      message: 'kuka端伺服器尚未準備好，請稍後再試。'
    });

    if (errorMessage !== lastErrorMessage) {
      //require('fs').appendFileSync('service.log', errorMessage + '\n');
      checkLogFileSize();
      fs.appendFileSync(logFilePath, errorMessage + '\n');
      lastErrorMessage = errorMessage;
    }
    //require('fs').appendFileSync('service.log', `連線失敗: ${error.message}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);

    setTimeout(() => {
      console.log('🔁 嘗試重新連線到kuka伺服器...');
      client.destroy();
      client = new net.Socket(); // 建立新連線實體
      bindClientHandlers();
      connectToCSharp();
    }, 5000);
  });
}

function connectToCSharp(retryDelay = 5000) {
  client.connect(CSHARP_PORT, CSHARP_SERVER_IP, () => {
    console.log(`\n已連接到kuka伺服器 (IP: ${CSHARP_SERVER_IP}, PORT: ${CSHARP_PORT})`);
    csharpReady = true;     // 伺服器狀態回復
    lastErrorMessage = '';  // 重設錯誤訊息過濾器

    // 通知等待的 client：kuka伺服器已連線
    waitingClients.forEach(sock => {
      sock.emit('kuka_server_ready', {
        message: 'kuka伺服器已重新連線！'
      });
    });
    waitingClients.clear();

    checkLogFileSize();
    fs.appendFileSync('service.log', `連線時間: ${new Date()}, mode: ${on_line}, RUN_MODE: ${RUN_MODE}\n`);
  });
}

bindClientHandlers();
connectToCSharp();

http.listen(PORT, () => {
  console.log(`\n` );
  console.log(`\x1b[34mBuild 2026-06-08\x1b[0m`);
  console.log(`應用軟體已在 port ${PORT} 執行!` );
});

const fs = require('fs');
const os = require('os');
const path = require('path');
const { execSync } = require('child_process');

function getIpAddress(interfaceName) {
  try {
    const output = execSync('ipconfig', { encoding: 'utf8' });
    const lines = output.split('\n');
    let foundInterface = false;

    for (let line of lines) {
      line = line.trim();

      // 檢查是否找到特定的介面名稱
      if (line.includes(interfaceName)) {
        foundInterface = true;
      }

      // 如果已經找到該介面，並且此行包含 IPv4 地址
      if (foundInterface && line.includes('IPv4')) {
        const match = line.match(/(\d{1,3}\.){3}\d{1,3}/);
        if (match) {
          return match[0]; // 回傳IP
        }
      }
    }

    console.error(`❌ 找不到 ${interfaceName} 的 IPv4 位址`);
    return null;
  } catch (err) {
    console.error(`❌ 執行 ipconfig 出錯`, err);
    return null;
  }
}

function getLocalIp(card = 'false') {
  if (card === 'true') {
    // 如果卡片為 true，則取乙太網路卡 IP
    return getIpAddress('vEthernet (Default Switch)');
  }
  // 預設取 Wi-Fi 的 IP
  return getIpAddress('Wi-Fi');
}

// 解析參數
const args = process.argv.slice(2);
let remoteIp = null;
let runMode = 'false'; // 預設 false
let card = 'false'; // 預設 false

args.forEach(arg => {
  const [key, value] = arg.split('=');
  if (key === 'remote' && value) {
    remoteIp = value;
  }
  if (key === 'mode' && value) {
    runMode = value;
  }
  if (key === 'card' && value) {
    card = value;
  }
});

const envPath = path.join(__dirname, '.env');

// 根據 card 參數取得 IP
const localIp = getLocalIp(card);

if (!localIp) {
  console.error('❌ 無法取得本機IP');
  process.exit(1);
}

// 讀取 .env
let envContent = fs.readFileSync(envPath, 'utf-8');

// 處理 SERVER_IP
if (/^SERVER_IP=.*$/m.test(envContent)) {
  envContent = envContent.replace(/^SERVER_IP=.*$/m, `SERVER_IP=${localIp}`);
} else {
  envContent += `\nSERVER_IP=${localIp}`;
}

// 處理 CSHARP_SERVER_IP
if (/^CSHARP_SERVER_IP=.*$/m.test(envContent)) {
  if (remoteIp) {
    envContent = envContent.replace(/^CSHARP_SERVER_IP=.*$/m, `CSHARP_SERVER_IP=${remoteIp}`);
  } else {
    envContent = envContent.replace(/^CSHARP_SERVER_IP=.*$/m, `CSHARP_SERVER_IP=${localIp}`);
  }
} else {
  envContent += `\nCSHARP_SERVER_IP=${remoteIp ? remoteIp : localIp}`;
}

// 處理 RUN_MODE
if (/^RUN_MODE=.*$/m.test(envContent)) {
  envContent = envContent.replace(/^RUN_MODE=.*$/m, `RUN_MODE=${runMode}`);
} else {
  envContent += `\nRUN_MODE=${runMode}`;
}

// 寫回 .env
fs.writeFileSync(envPath, envContent.trim() + '\n', 'utf-8'); // 確保最後一行有換行

// 顯示結果
console.log(`✅ SERVER_IP 設為: ${localIp}`);
console.log(`✅ CSHARP_SERVER_IP 設為: ${remoteIp ? remoteIp : localIp}`);
console.log(`✅ RUN_MODE 設為: ${runMode}`);


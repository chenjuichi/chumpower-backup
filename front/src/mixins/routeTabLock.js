//import { randomUUID }  from 'routeTabLock.js';

const TAB_ID = randomUUID();
const HEARTBEAT_MS = 2000;
const STALE_MS = HEARTBEAT_MS * 3;

function randomUUID() {
  // 1) 現代瀏覽器原生
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }

  // 2) 有 getRandomValues：產生真 v4 UUID（強隨機）
  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const buf = new Uint8Array(16);
    crypto.getRandomValues(buf);
    // v4 variant bits
    buf[6] = (buf[6] & 0x0f) | 0x40; // version 4
    buf[8] = (buf[8] & 0x3f) | 0x80; // variant RFC 4122
    const hex = [...buf].map(b => b.toString(16).padStart(2, '0')).join('');
    return (
      hex.slice(0, 8) + '-' +
      hex.slice(8, 12) + '-' +
      hex.slice(12, 16) + '-' +
      hex.slice(16, 20) + '-' +
      hex.slice(20)
    );
  }

  // 3) 最後備案（弱隨機，盡量少用，但可在極舊環境運作）
  let d = Date.now();
  if (typeof performance !== 'undefined' && typeof performance.now === 'function') {
    d += performance.now();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, c => {
    const r = (d + Math.random() * 16) % 16 | 0;
    d = Math.floor(d / 16);
    return (c === 'x' ? r : (r & 0x3) | 0x8).toString(16);
  });
}


function makeKeys(userId, routeKey) {
  // 以「使用者 + 路由」為維度上鎖；不同 userId 不互斥
  const prefix = `routeLock:${userId || 'guest'}:${routeKey}`;
  return {
    OWNER_KEY: `${prefix}:owner`,    // = TAB_ID
    HB_KEY:    `${prefix}:hb`,       // = timestamp
  };
}

export function getRouteKeyByRoute(route) {
  // 你也可以改用 route.name；用 path 較直觀
  return route?.path || '';
}

export function tryAcquireRouteLock(userId, routeKey) {
  const { OWNER_KEY, HB_KEY } = makeKeys(userId, routeKey);
  const now = Date.now();

  const owner = localStorage.getItem(OWNER_KEY);
  const lastHb = Number(localStorage.getItem(HB_KEY) || 0);
  const hasValidLock = owner && (now - lastHb) < STALE_MS;

  if (!hasValidLock || owner === TAB_ID) {
    localStorage.setItem(OWNER_KEY, TAB_ID);
    localStorage.setItem(HB_KEY, String(now));
    return true; // 取得鎖
  }
  return false;  // 被同一 user 的其他分頁佔用
}

let hbTimer = null;
export function startHeartbeat(userId, routeKey) {
  const { OWNER_KEY, HB_KEY } = makeKeys(userId, routeKey);
  stopHeartbeat();
  hbTimer = setInterval(() => {
    const owner = localStorage.getItem(OWNER_KEY);
    if (owner === TAB_ID) {
      localStorage.setItem(HB_KEY, String(Date.now()));
    } else {
      stopHeartbeat();
    }
  }, HEARTBEAT_MS);
}

export function stopHeartbeat() {
  if (hbTimer) {
    clearInterval(hbTimer);
    hbTimer = null;
  }
}

export function releaseRouteLock(userId, routeKey) {
  const { OWNER_KEY, HB_KEY } = makeKeys(userId, routeKey);
  const owner = localStorage.getItem(OWNER_KEY);
  if (owner === TAB_ID) {
    localStorage.removeItem(OWNER_KEY);
    localStorage.removeItem(HB_KEY);
  }
  stopHeartbeat();
}

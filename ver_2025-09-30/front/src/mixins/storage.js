// storage.js
class MyStorage {
  constructor() {
    // 建立 tabId，存在 sessionStorage (確保不同分頁不同)
    if (!sessionStorage.getItem("tabId")) {
      sessionStorage.setItem("tabId", Date.now() + "_" + Math.random())
    }
    this.tabId = sessionStorage.getItem("tabId")
  }

  // 存資料
  setItem(key, value, perTab = true) {
    const fullKey = perTab ? `${this.tabId}_${key}` : key
    localStorage.setItem(fullKey, JSON.stringify(value))
  }

  // 取資料
  getItem(key, perTab = true) {
    const fullKey = perTab ? `${this.tabId}_${key}` : key
    const item = localStorage.getItem(fullKey)
    try {
      return JSON.parse(item)
    } catch {
      return item
    }
  }

  // 移除資料
  removeItem(key, perTab = true) {
    const fullKey = perTab ? `${this.tabId}_${key}` : key
    localStorage.removeItem(fullKey)
  }
}

// 單例
export const myStorage = new MyStorage()
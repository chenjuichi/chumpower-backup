import mitt from 'mitt';

const eventBus = mitt();

let isAuthenticated = false;

const authModule = {
  get isAuthenticated() {
    return isAuthenticated;
  },

  set isAuthenticated(value) {
    isAuthenticated = value;
    eventBus.emit('authStateChanged', isAuthenticated); // 发布认证状态变更事件
  },
};

//•  export default 用於匯出模組的預設值，可以是變數、函數或class。導入時不需要使用大括弧，可以隨意命名。
//•  export 用於命名匯出，導入時需要使用大括弧並使用相同的名稱。
export { authModule, eventBus };
//export default eventBus;
import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/HomeView.vue'
import About from '../views/AboutView.vue'
import A from '../views/a.vue';
import B from '../views/b.vue';
import C from '../views/c.vue';
import MyTable from '../views/MyTable.vue';
//import LoginRegister from '@/views/LoginRegister.vue';
import LoginRegister from '../views/LoginForm2.vue';
import Employer from '../views/Employer.vue';
import Main from '../views/Main.vue';
import NotFound from '../views/NotFound.vue';   // 404 Not Found 頁面

const routes = [
  { path: '/', name: 'LoginRegister', component: LoginRegister, meta: { hideNavAndFooter: true } },
  { path: '/main', name: 'Main', component: Main },
  { path: '/employer', name: 'Employer', component: Employer },
  { path: '/home', name: 'Home', component: Home },
  { path: '/about', name: 'About', component: About },
  { path: '/a', name: 'a', component: A },
  { path: '/b', name: 'b', component: B },
  { path: '/c', name: 'c', component: C },
  { path: '/d', name: 'd', component: MyTable },
  { path: '/:pathMatch(.*)*', name: 'NotFound', component: NotFound, meta: { hideNavAndFooter: true } }, // 404 Not Found 路由
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
});

router.beforeEach((to, from, next) => {
  const toDepth = to.path.split('/').length;
  const fromDepth = from.path.split('/').length;
  to.meta.transitionName = toDepth < fromDepth ? 'slide-right' : 'slide-left';
  //next();

  // 認證檢查邏輯
  let isAuthenticated = localStorage.getItem('Authenticated');
  if (isAuthenticated === null) {
    //isAuthenticated = false;
    isAuthenticated = 'false'; // 確保初始值為字串 'false'
    localStorage.setItem('Authenticated', isAuthenticated);
  } else {
    isAuthenticated = JSON.parse(isAuthenticated); // 將字串轉換為布爾值
  }

  console.log("routing is(to, from, auth):", to.name, from.name, isAuthenticated);

  if (to.name !== 'LoginRegister' && !isAuthenticated) {
    next({ name: 'LoginRegister' });
  } else {
    next();
  }
});

// 將所有路由的 path 和 name 儲存到 routerLinks
const routerLinks = routes.map(route => {
  return { path: route.path, name: route.name };
});

//•  export default 用於匯出模組的預設值，可以是變數、函數或class。導入時不需要使用大括弧，可以隨意命名。
//•  export 用於命名匯出，導入時需要使用大括弧並使用相同的名稱。
export { router, routerLinks };
//export default router;


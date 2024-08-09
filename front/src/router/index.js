import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/HomeView.vue'
import About from '../views/AboutView.vue'

import A from '../views/a.vue';
import B from '../views/b.vue';
import C from '../views/c.vue';
import D from '../views/d.vue';

import E from '../views/e.vue';
import F from '../views/f.vue';
import G01 from '../views/g01.vue';
import G01C from '../views/g01c.vue';
import G01D from '../views/g01d.vue';
import G1 from '../views/g1.vue';
import G2 from '../views/g2.vue';
import G3 from '../views/g3.vue';
import H1 from '../views/h1.vue';
import H2 from '../views/h2.vue';
import H3 from '../views/h3.vue';
import J1 from '../views/j1.vue';
import J2 from '../views/j2.vue';
import J3 from '../views/j3.vue';
import J4 from '../views/j4.vue';

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
  { path: '/a', name: 'A', component: A },
  { path: '/b', name: 'B', component: B },
  { path: '/c', name: 'C', component: C },
  { path: '/d', name: 'D', component: D },
  { path: '/e', name: 'E', component: E },
  { path: '/f', name: 'F', component: F },
  { path: '/g01', name: 'G01', component: G01 },
  { path: '/g01c', name: 'G01C', component: G01C },
  { path: '/g01d', name: 'G01D', component: G01D },
  { path: '/g1', name: 'G1', component: G1 },
  { path: '/g2', name: 'G2', component: G2 },
  { path: '/g3', name: 'G3', component: G3 },
  { path: '/h1', name: 'H1', component: H1 },
  { path: '/h2', name: 'H2', component: H2 },
  { path: '/h3', name: 'H3', component: H3 },
  { path: '/j1', name: 'J1', component: J1 },
  { path: '/j2', name: 'J2', component: J2 },
  { path: '/j3', name: 'J3', component: J3 },
  { path: '/j4', name: 'J4', component: J4 },

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


import { createRouter, createWebHistory } from 'vue-router';
import Home from '../views/HomeView.vue'
import About from '../views/AboutView.vue'
import A from '../views/a.vue';
import B from '../views/b.vue';
import C from '../views/c.vue';
import MyTable from '../views/MyTable.vue';
import LoginRegister from '@/views/LoginRegister.vue';

const routes = [
  //{ path: '/', name: 'Home', component: Home },
  { path: '/', name: 'LoginRegister', component: LoginRegister },
  { path: '/about', name: 'About', component: About },
  { path: '/a', name: 'a', component: A },
  { path: '/b', name: 'b', component: B },
  { path: '/c', name: 'c', component: C },
  { path: '/d', name: 'd', component: MyTable },
];

const router = createRouter({
  history: createWebHistory(process.env.BASE_URL),
  routes
});

router.beforeEach((to, from, next) => {
  const toDepth = to.path.split('/').length;
  const fromDepth = from.path.split('/').length;
  to.meta.transitionName = toDepth < fromDepth ? 'slide-right' : 'slide-left';
  next();
});

export default router;


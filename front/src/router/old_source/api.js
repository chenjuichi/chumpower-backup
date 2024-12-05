
import { apiOperation, showSnackbar, setupListUsersWatcher, departments, snackbar, snackbar_info, snackbar_color, temp_desserts, loginUser, loginEmpIDInput } from '../crud.js';

// 使用 apiOperation 函式來建立 API 請求
export const listDepartments = apiOperation('get', '/listDepartments');
export const listUsers = apiOperation('get', '/listUsers');
export const register = apiOperation('post', '/register');
export const login = apiOperation('post', '/login');

// 其他變數和函式
export { showSnackbar, setupListUsersWatcher };
export { departments, snackbar, snackbar_info, snackbar_color, temp_desserts, loginUser, loginEmpIDInput };

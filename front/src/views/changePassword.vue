<template>
<div>
  <!-- Snackbar -->
  <v-snackbar v-model="snackbar" location="top right" timeout="2000" :color="snackbar_color">
    {{ snackbar_info }}
    <template v-slot:actions>
      <v-btn color="#adadad" @click="snackbar = false">
        <v-icon dark>mdi-close-circle</v-icon>
      </v-btn>
    </template>
  </v-snackbar>

  <v-dialog
    v-model="localDialog"
    persistent max-width="450px"
    max-height="80vh"
    @update:model-value="updateDialog"
    class="custom-dialog-position"
  >
    <v-card elevation="16" class="custom-card">
      <v-img class="align-end text-white custom-img" height="200" :src="imageSrc" cover>
        <v-card-title>{{ company_name }}</v-card-title>
      </v-img>

      <v-card-subtitle class="pt-2">
        <i class="fa-solid fa-unlock-keyhole" style="color: #63E6BE;" />
        修改密碼
      </v-card-subtitle>

      <v-card-text class="custom-card-text">
        <v-container class="custom-container">
          <!--舊密碼-->
          <div style="display:flex; align-items:center; padding-bottom:10px; position:relative;
            top:-10px;">
            <!-- 左邊的文字 -->
            <span style="width:60px; font-weight:bold;  align-self:center;">舊密碼</span>
            <v-text-field
              class="custom-field"
              density="compact"
              color="primary"
              max-width="225"
              prepend-icon="mdi-lock"
              :append-icon="eyeShow1 ? 'mdi-eye-off' : 'mdi-eye'"
              :type="eyeShow1 ? 'password' : 'text'"
              @click:append="eyeShow1 = !eyeShow1"
              @keydown.enter="userLogin"
              @update:focused ="checkUsers"

              v-model="oldPassword"
              ref="oldPasswordRef"
              :rules="[requiredRule, oldPasswordCheckRule]"
            ></v-text-field>
          </div>
          <!--新密碼-->
          <div style="display:flex; align-items:center; padding-bottom:10px; position:relative;
            top:-20px;">
            <!-- 左邊的文字 -->
            <span style="width: 60px; font-weight: bold;">新密碼</span>
            <v-text-field
              class="custom-field"
              density="compact"
              color="primary"
              max-width="185"
              prepend-icon="mdi-lock"

              :type="eyeShow1 ? 'password' : 'text'"
              @click:append="eyeShow1 = !eyeShow1"

              v-model="newPassword"
              ref="newPasswordRef"

              :rules="[requiredRule, passwordRule, newNotSameAsOldRule]"
            ></v-text-field>
          </div>
          <!--確認密碼-->
          <div style="display:flex; align-items:center; padding-bottom:10px; position:relative;
            top:-30px;">
            <!-- 左邊的文字 -->
            <span style="width: 70px; font-weight: bold;">確認密碼</span>
            <v-text-field
              class="custom-field"
              density="compact"
              color="primary"
              max-width="185"
              prepend-icon="mdi-account-check"
              :type="eyeShow1 ? 'password' : 'text'"

              v-model="confirmPpassword"
              :rules="[requiredRule, confirmPasswordRule]"
            ></v-text-field>
          </div>
        </v-container>
      </v-card-text>
      <v-card-actions class="custom-card-actions">
        <!-- <v-spacer></v-spacer> -->
        <v-btn color="blue darken-1" text @click="closeDialog">取消</v-btn>
        <v-btn color="blue darken-1" text @click="userUpdatePassword" :disabled="checkDataForSaveButton">確定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</div>
</template>

<script setup>
import { ref, computed, watch, defineComponent, onMounted, nextTick } from 'vue';
//import axios from 'axios';
import { myMixin } from '../mixins/common.js';

import { showSnackbar, snackbar, snackbar_info, snackbar_color }  from '../mixins/crud.js';
import { apiOperation }  from '../mixins/crud.js';
// 使用 apiOperation 函式來建立 API 請求
const login2 = apiOperation('post', '/login2');
const updatePassword = apiOperation('post', '/register');

//=== component name ==
defineComponent({
  name: 'ChangePassword'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({
  dialog: {
    type: Boolean,
    required: true
  }
});

// === emits ===
const emit = defineEmits(['update:dialog']);

//=== data ===
const company_name = ref('銓寶工業股份有限公司')
const imageSrc = ref(require('../assets/organic-1280537_1280.jpg')); //企業視覺圖像

//const snackbar = ref(false);
//const snackbar_color = ref('');   // default: 'red accent-2'
//const snackbar_info = ref('');
//const snackbar_icon_color = ref('#adadad');
//const snackbar_timeout = ref(2000);

//const dialog = ref(false);
const localDialog = ref(props.dialog);

const oldPasswordRef = ref(null);
const oldPasswordError = ref(true);
const oldPassword = ref('');
const newPasswordRef = ref(null);
const newPassword = ref('');
const confirmPpassword = ref('');
const currentUser = ref(null);
const eyeShow1 = ref(true);

const requiredRule = value => !!value || '欄位必須輸入資料...';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{6,}$/.test(value) || '需6個字以上，且含數字和小寫字母!';
const confirmPasswordRule = value => value === newPassword.value || '密碼不相同!';

const oldPasswordCheckRule = value => {
  if (oldPasswordError.value) return '舊密碼錯誤!';
  return true;
};

const newNotSameAsOldRule = value => {
  if (value === oldPassword.value) {
    return '新舊密碼不可以相同!';
  }
  return true;
};

//=== watch ===
watch(() => props.dialog, (newVal) => {
  localDialog.value = newVal;
});

watch(oldPassword, () => {
  oldPasswordError.value = false;
});

//=== computed ===
const checkDataForSaveButton = computed(() => {
  return !(newPassword.value && confirmPpassword.value && oldPasswordError.value == false);
});

//=== mounted ===
onMounted(async () => {
  console.log("changePassword.vue, mounted()...");

  //let user = localStorage.getItem("loginedUser");
  //currentUser.value = user ? JSON.parse(user) : null;
  //console.log("currentUser:", currentUser.value);

  //user define
  let userRaw = sessionStorage.getItem('auth_user');
  if (!userRaw) {
    // 只在第一次開分頁時，從 localStorage 複製一份
    userRaw = localStorage.getItem('loginedUser');
    if (userRaw) {
      sessionStorage.setItem('auth_user', userRaw);
    }
  }
  currentUser.value = userRaw ? JSON.parse(userRaw) : null;

  if (currentUser.value) {
    //currentUser.value.setting_items_per_page = pagination.itemsPerPage;
    //currentUser.value.setting_lastRoutingName = routeName.value;

    localStorage.setItem('loginedUser', JSON.stringify(currentUser.value));
    sessionStorage.setItem('auth_user', JSON.stringify(currentUser.value));
  }
  console.log("currentUser:", currentUser.value);
  //
});

//=== method ===
const updateDialog = (value) => {
  localDialog.value = value;
  if (!value) {
    emit('update:dialog', false);
  }
};

const closeDialog = () => {
  localDialog.value = false;
  emit('update:dialog', false);
};

const userLogin = async () => {
  console.log("userLogin()...");

  const payload = {
    empID: currentUser.value.empID,
    password: oldPassword.value,
  };

  const status = await login2(payload);
  console.log("login2, status:", status)

  if (!status) {
    oldPasswordError.value = true;

    // 手動觸發驗證錯誤
    await nextTick();                   // 等 DOM 更新後再驗證
    oldPasswordRef.value?.validate();   // 觸發欄位的驗證規則（即在 :rules 裡的那些規則函式）
    //if (oldPasswordRef.value) {
    //  oldPasswordRef.value.validate();
    //}
  } else {
    oldPasswordError.value = false;
    newPasswordRef.value?.focus();
  }
};

const checkUsers = (focused) => {
  if (!focused) { // 當失去焦點時
    oldPasswordRef.value?.validate();
    userLogin();
  }
};

const userUpdatePassword = () => {
  validatePasswordFields();     // 輸入資料檢查

  localDialog.value = false;
  emit('update:dialog', false);

  initAxios();

  currentUser.value = JSON.parse(localStorage.getItem("loginedUser"));
  const path = '/updatePassword';
  const payload = {
    newPassword: newPassword.value,
    empID: currentUser.value.empID,
  };
  updatePassword(payload).then(status => {
    status && (console.log("update password is ok!"));
  });
};

const validatePasswordFields = () => {
  if (!newPassword.value || !confirmPpassword.value) {
    showSnackbar('所有欄位都需要填!', 'yellow lighten-5');
    return;
  }

  if (newPassword.value !== confirmPpassword.value) {
    showSnackbar('密碼與確認密碼不相符合!', 'yellow lighten-5');
    return;
  }
};
</script>

<style scoped lang="scss">
:deep(.v-input__details) {
  position: relative;
  right: 25px !important;
  width: 270px !important;
}

// padding-top = padding-bottom = (height - line-height) / 2
:deep(.v-input.custom-field .v-input__control) {
  height: 32px; // 調整高度
}

:deep(.v-input.custom-field .v-field__input) {
  padding-top: 6px;
  padding-bottom: 6px;
  line-height: 20px;
}
//

.custom-container {
  overflow-y: hidden !important;  // 禁用垂直scroll bar
}

.custom-dialog-position {
  position: fixed !important;
  top: 40px !important;
}

.custom-card {
  padding-top: 0px !important;    // 調整上內邊距離
}

.custom-img {
  margin-top: -4px;               // 移除 v-img 上缘空白
}

.custom-card-text {
  padding-top: 10px !important;   // 移除 v-card-text 上內邊距離
}

.custom-card-actions {
  //margin-top: -50px;      // 向上移動按钮位置距離

  position:relative;
  top:-85px;
}

.custom-text-field {
  margin-top: -10px;      // 向上移动文本字段位置距離
}
</style>

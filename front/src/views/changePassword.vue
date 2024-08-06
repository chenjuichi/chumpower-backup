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
      <!--
        src="https://cdn.pixabay.com/photo/2016/03/26/13/09/organic-1280537_1280.jpg"
      -->
      <v-img
        class="align-end text-white custom-img"
        height="200"
        :src="imageSrc"

        cover
      >
        <v-card-title>{{ company_name }}</v-card-title>
      </v-img>

      <v-card-subtitle class="pt-2">
        <i class="fa-solid fa-unlock-keyhole" style="color: #63E6BE;" />
        修改密碼
      </v-card-subtitle>

      <v-card-text class="custom-card-text">
        <v-container class="custom-container">
          <v-text-field
            label="新密碼"
            color="primary"
            prepend-icon="mdi-lock"
            :append-icon="eyeShow1 ? 'mdi-eye-off' : 'mdi-eye'"
            :type="eyeShow1 ? 'password' : 'text'"
            @click:append="eyeShow1 = !eyeShow1"
            v-model="newPassword"
            :rules="[requiredRule, passwordRule]"
            class="custom-text-field"
            style="width: 100% !important; max-width: 223px !important;"
          />

          <v-text-field
            label="確認密碼"
            color="primary"
            prepend-icon="mdi-account-check"
            :type="eyeShow1 ? 'password' : 'text'"
            v-model="confirmPpassword"
            :rules="[requiredRule, confirmPasswordRule]"
            class="custom-text-field"
            style="width: 100% !important; max-width: 183px !important; padding-top: 8px;"
          />
        </v-container>
      </v-card-text>
      <v-card-actions class="custom-card-actions">
        <v-spacer></v-spacer>
        <v-btn color="blue darken-1" text @click="closeDialog">取消</v-btn>
        <v-btn color="blue darken-1" text @click="userUpdatePassword" :disabled="checkDataForSaveButton">確定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</div>
</template>

<script setup>
import { ref, computed, watch, defineComponent, onMounted } from 'vue';
//import axios from 'axios';
import { myMixin } from '../mixins/common.js';

import { apiOperation, showSnackbar, snackbar, snackbar_info, snackbar_color }  from '../mixins/crud.js';
// 使用 apiOperation 函式來建立 API 請求
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
const newPassword = ref('');
const confirmPpassword = ref('');
const currentUser = ref(null);
const eyeShow1 = ref(true);

const requiredRule = value => !!value || '欄位必須輸入資料...';
const passwordRule = value => /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{6,}$/.test(value) || '需6個字以上，且含數字和小寫字母!';
const confirmPasswordRule = value => value === newPassword.value || '密碼不相同!';

//=== watch ===
watch(() => props.dialog, (newVal) => {
  localDialog.value = newVal;
});

//=== computed ===
const checkDataForSaveButton = computed(() => {
  return !(newPassword.value && confirmPpassword.value);
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
  margin-top: -50px;      // 向上移動按钮位置距離
}

.custom-text-field {
  margin-top: -10px;      // 向上移动文本字段位置距離
}
</style>

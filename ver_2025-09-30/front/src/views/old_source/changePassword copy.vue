<template>
  <v-row justify="center">
  <v-dialog v-model="dialog" persistent max-width="600px">
      <v-card>
      <v-card-title>
          <span class="text-h5">修改密碼</span>
      </v-card-title>
      <v-card-text>
          <v-container>
          <v-row>
              <v-col cols="12" md="6">
              <v-text-field
                  label="新密碼*"
                  v-model="newPassword"
                  required
                  prepend-icon="mdi-lock"
                  :append-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
                  :type="showPassword ? 'text' : 'password'"
                  class="mb-6 text-teal"
                  @click:append="toggleShowPassword"
              ></v-text-field>
              <small class='errormsg'>{{ passwordErrMsg }}</small>
              </v-col>
              <v-col cols="12" md="6" align="center" style="margin-top: 35px">
              <v-progress-linear
                  :color="score.color"
                  :value="score.value"
              ></v-progress-linear>
              </v-col>
              <v-col cols="12">
              <v-text-field
                  label="確認密碼*"
                  v-model="confirmPpassword"
                  :type="showPassword ? 'text' : 'password'"
                  required
                  prepend-icon="mdi-account-check"
                  :rules="[passwordConfirmationRule]"
              ></v-text-field>
              </v-col>
          </v-row>
          </v-container>
          <small>*indicates required field</small>
      </v-card-text>
      <v-card-actions>
          <v-spacer></v-spacer>
          <v-btn color="blue darken-1" text @click="dialog = false">取消</v-btn>
          <v-btn color="blue darken-1" text @click="save" :disabled="checkDataForSaveButton">確定</v-btn>
      </v-card-actions>
      </v-card>
  </v-dialog>
  </v-row>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import axios from 'axios';
import { zxcvbn } from '@zxcvbn-ts/core';

const dialog = ref(false);
const newPassword = ref('');
const confirmPpassword = ref('');
const showPassword = ref(false);
const passwordErrMsg = ref('');
const currentUser = ref({});
const dialog_data = ref(false);

const toggleShowPassword = () => {
showPassword.value = !showPassword.value;
};

const passwordConfirmationRule = () => (newPassword.value === confirmPpassword.value) || '密碼不相同!';

const score = computed(() => {
const result = zxcvbn(newPassword.value);
switch (result.score) {
    case 4:
    return { color: "light-blue", value: 100 };
    case 3:
    return { color: "light-green", value: 75 };
    case 2:
    return { color: "yellow", value: 50 };
    case 1:
    return { color: "orange", value: 25 };
    default:
    return { color: "red", value: 0 };
}
});

const checkDataForSaveButton = computed(() => {
return !(newPassword.value && confirmPpassword.value && passwordErrMsg.value === '');
});

const save = () => {
dialog.value = false;
currentUser.value = JSON.parse(localStorage.getItem("loginedUser"));
const path = '/updatePassword';
const payload = {
    newPassword: newPassword.value,
    empID: currentUser.value.empID,
};

axios.post(path, payload)
    .then(res => {
    console.log("update password is ok!", res.data.status);
    })
    .catch(err => {
    console.error(err);
    });
};

watch(newPassword, (val) => {
const isPasswordRule = /^(?=.*\d)(?=.*[a-z])[0-9a-zA-Z]{8,12}$/;
passwordErrMsg.value = '';
const result = val.search(isPasswordRule);
if (result !== -1) {
    passwordErrMsg.value = '';
} else {
    passwordErrMsg.value = '資料格式或資料長度錯誤!';
}
});

watch(dialog_data, (val) => {
if (val) {
    dialog.value = true;
}
});
</script>

<style scoped lang="scss">
small.errormsg {
font-size: 80%;
color: red;
position: relative;
top: -35px;
left: 35px;
}
</style>

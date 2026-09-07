<template>

  <div class="qr-mobile-page">

    <v-snackbar
      v-model="snackbar"
      location="top"
      timeout="2500"
      :color="snackbar_color"
    >
      {{ snackbar_info }}
    </v-snackbar>


    <v-card
      class="qr-mobile-card"
      elevation="6"
    >

      <v-card-title
        class="text-center title"
      >
        銓寶工業股份有限公司
      </v-card-title>


      <!-- ================================== -->
      <!-- 等待登入 -->
      <!-- ================================== -->
      <template
        v-if="
          pageStatus === 'input'
        "
      >

        <div class="phone-icon">

          <v-icon
            size="58"
            color="primary"
          >
            mdi-monitor-cellphone
          </v-icon>

        </div>


        <div class="login-message">

          工作站登入確認

        </div>


        <div class="login-description">

          請輸入您的工號與密碼，
          以允許目前電腦登入。

        </div>


        <v-card-text>

          <v-text-field
            v-model="empID"
            label="工號"
            prepend-inner-icon="
              mdi-account
            "
            inputmode="numeric"
            maxlength="8"
            autocomplete="username"
            variant="outlined"
            density="comfortable"
            :disabled="loading"
          />


          <v-text-field
            v-model="password"
            label="密碼"
            prepend-inner-icon="
              mdi-lock
            "
            :append-inner-icon="
              showPassword
                ? 'mdi-eye-off'
                : 'mdi-eye'
            "
            :type="
              showPassword
                ? 'text'
                : 'password'
            "
            autocomplete="
              current-password
            "
            variant="outlined"
            density="comfortable"
            :disabled="loading"
            @click:append-inner="
              showPassword =
                !showPassword
            "
            @keydown.enter="
              confirmLogin
            "
          />


          <v-btn
            block
            size="large"
            color="primary"
            :loading="loading"
            :disabled="
              loading ||
              !canSubmit
            "
            @click="confirmLogin"
          >

            <v-icon start>
              mdi-login
            </v-icon>

            確認登入

          </v-btn>

        </v-card-text>

      </template>


      <!-- ================================== -->
      <!-- 成功 -->
      <!-- ================================== -->
      <template
        v-else-if="
          pageStatus === 'success'
        "
      >

        <div class="result-area">

          <v-icon
            size="86"
            color="success"
          >
            mdi-check-circle
          </v-icon>


          <div class="result-title">
            登入確認完成
          </div>


          <div class="result-message">

            工作站已收到登入授權。

            <br>

            您現在可以關閉此頁面。

          </div>

        </div>

      </template>


      <!-- ================================== -->
      <!-- QR 無效 -->
      <!-- ================================== -->
      <template
        v-else
      >

        <div class="result-area">

          <v-icon
            size="86"
            color="warning"
          >
            mdi-alert-circle
          </v-icon>


          <div class="result-title">

            QR Code 無效

          </div>


          <div class="result-message">

            此 QR Code
            可能已過期或已使用。

            <br>

            請回到工作站重新產生。

          </div>

        </div>

      </template>

    </v-card>

  </div>

</template>


<script setup>

import {
  ref,
  computed,
  onMounted
} from 'vue';

import {
  useRoute
} from 'vue-router';

import {
  apiOperation
} from '../mixins/crud.js';

import {
  useSocketio
} from '../mixins/SocketioService.js';

import {
  socket_server_ip
} from '../mixins/crud.js';

import {
  snackbar,
  snackbar_info,
  snackbar_color
} from '../mixins/crud.js';


const route =
  useRoute();


// ========================================================
// API
// ========================================================

const qrLoginConfirm =
  apiOperation(
    'post',
    '/qrLogin/confirm'
  );


// ========================================================
// data
// ========================================================

const token =
  ref('');

const empID =
  ref('');

const password =
  ref('');

const showPassword =
  ref(false);

const loading =
  ref(false);

const pageStatus =
  ref('input');


// ========================================================
// Socket
// ========================================================

const userId =
  'qr_mobile';

const clientAppName =
  'QrLogin';

const {
  socket,
  setupSocketConnection
} =
  useSocketio(
    socket_server_ip.value,
    userId,
    clientAppName
  );


// ========================================================
// computed
// ========================================================

const canSubmit =
  computed(() => {

    return (
      token.value &&
      empID.value.trim() &&
      password.value
    );
  });


// ========================================================
// mounted
// ========================================================

onMounted(
  async () => {

    console.log(
      'QrLogin mounted...'
    );


    // QR Code query string
    token.value =
      String(
        route.query.t || ''
      ).trim();


    if (!token.value) {

      pageStatus.value =
        'invalid';

      return;
    }


    try {

      await setupSocketConnection();

      console.log(
        'QrLogin socket ok:',
        socket.value?.id
      );

    } catch (error) {

      console.error(
        'QrLogin socket error:',
        error
      );
    }
  }
);


// ========================================================
// method
// ========================================================

const confirmLogin =
  async () => {

    if (!canSubmit.value) {
      return;
    }

    loading.value = true;

    try {

      let tempEmpID =
        empID.value.trim();


      // 與電腦 Login 相同
      // 不滿 8 位前面補 0
      if (
        tempEmpID.length < 8
      ) {

        tempEmpID =
          tempEmpID.padStart(
            8,
            '0'
          );
      }


      const payload = {

        token:
          token.value,

        empID:
          tempEmpID,

        password:
          password.value
      };


      const data =
        await qrLoginConfirm(
          payload
        );


      console.log(
        'qrLogin/confirm:',
        data
      );


      if (
        !data ||
        data.status !== true
      ) {

        showSnackbar(
          data?.message ||
            '登入驗證失敗',
          'red accent-2'
        );

        return;
      }


      // ==============================================
      // Flask 已經把 DB 設為 approved
      //
      // Socket 只負責通知電腦：
      // 「可以去 exchange 了」
      // ==============================================
      if (
        socket.value &&
        socket.value.connected
      ) {

        socket.value.emit(
          'qr-login-approved',
          {
            token:
              token.value
          }
        );

      } else {

        showSnackbar(
          'Socket 尚未連線',
          'red accent-2'
        );

        return;
      }


      password.value = '';

      pageStatus.value =
        'success';


    } catch (error) {

      console.error(
        'confirmLogin error:',
        error
      );

      showSnackbar(
        '登入確認發生錯誤',
        'red accent-2'
      );

    } finally {

      loading.value = false;
    }
  };


const showSnackbar =
  (
    message,
    color
  ) => {

    snackbar_info.value =
      message;

    snackbar_color.value =
      color;

    snackbar.value =
      true;
  };

</script>


<style scoped>

.qr-mobile-page {

  min-height: 100vh;

  display: flex;

  align-items: center;
  justify-content: center;

  padding: 20px;

  background:
    #f5f7fa;
}


.qr-mobile-card {

  width: 100%;

  max-width: 420px;

  padding:
    20px 16px 28px;

  border-radius: 16px;
}


.title {

  font-size: 20px;

  font-weight: 700;
}


.phone-icon {

  display: flex;

  justify-content: center;

  margin-top: 24px;
}


.login-message {

  margin-top: 12px;

  text-align: center;

  font-size: 22px;

  font-weight: 700;
}


.login-description {

  padding:
    10px 25px 8px;

  text-align: center;

  font-size: 14px;

  color: #666;

  line-height: 1.6;
}


.result-area {

  min-height: 300px;

  display: flex;

  flex-direction: column;

  align-items: center;
  justify-content: center;

  text-align: center;

  padding: 30px 20px;
}


.result-title {

  margin-top: 18px;

  font-size: 23px;

  font-weight: 700;
}


.result-message {

  margin-top: 12px;

  font-size: 15px;

  line-height: 1.8;

  color: #666;
}

</style>
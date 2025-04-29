<template>
<div :class="['page_contain', { 'no-footer': !showFooter }]" :style="containerStyle" :key="componentKey">
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
    v-model="uploadDialog"
    max-width="400"
    @update:model-value="onDialogClose"
  >
    <v-card class="align-center pa-5">
      <v-card-title class="text-h6">選擇上傳類型</v-card-title>
      <v-card-text class="d-flex flex-column align-center">
        <v-radio-group v-model="uploadType" column>
          <v-radio label="上傳工單 (Excle)" value="excel" />
          <v-radio label="上傳物料清單 (PDF)" value="pdf" />
          <v-radio label="上傳領退料單 (PDF)" value="pdf1" />
        </v-radio-group>
      </v-card-text>
      <v-card-actions>
        <v-spacer />
        <v-btn color="primary" @click="cancelAndGo">取消</v-btn>
        <v-btn color="primary" @click="confirmUploadType">確定</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
  <!-- 主卡片區域 -->
  <v-card class="align-center pa-5">
    <v-card-title>
      {{ uploadTitle }}
    </v-card-title>
    <v-card-text class="d-flex flex-column align-center">
      <v-file-input
        v-model="file"
        :label="uploadType === 'excel' ? '選擇 Excel 檔案' : '選擇 PDF 檔案 (可複選, 按住Shift鍵)'"
        :accept="uploadType === 'excel' ? '.xlsx,.xls' : '.pdf'"
        :multiple="uploadType === 'pdf'"
        show-size
        prepend-icon="mdi-file-arrow-left-right"

        variant="underlined"
        style="min-width:500px; max-width:500px;"
      />
      <v-btn color="primary" @click="handleUpload">上傳</v-btn>
    </v-card-text>
  </v-card>
  <v-btn color="info" class="ma-5" @click="uploadDialog = true">開啟上傳選單</v-btn>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onUpdated , onMounted, onUnmounted, onBeforeMount, onBeforeUnmount } from 'vue';

import { useRoute } from 'vue-router';
import { useRouter } from 'vue-router';

import { myMixin } from '../mixins/common.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { apiOperationF }  from '../mixins/crudF.js';
const uploadExcelFile = apiOperationF('post', '/uploadExcelFile');
const uploadPdfFiles = apiOperationF('post', '/uploadPdfFiles');

//=== component name ==
defineComponent({ name: 'UploadXlsFile' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
const route = useRoute(); 			// Initialize router
const router = useRouter();
const currentUser = ref({});
const componentKey = ref(0)    	// key值用於強制重新渲染
const file = ref([]);         // 儲存 Excel 檔案
//const pdfFiles = ref([]);       // 以陣列儲存多個 PDF 檔案

const uploadDialog = ref(true);  // 預設先打開
const uploadType = ref('excel');

const showBackWarning = ref(true)

const pagination = reactive({
  itemsPerPage: 5, 							// 預設值, rows/per page
  page: 1,
});

//=== watch ===
//watch(currentUser, (newUser) => {
//  if (newUser.perm < 1) {
//    permDialog.value = true;
//  }
//});

//=== computed ===
const containerStyle = computed(() => ({
  bottom: props.showFooter ? '60px' : '0'
}));

const routeName = computed(() => route.name);

const uploadTitle = computed(() => {
  switch (uploadType.value) {
    case 'excel':
      return '上傳工單 (Excel)'
    case 'pdf':
      return '上傳物料清單 (PDF)'
    case 'pdf1':
      return '上傳領退料單 (PDF)'
    default:
      return '請選擇上傳類型'
  }
})

//=== mounted ===
onMounted(async () => {
  console.log("UploadXlsFile.vue, mounted()...");

  // 阻止直接後退
  window.history.pushState(null, null, document.URL); //呼叫到瀏覽器原生的 history 物件
  //history.pushState(null, null, document.URL);
  window.addEventListener('popstate', handlePopState);

  let userData = JSON.parse(localStorage.getItem('loginedUser'));
  console.log("current routeName:", routeName.value);
  console.log("current userData:", userData);

  userData.setting_items_per_page = pagination.itemsPerPage;
  userData.setting_lastRoutingName = routeName.value;
  localStorage.setItem('loginedUser', JSON.stringify(userData));

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);
});

//=== onUpdated ===
onUpdated(() => {

})

//=== unmounted ===
onUnmounted(() => {
  window.removeEventListener('popstate', handlePopState)

});

//=== created ===
onBeforeMount(() => {
  console.log("UploadXlsFile.vue, created()...", currentUser.value)

  initAxios();
  initialize();
});

onBeforeUnmount(() => {

});

//=== method ===
const initialize = async () => {
  console.log("initialize()...");

};

const onDialogClose = (val) => {
  if (!val) {
    console.log("Dialog 被關閉，導向 /main");
    uploadType.value = '';          // 可選：清空選擇
    router.push({ name: 'Main' });  // 或 path: '/main'
  }
};

const cancelAndGo = () => {
  console.log("cancelAndGo()...");

  uploadDialog.value = false
  uploadType.value = ''
  router.push({ name: 'Main' })
};
/*
const handlePopState = () => {
  // 重新添加歷史紀錄以阻止實際後退
  history.pushState(null, null, document.URL)

  // 只在第一次顯示警告
  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面内的導航按鍵', 'red accent-2');
    showBackWarning.value = false
  }
}
*/
const handlePopState = () => {
  // ✅ 正確方式：保留 Vue Router 的 state
  // history.pushState(history.state, '', document.URL)

  // 重新導向到當前頁面，強制中止「後退」行為
  //router.replace(router.currentRoute.value.fullPath)

  // 導回目前頁面（取消後退）
  router.replace(route.fullPath)

  if (showBackWarning.value) {
    showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
    showBackWarning.value = false
  }
}

const confirmUploadType = () => {
  uploadDialog.value = false;
  //file.value = null; // 清空上次選擇
  file.value = []; // 清空上次選擇
};

const handleUpload = async () => {
  //if (!file.value || (Array.isArray(file.value) && file.value.length === 0)) {
  if (!file.value || file.value.length === 0) {
      showSnackbar('請選擇檔案', 'red accent-2');
    return;
  }

  if (uploadType.value === 'excel') {
    await uploadExcelFileFun();
  } else {
    await uploadPdfFilesFun();
  }
};

const uploadExcelFileFun = async () => {
	console.log("uploadExcelFileFun()...");

  //if (!file.value) {
	//	showSnackbar('請選擇檔案', 'red accent-2');
  //  return;
  //}

  let formData = new FormData();					  //封裝表單資料，以用於上傳檔案
  formData.append('file', file.value[0]);		//將所選擇的檔案 (file.value) 加入 FormData 物件中

  // 多個檔案，要用 getlist('files') 方式處理，所以 key 要用 'files'
  //file.value.forEach((f) => {
  //  formData.append('files', f); // ✅ 注意：key 是 'files'（要配合後端 Flask）
  //});

	try {
		const response = await uploadExcelFile(formData);
		console.log("response:", response);
		//let temp_message = '檔案上傳成功: ' + response.message;
		showSnackbar(response.message, '#008184');
		//file.value = null;
		file.value = [];
  } catch (error) {
		let temp_message = 'Excel 上傳失敗: ' + (error.response.message || '未知錯誤');
		showSnackbar(temp_message, 'red accent-2');
  }
};

const uploadPdfFilesFun = async () => {
  let formData = new FormData();
  //for (let f of file.value) {
  //  formData.append('files', f);
  //}
  file.value.forEach(pdf => {
    formData.append('files', pdf); // 名稱需為 'files'
  });

  formData.append('uploadType', uploadType.value);  // 加入 uploadType

  try {
    const response = await uploadPdfFiles(formData);
    showSnackbar(response.message, '#008184');
    //file.value = null;
    file.value = [];
  } catch (error) {
    showSnackbar('PDF 上傳失敗: ' + error?.response?.message || '未知錯誤', 'red accent-2');
  }
};

const showSnackbar = (message, color) => {
  console.log("showSnackbar,", message, color)

  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

@import "../styles/variables.scss";

.page_contain {
  position: fixed;
  left: 0px !important;
  top: 60px !important;       // 確保在導航欄下方
  bottom: 60px !important;    // 確保在頁腳上方
  padding: 0px 10px;
  width: 100vw;               // 視窗寬度
  margin: 0;
  overflow-y: auto;           // 添加 scrollbar，防止內容溢出
  overflow-x: hidden;
}

.no-footer {
  margin-bottom: 0;           // 沒有頁腳時的底部邊距
}
</style>



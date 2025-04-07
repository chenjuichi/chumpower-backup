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

	<v-card class="align-center pa-5">
		<v-card-title>上傳 Excel 檔案</v-card-title>
		<v-card-text class="d-flex flex-column align-center">
			<v-file-input
				v-model="file"
				label="選擇 Excel 檔案"
				accept=".xlsx, .xls"
				show-size
				prepend-icon="mdi-file-arrow-left-right"
    		variant="filled"
				style="min-width:500px; max-width:500px;"
			/>
			<v-btn color="primary" @click="uploadExcelFileFun">上傳</v-btn>
		</v-card-text>
	</v-card>
</div>
</template>

<script setup>
import { ref, reactive, defineComponent, computed, watch, onUpdated , onMounted, onUnmounted, onBeforeMount, onBeforeUnmount } from 'vue';

import { useRoute } from 'vue-router';

import { myMixin } from '../mixins/common.js';

import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

import { apiOperationF }  from '../mixins/crudF.js';
const uploadExcelFile = apiOperationF('post', '/uploadExcelFile');

//=== component name ==
defineComponent({ name: 'UploadXlsFile' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({ showFooter: Boolean });

//=== data ===
const route = useRoute(); 			// Initialize router
const currentUser = ref({});
const componentKey = ref(0)    	// key值用於強制重新渲染
const file = ref(null);

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

//=== mounted ===
onMounted(async () => {
  console.log("UploadXlsFile.vue, mounted()...");

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

const uploadExcelFileFun = async () => {
	console.log("uploadExcelFileFun()...");

  if (!file.value) {
		showSnackbar('請選擇檔案', 'red accent-2');
    return;
  }

  let formData = new FormData();					//封裝表單資料，以用於上傳檔案
  formData.append('file', file.value);		//將所選擇的檔案 (file.value) 加入 FormData 物件中

	try {
		const response = await uploadExcelFile(formData);
		console.log("response:", response);
		//let temp_message = '檔案上傳成功: ' + response.message;
		showSnackbar(response.message, '#008184');
		file.value = null;
  } catch (error) {
		let temp_message = '上傳失敗: ' + (error.response.message || '未知錯誤');
		showSnackbar(temp_message, 'red accent-2');
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



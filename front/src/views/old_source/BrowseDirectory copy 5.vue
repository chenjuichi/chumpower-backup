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
      v-model="localPdf"
      @update:model-value="updatePdf"
      persistent max-width="600px"
      max-height="80vh"
      class="custom-dialog-position"
    >
      <v-card elevation="16" class="custom-card">
        <div>
          <h3>目錄</h3>
          <!-- 返回上一層目錄按鈕 -->
          <button @click="fetchDirectory('', true)" :disabled="currentPath === 'C:\\'" style="margin-bottom: 10px;">
            返回上一層
          </button>

          <!-- 目錄列表 -->
          <ul>
            <li v-for="item in directoryContents" :key="item.name">
              <span @click="item.is_dir ? fetchDirectory(item.name) : selectFile(item.name)" :style="{ cursor: item.is_dir ? 'pointer' : 'default' }">
                {{ item.name }}
              </span>
            </li>
          </ul>
        </div>

        <!-- 檔案選擇後，進行處理，但不顯示讀取按鈕 -->
				 <!--
        <div v-if="selectedFile && !fileReady">
          <p>檔案選擇完成，準備處理...</p>
        </div>
				-->
        <!-- 檔案處理後，顯示檔案名稱但不顯示 <textarea /> 或插入條碼按鈕 -->
        <div v-if="selectedFile && fileReady">
          <!-- 已選擇檔案顯示 -->
					 <!--
          <h3>已選擇檔案：{{ selectedFile }}</h3>
					-->
          <!-- 不顯示「讀取檔案」按鈕，直接讀取檔案 -->
          <button @click="readFileFun" v-if="!fileContent && !isReadingFile">讀取檔案</button>

          <!-- 讀取檔案後，不顯示 <textarea /> 和插入條碼按鈕，但插入條碼 -->
          <div v-if="fileContent && !showTextarea">
            <textarea readonly :value="fileContent" rows="10" cols="50"></textarea>
          </div>

          <!-- 顯示條碼並插入，但不顯示插入條碼按鈕 -->
          <div v-if="barcodeText && !showBarcodeButton">
            <vue3-barcode :value="barcodeText" format="CODE128" height=50 :text="barcodeText" />
          </div>

          <!-- 這裡是控制"另存新檔"按鈕顯示 -->
					<!--
          <button @click="saveFileFun" v-if="fileContent && barcodeText">另存新檔</button>
					-->
        </div>

      </v-card>
    </v-dialog>
  </div>
</template>

<script setup>
import { ref, defineComponent, onBeforeMount, onMounted, watchEffect } from 'vue';

import Vue3Barcode from 'vue3-barcode';

import { myMixin } from '../mixins/common.js';

import { apiOperation } from '../mixins/crud.js';

const listDirectory = apiOperation('post', '/listDirectory');
const readFile = apiOperation('post', '/readFile');
const saveFile = apiOperation('post', '/saveFile');

// === component name ==
defineComponent({
  name: 'BrowseDirectory'
});

// === mix ==
const { initAxios } = myMixin();

//=== props ===
const props = defineProps({
	pdf: {
		type: Boolean,
		required: true
	}
});

// === emits ===
const emit = defineEmits(['update:pdf']);

// === data ===
const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2'); // default: 'red accent-2'
const localPdf = ref(false);

const fileReady = ref(false); // 用來控制是否準備顯示 "另存新檔" 按鈕
const selectedFile = ref(null); // 儲存已選擇檔案的名稱
const fileContent = ref(''); // 儲存檔案內容
const barcodeText = ref(''); // 儲存條碼內容
const isReadingFile = ref(false); // 用來控制讀取檔案的狀態，避免重複讀取
const showTextarea = ref(false); // 用來控制是否顯示 <textarea />
const showBarcodeButton = ref(false); // 用來控制是否顯示條碼插入按鈕

const currentPath = ref('C:\\vue\\chumpower\\pdf_file'); // 初始路徑
const directoryContents = ref([]); // 儲存目錄內容

//=== mounted ===
onMounted(() => {
	console.log("BrowseDirectory, mounted()...");

	// 自動追蹤callBack裡的響應式數據, bgColor.value
	watchEffect(() => (localPdf.value = props.pdf));
});

//=== created ===
onBeforeMount(() => {
	console.log("BrowseDirectory, created()...")

	initAxios();
	initialize();
});

// === methods ===
const initialize = () => {
	console.log("initialize()...")

	fetchDirectory();
};

const selectFile = (fileName) => {
  let fileNameWithoutExtension = fileName.split('.').slice(0, -1).join('.');
  selectedFile.value = fileName; // 保留完整檔案名稱
  barcodeText.value = fileNameWithoutExtension; // 設置條碼文字為去除副檔名的名稱
  fileReady.value = true; // 設置檔案準備好
  isReadingFile.value = true; // 開始讀取檔案

	// 檔案選擇後直接觸發 readFileFun 讀取檔案
  readFileFun();
};

const fetchDirectory = async (subDirectory = '', goUp = false) => {
  let payload = {};

  if (goUp) {
    const pathParts = currentPath.value.split('\\');
    pathParts.pop(); // 移除最後一部分
    currentPath.value = pathParts.join('\\') || 'C:\\'; // 確保不會為空
  } else if (subDirectory) {
    currentPath.value = `${currentPath.value}\\${subDirectory}`;
  }

  payload.path = currentPath.value;

  try {
    directoryContents.value = await listDirectory(payload);
  } catch (error) {
    showSnackbar('路徑錯誤 或 沒有檔案！', 'red accent-2');
    console.error('路徑錯誤 或 沒有檔案:', error);
  }
};

const readFileFun = async () => {
	console.log("readFileFun()...")

  let payload = { filepath: `${currentPath.value}\\${selectedFile.value}` };

  try {
    fileContent.value = await readFile(payload);
    const fileNameWithoutExtension = selectedFile.value.split('.').slice(0, -1).join('.');
    barcodeText.value = fileNameWithoutExtension;
		console.log("readFileFun, step1...")
    // 設置顯示條碼，並自動插入條碼
    showTextarea.value = true; // 顯示 <textarea />
    showBarcodeButton.value = true; // 顯示插入條碼按鈕

		// 自動儲存檔案
		saveFileFun();
  } catch (error) {
    showSnackbar('檔案讀取錯誤！', 'red accent-2');
    console.error('檔案讀取錯誤:', error);
  }
};

const saveFileFun = async () => {
  const payload = {
    filepath: `${currentPath.value}\\${selectedFile.value}`,
    updated_content: fileContent.value,
    barcode_text: barcodeText.value,
  };

  try {
    const response = await saveFile(payload);

		// 關閉對話框
		localPdf.value = false;

    if (response instanceof Blob) {
      const url = window.URL.createObjectURL(response);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `NEW_${selectedFile.value}`);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

			// 關閉對話框
			localPdf.value = false
    }
  } catch (error) {
    console.error('保存檔案失敗:', error);
  }
};

const updatePdf = (value) => {
	localPdf.value = value;
	if (!value) {
		emit('update:pdf', false);
	}
};

const showSnackbar = (message, color) => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');
</style>

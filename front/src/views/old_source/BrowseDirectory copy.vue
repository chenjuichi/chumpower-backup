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
      <h2>目錄瀏覽</h2>
      <ul>
        <li v-for="item in directory" :key="item.name">
          <span @click="item.isDirectory ? browseDirectory(item.name) : selectFile(item.name)">
            {{ item.name }} {{ item.isDirectory ? '(資料夾)' : '' }}
          </span>
        </li>
      </ul>

      <h3 v-if="selectedFile">選取的檔案：{{ selectedFile }}</h3>
      <button v-if="selectedFile" @click="fetchFileContent">讀取檔案內容</button>

      <iframe v-if="fileContent" :src="fileContent" width="100%" height="500px"></iframe>
		</v-card>
	</v-dialog>
</div>
</template>

<script setup>
import { ref, computed, watch, defineComponent, onMounted, onBeforeMount } from 'vue';
import axios from 'axios';
import { nodeMixin } from '../mixins/common.js';

//=== component name ==
defineComponent({
  name: 'BrowseDirectory'
});

// === mix ==
const { initAxios } = nodeMixin();

//=== props ===
const props = defineProps({
  pdf: {
    type: Boolean,
    required: true
  }
});

// === emits ===
const emit = defineEmits(['update:pdf']);

//=== data ===
const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

const localPdf = ref(props.pdf);

const directory = ref([]);
const currentPath = ref('');
const selectedFile = ref('');
const fileContent = ref('');

//=== created ===
onBeforeMount(() => {
  console.log("BrowseDirectory, created()...")

  initAxios();
	initialize();
});

//=== method ===
const initialize = () => {
  console.log("initialize()...")

  browseDirectory('');
};

const updatePdf = (value) => {
  localPdf.value = value;
  if (!value) {
    emit('update:pdf', false);
  }
};

const closeDialog = () => {
  localPdf.value = false;
  emit('update:pdf', false);
};

// 瀏覽目錄或磁碟機
const browseDirectory = async (folderName) => {
	currentPath.value = currentPath.value ? `${currentPath.value}\\${folderName}` : folderName;
	const path = '/list-directory';
	try {
		const response = await axios.get(path, {
      params: { path: currentPath.value },
    })
		directory.value = response.data;
	} catch (error) {
		showSnackbar('無法讀取目錄！', 'red accent-2');
		console.error('無法讀取目錄:', error);
	}
};

// 選擇檔案
const selectFile = (fileName) => {
	selectedFile.value = `${currentPath.value}\\${fileName}`;
};

// 讀取檔案內容
const fetchFileContent = async () => {
	const path = '/read-file';
	try {
		// 若已存在舊的 Blob URL，則釋放
		if (fileContent.value) {
			URL.revokeObjectURL(fileContent.value);
    }
		const response = await axios.get(path, {
			params: { path: selectedFile.value },
			responseType: 'blob', 									// 確保以二進制流接收
		})
		fileContent.value = URL.createObjectURL(response.data); 	// 生成 Blob URL
	} catch (error) {
		showSnackbar('無法讀取檔案！', 'red accent-2');
		console.error('無法讀取檔案:', error);
	}
};

const showSnackbar = (message, color) => {
	//if (debounceTimeout) {
	//  clearTimeout(debounceTimeout);
	//}

	//debounceTimeout = setTimeout(() => {
		snackbar_info.value = message;
		snackbar_color.value = color;
		snackbar.value = true;
	//}, 100); // 防止短時間內重複觸發
};

</script>

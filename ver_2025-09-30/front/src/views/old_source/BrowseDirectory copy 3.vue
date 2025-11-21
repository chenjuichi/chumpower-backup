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
				<button
					@click="fetchDirectory('', true)"
					:disabled="currentPath === 'C:\\'"
					style="margin-bottom: 10px;">
					返回上一層
				</button>

				<!-- 目錄列表 -->
				<ul>
					<li v-for="item in directoryContents" :key="item.name">
						<span
							@click="item.is_dir ? fetchDirectory(item.name) : selectFile(item.name)"
							:style="{ cursor: item.is_dir ? 'pointer' : 'default' }">
							{{ item.name }}
						</span>
					</li>
				</ul>
			</div>

			<div v-if="selectedFile">
				<h3>已選擇檔案：{{ selectedFile }}</h3>
				<button @click="readFileFun">讀取檔案</button>
				<div v-if="fileContent">
					<textarea readonly :value="fileContent" rows="10" cols="50"></textarea>
				</div>
				<div>
					<vue3-barcode :value="barcodeText" format="CODE128" height=50  :text="barcodeText" />
				</div>
				<button @click="saveFileFun">另存新檔</button>
			</div>

			</v-card>
		</v-dialog>
	</div>
	</template>

	<script setup>
	import { ref, defineComponent, onBeforeMount, onMounted, watchEffect } from 'vue';
	//import VueBarcode from '@vueup/vue-barcode';
	//import VueBarcode from 'vue-barcode';
	import Vue3Barcode from 'vue3-barcode'
	import { myMixin } from '../mixins/common.js';
	import { apiOperation }  from '../mixins/crud.js';
	const listDirectory = apiOperation('post', '/listDirectory');
	const readFile = apiOperation('post', '/readFile');
	const saveFile = apiOperation('post', '/saveFile');


	//=== component name ==
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

	//=== data ===
	const snackbar = ref(false);
	const snackbar_info = ref('');
	const snackbar_color = ref('red accent-2');   // default: 'red accent-2'

	const localPdf = ref(false);


	const currentPath = ref('C:\\vue\\chumpower\\pdf_file'); // 初始路徑
	const directoryContents = ref([]); // 儲存目錄內容
	const selectedFile = ref(null); // 儲存已選擇檔案的名稱
	const fileContent = ref(''); // 儲存檔案內容
	const barcodeText = ref(''); // 儲存條碼內容

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

	//=== method ===
	const initialize = () => {
		console.log("initialize()...")

		fetchDirectory();
	};

	const selectFile = (fileName) => {
		// 取檔案名稱，不包含副檔名
		let fileNameWithoutExtension = fileName.split('.').slice(0, -1).join('.');
		selectedFile.value = fileName; // 保留完整檔案名稱
		barcodeText.value = fileNameWithoutExtension; // 設置條碼文字為去除副檔名的名稱
	};

	const fetchDirectory = async (subDirectory = '', goUp = false) => {
			let payload = {};

			// 計算目標路徑
			if (goUp) {
					// 回上一層：移除當前路徑的最後一節
					const pathParts = currentPath.value.split('\\');
					pathParts.pop(); // 移除最後一部分
					currentPath.value = pathParts.join('\\') || 'C:\\'; // 確保不會為空
			} else if (subDirectory) {
					// 進入子目錄：拼接子目錄
					currentPath.value = `${currentPath.value}\\${subDirectory}`;
			}

			// 更新 payload
			payload.path = currentPath.value;

			try {
					// 請求新目錄內容
					directoryContents.value = await listDirectory(payload);
			} catch (error) {
					showSnackbar('路徑錯誤 或 沒有檔案！', 'red accent-2');
					console.error('路徑錯誤 或 沒有檔案:', error);
			}
	};

	const readFileFun = async () => {
		console.log("readFileFun(), selectedFile:",selectedFile.value)

		let payload = {
			filepath: `${currentPath.value}\\${selectedFile.value}`, // 拼接完整路徑
		}
		try {
			fileContent.value = await readFile(payload);
			barcodeText.value = selectedFile.value;
	} catch (error) {
			showSnackbar('檔案讀取錯誤！', 'red accent-2');
			console.error('檔案讀取錯誤:', error);
		}
	};

	const saveFileFun = async () => {
			// 確保代碼只在瀏覽器環境中執行
			if (typeof window === 'undefined' || !document) {
					console.error('This code is running outside of the browser!');
					return;
			}
			//console.error('saveFileFun(), selectedFile, barcodeText:',selectedFile.value, barcodeText.value);
			let fileNameWithoutExtension = selectedFile.value.split('.').slice(0, -1).join('.');
			barcodeText.value = fileNameWithoutExtension; // 設置條碼文字為去除副檔名的名稱
			//console.error('saveFileFun(), barcodeText:', barcodeText.value);

			let payload = {
				filepath: `${currentPath.value}\\${selectedFile.value}`, // 拼接完整路徑,
				barcode_text: barcodeText.value,
			};

			try {
					const response = await saveFile(payload); // 從後端獲取文件

					// 檢查返回的資料是否為 Blob 類型
					if (response instanceof Blob) {
							// 生成下載鏈接
							const url = window.URL.createObjectURL(response); // 使用 Blob 生成 URL
							const link = document.createElement('a');
							link.href = url;
							link.setAttribute('download', `NEW_${selectedFile.value}`); // 使用動態檔案名稱
							document.body.appendChild(link);
							link.click();
							document.body.removeChild(link);
					} else {
							console.error('Response is not a Blob.');
					}

			} catch (error) {
					showSnackbar('新增檔案失敗！', 'red accent-2');
					console.error('新增檔案失敗:', error);
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
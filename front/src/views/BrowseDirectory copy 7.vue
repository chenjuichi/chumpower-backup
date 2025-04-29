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
		@update:modelValue="updatePdf"
		persistent max-width="600px"
		max-height="80vh"
		class="custom-dialog-position"
	>
		<v-card elevation="16" class="pt-0">
			<v-img class="align-end text-white custom-img" height="200" :src="imageSrc" cover>
				<v-card-title>{{ company_name }}</v-card-title>
			</v-img>
			<v-card-subtitle
				class="pt-2"
				style="font-weight: 700; font-family: '微軟正黑體', sans-serif;">
				<i class="fa-solid fa-paste" style="color: #63E6BE;" />
				表單貼條碼&nbsp;&nbsp;&nbsp;
				<i class="fa-solid fa-folder-tree"style="color:#3F51B5;"></i>
				{{ currentPath }}
			</v-card-subtitle>

			<v-card-text class="custom-card-text" ref="scrollContainer">
					<v-container class="custom-container">
						<div>
							<div
								style="position:relative; top:5px; left:50px; display:flex; align-items:center; gap:10px; font-size:16px; font-weight:700; color:#3F51B5; font-family:'微軟正黑體', sans-serif;">
								<span>補日期章</span>
								<v-radio-group v-model="stampYesNo" inline style="right:270px; position:relative;">
									<v-radio label="yes" :value="1" />
									<v-radio label="no" :value="0" />
								</v-radio-group>
							</div>

							<!-- 返回上一層目錄按鈕 -->
							<button
								@click="fetchDirectory('', true)"
								v-if="currentPath !== 'C:\\vue\\chumpower\\pdf_file'"
								style="margin-bottom: 10px; font-size: 16px; font-weight: 700; color:#3F51B5; font-family: '微軟正黑體', sans-serif;">
								返回上一層
							</button>
							<!-- 目錄列表 -->
							<ul>
								<li v-for="item in directoryContents" :key="item.name">
									<span
										@click="handleItemClick(item)"

										:style="{
											cursor: item.is_dir ? 'pointer' : 'default',
											color: selectedFileName === item.name ? '#3F51B5' : 'inherit',
											fontWeight: selectedFileName === item.name ? '700' : 'normal'
										}"
									>
										{{ item.name }}<span v-if="item.is_dir" style="font-weight: 700; color:#3F51B5;"> (+)</span>
									</span>
								</li>
							</ul>
						</div>

						<!-- 檔案處理後，顯示檔案名稱但不顯示 <textarea /> 或插入條碼按鈕 -->
						<div v-if="selectedFile && fileReady">

							<!-- 不顯示「讀取檔案」按鈕，直接讀取檔案 -->
							<!--
							<button @click="readFileFun" v-if="!fileContent && !isReadingFile">讀取檔案</button>
							-->

							<!-- 讀取檔案後，不顯示 <textarea /> -->
							<div v-if="fileContent && !showTextarea">
								<textarea readonly :value="fileContent" rows="10" cols="50" />
							</div>

							<!-- 顯示條碼並插入，但不顯示插入條碼按鈕 -->
							<div v-if="barcodeText && !showBarcodeButton">
								<vue3-barcode :value="barcodeText" format="CODE128" height=50 :text="barcodeText" />
							</div>
						</div>
					</v-container>

			</v-card-text>

			<v-card-actions>
				<v-spacer></v-spacer>
				<v-btn color="blue darken-1" text @click="closeDialog">取消</v-btn>
				<v-btn color="blue darken-1" text @click="createNewPdf" :disabled="checkDataForSaveButton">確定</v-btn>
			</v-card-actions>
		</v-card>
	</v-dialog>
</div>
</template>

<script setup>
import { ref, defineComponent, onBeforeMount, onMounted, watchEffect, computed, watch, nextTick } from 'vue';

import Vue3Barcode from 'vue3-barcode';

import { myMixin } from '../mixins/common.js';
import { apiOperation } from '../mixins/crud.js';
import { apiOperationB } from '../mixins/crudB.js';

const listDirectory = apiOperation('post', '/listDirectory');
const readFile = apiOperation('post', '/readFile');
const saveFile = apiOperationB('post', '/saveFile');
const stampFile = apiOperationB('post', '/stampFile');
const downloadFile = apiOperationB('post', '/downloadFile');

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
const company_name = ref('銓寶工業股份有限公司')
const imageSrc = ref(require('../assets/organic-1280537_1280.jpg')); //企業視覺圖像

const snackbar = ref(false);
const snackbar_info = ref('');
const snackbar_color = ref('red accent-2');

const localPdf = ref(false);								//	on/off dialog
const scrollContainer = ref(null);					// 引用滾動內容區域

const pdfType=ref(1);												// radio button 預設值
const fileReady = ref(false); 							// 用來控制是否準備顯示 "另存新檔" 按鈕
const stampYesNo=ref(0);										// 1:補日期章, 0:no

const selectedFile = ref(null); 						// 儲存已選擇檔案的名稱
const selectedFileName = ref('');						// 用於追蹤目前選取的檔案名稱

const fileContent = ref(''); 								// 儲存檔案內容
const barcodeText = ref(''); 								// 儲存條碼內容
const isReadingFile = ref(false); 					// 用來控制讀取檔案的狀態，避免重複讀取
const showTextarea = ref(false); 						// 用來控制是否顯示 <textarea />
const showBarcodeButton = ref(false); 			// 用來控制是否顯示條碼插入按鈕

const currentPath = ref('C:\\vue\\chumpower\\pdf_file'); 	// 初始路徑
const topPath = ref('C:\\vue\\chumpower\\pdf_file'); 	// 初始路徑
const directoryContents = ref([]); 												// 儲存目錄內容

const currentUser = ref({});

//=== mounted ===
onMounted(() => {
	console.log("BrowseDirectory, mounted()...");

	console.log("scrollContainer:", scrollContainer.value); // 應為非 null

	// 自動追蹤callBack裡的響應式數據, localPdf
	watchEffect(() => (localPdf.value = props.pdf));

	let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);
});

//=== created ===
onBeforeMount(() => {
	console.log("BrowseDirectory, created()...")

	initAxios();
	initialize();
});

//=== computed ===
const checkDataForSaveButton = computed(() => {
  return !(fileReady.value);
});
/*
const splitName = computed(() => {
	console.log("currentUser.value.name:", currentUser.value.name)
	if (!currentUser.value.name) return { last_name: '', first_name: '' };
	// 處理4字姓名：假設是複姓(2字)+名字(2字)
	if (currentUser.value.name.length === 4) {
		return {
			last_name: currentUser.value.name.substring(0, 2),
			first_name: currentUser.value.name.slice(2, 4)
		};
	}
	// 處理3字姓名
	if (currentUser.value.name.length === 3) {
		return {
			last_name: currentUser.value.name.substring(0, 1),
			first_name: currentUser.value.name.substring(1, 3)
		};
	}
	// 默認處理2字姓名
	return {
		last_name: currentUser.value.name.substring(0, 1),
		first_name: currentUser.value.name.substring(1, 2) || '' // 防止單字姓名時 undefined
	};
});
*/
//=== watch ===
/*
watch(localPdf, (value) => {
	if (value) {
		scrollToBottom()
	}
});
*/
watch(localPdf, async (value) => {
  if (value) {
    console.log("Dialog opened, scrolling to bottom...");
    await nextTick(); // 確保 DOM 更新完成
    scrollToBottom();
  }
});

// === methods ===
const initialize = () => {
	console.log("initialize()...")

	//currentPath.value = 'C:\\vue\\chumpower\\pdf_file'; 	// 初始路徑

	fetchDirectory();
};

// 滾動到底部
const scrollToBottom = () => {
  nextTick(() => {
    // 检查 scrollContainer 是否已被绑定
    if (scrollContainer.value) {
      const target = scrollContainer.value.$el; // 获取实际的 DOM 元素
      if (target) {
        console.log("scrollContainer:", target);
        console.log("scrollHeight:", target.scrollHeight);
        console.log("clientHeight:", target.clientHeight);
        target.scrollTop = target.scrollHeight; // 滚动到底部
      } else {
        console.error("scrollContainer is still null");
      }
    } else {
      console.error("scrollContainer is null or undefined");
    }
  });
};

const createNewPdf = () => {
	console.log("createNewPdf()...")

  isReadingFile.value = true; 	// 開始讀取檔案
  readFileFun();								// 檔案選擇後直接觸發 readFileFun 讀取檔案
	//selectedFile.value = null;
	fileReady.value = false;
	selectedFileName.value = '';

	//if (showTextarea.value && showBarcodeButton.value) {
	//	saveFileFun();		// 讀取檔案
	//} else {
	//	localPdf.value = false;
	//	emit('update:pdf', false);
	//}
};

const selectFile = (fileName) => {
	console.log("selectFile(), fileName:", fileName);

	if (fileName != undefined) {
		let fileNameWithoutExtension = fileName.split('.').slice(0, -1).join('.');
		selectedFile.value = fileName; 								// 保留完整檔案名稱
		barcodeText.value = fileNameWithoutExtension; // 設置條碼文字為去除副檔名的名稱
		fileReady.value = true; 											// 設置檔案準備好

		selectedFileName.value = fileName;						// 更新選取的檔案名稱
	}
  //isReadingFile.value = true; 									// 開始讀取檔案
	//readFileFun();	// 檔案選擇後直接觸發 readFileFun 讀取檔案
};

const handleItemClick = (item) => {
  // 設定 pdfType
  if (item.name === '物料清單') {
    pdfType.value = 1;
  } else if (item.name === '領退料單') {
    pdfType.value = 2;
  } else {
    pdfType.value = 0;
  }

  // 根據是否為資料夾來執行對應的動作
  if (item.is_dir) {
    fetchDirectory(item.name);
  } else {
    selectFile(item.name);
  }
};

const fetchDirectory = async (subDirectory = '', goUp = false) => {
	console.log("fetchDirectory()...")

  if (goUp) {
    const pathParts = currentPath.value.split('\\');
    pathParts.pop(); // 移除最後一部分
    //currentPath.value = pathParts.join('\\') || 'C:\\'; // 確保不會為空
    currentPath.value = pathParts.join('\\') || topPath; // 確保不會為空
  } else if (subDirectory) {
    currentPath.value = `${currentPath.value}\\${subDirectory}`;
  }

	let payload = {
		path: currentPath.value,
	}

  try {
    directoryContents.value = await listDirectory(payload);

		//selectedFile.value = null;
		fileReady.value = false;
		selectedFileName.value = '';
  } catch (error) {
    showSnackbar('路徑錯誤 或 沒有檔案！', 'red accent-2');
    console.error('路徑錯誤 或 沒有檔案:', error);
  }
};

const readFileFun = async () => {
	console.log("readFileFun()...")

	showTextarea.value = false;
  showBarcodeButton.value = false;

  let payload = {
		filepath: `${currentPath.value}\\${selectedFile.value}`
	};

  try {
		console.log("readFileFun step1...")
    //fileContent.value = await readFile(payload);
    await readFile(payload);
		//console.log("selectedFile.value:", selectedFile.value);
		//console.log("readFileFun step2...")
    const fileNameWithoutExtension = selectedFile.value.split('.').slice(0, -1).join('.');
		//console.log("readFileFun step3...")
    barcodeText.value = fileNameWithoutExtension;

    // 設置顯示條碼，並自動插入條碼
    showTextarea.value = true; 			// 顯示 <textarea />
    showBarcodeButton.value = true; // 顯示插入條碼按鈕

		await saveFileFun();
  } catch (error) {
    showSnackbar('讀取檔案錯誤！', 'red accent-2');
    console.error('讀取檔案錯誤:', error);
  }
};
/*
const downloadFileFun = async () => {
	console.log("downloadFileFun()...")

  const payload = {
    filepath: `${currentPath.value}\\${selectedFile.value}`,
  };

  try {
    await downloadFile(payload);
    console.log('文件下載完成');
  } catch (error) {
    showSnackbar('下載檔案錯誤！', 'red accent-2');
    console.error('下載檔案錯誤:', error);
  }
};
*/
const downloadFileFun = async () => {
	console.log("downloadFileFun()...")

	const payload = {
		filepath: `${topPath.value}\\NEW_${selectedFile.value}`,
	};

	try {
		const response = await downloadFile(payload);

		//console.log("response:", response);
		console.log("Response data:", response.data); // 確認是否為 Blob檔案型式

		selectedFileName.value = null;

		if (response.data instanceof Blob) {
			const fileName = response.headers['x-file-name'] || `NEW_${selectedFile.value}`;
      console.log('下載的檔案名稱:', fileName);
			//const fileName = `NEW_${selectedFile.value}`;
      //console.log('下載的檔案名稱:', fileName);

			//// 從回應標頭中提取檔案名稱
			//const contentDisposition = response.headers['content-disposition'];
			////let fileName = 'downloaded_file.pdf';
			//if (contentDisposition) {
			//	const matches = contentDisposition.match(/filename="(.+?)"/);
			//	if (matches) fileName = matches[1];
			//}

			// 建立下載鏈結並觸發下載
      const url = window.URL.createObjectURL(response.data);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', fileName);
      link.style.display = 'none';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
			return true; 													// 成功下載
    } else {
      console.error("回傳資料不是 Blob");
			return null;
    }
  } catch (error) {
    showSnackbar('下載檔案錯誤！', 'red accent-2');
    console.error('下載檔案錯誤:', error);
  }
};

const saveFileFun = async () => {
	console.log("saveFileFun()...")

	const positionMapping = {
		1: { x: 120, y: 880 },
		2: { x: 80, y: 500 },
	};
	const position = positionMapping[pdfType.value] || { x: 0, y: 0 }; // 預設值 {x: 0, y: 0}
	console.log("position:", pdfType.value, position)

  const payload = {
    filepath: `${currentPath.value}\\${selectedFile.value}`,
    updated_content: fileContent.value,
    barcode_text: barcodeText.value,
		pdfType: pdfType.value,
  };

	try {
		await saveFile(payload);				// 儲存檔案(server端)
		console.log('儲存檔案完成');

		//localPdf.value = false;
		if (stampYesNo.value == 1) {
			await stampFileFun();						//列印日期及姓名橡皮章
		}
	} catch (error) {
		showSnackbar('儲存檔案錯誤！', 'red accent-2');
		console.error('儲存檔案錯誤:', error);
	}
	//emit('update:pdf', false);
};

const stampFileFun = async () => {
	console.log("stampFileFun()...")

	const positionMapping = {
	 x: 0, y: 0
	};

	const position = positionMapping || { x: 0, y: 0 };

	console.log("日期章:");
	console.log("position:", position);
	console.log("currentPath:", currentPath.value);
	console.log("selectedFile:", selectedFile.value);
	console.log(`${currentPath.value}\\${selectedFile.value}`);
	console.log("currentUser.value.name:", currentUser.value.name);

	let temp_f='';
	let temp_l='';

	// 處理4字姓名：假設是複姓(2字)+名字(2字)
	if (currentUser.value.name.length == 4) {
		temp_l= currentUser.value.name.substring(0, 2);
		temp_f= currentUser.value.name.slice(2, 4);
	}
	// 處理3字姓名
	if (currentUser.value.name.length == 3) {
		temp_l= currentUser.value.name.substring(0, 1);
		temp_f= currentUser.value.name.substring(1, 3);
	}
	// 默認處理2字姓名
	if (currentUser.value.name.length == 2) {
		temp_l= '';
		temp_f= currentUser.value.name.substring(0, 2);
	}
	// 默認處理1字姓名
	if (currentUser.value.name.length == 1) {
		temp_l= '';
		temp_f= currentUser.value.name.substring(0, 1);
	}

	console.log("last, first name:", temp_l, temp_f);

	const payload = {
		last_name: temp_l,
		first_name: temp_f,
    filepath: `${currentPath.value}\\${selectedFile.value}`,
    updated_content: fileContent.value,
    //png_path: "C:\\vue\\chumpower\\pdf_file\\日期章\\stamp0.png",
    png_path: "C:\\vue\\chumpower\\日期章\\stamp0.png",
    //png_path: "C:\\vue\\chumpower\\pdf_file\\processed_image.png",
		//pdfType: pdfType.value,
  };

	//if (stampYesNo.value == 1) {
		try {

			await stampFile(payload);				// 儲存檔案(server端)
			console.log('日期印章檔案完成');

			//localPdf.value = false;
			await downloadFileFun();				// 下載檔案(client端)
		} catch (error) {
			showSnackbar('日期印章檔案錯誤！', 'red accent-2');
			console.error('日期印章檔案錯誤:', error);
		}
	//}
	//emit('update:pdf', false);
};

const updatePdf = (value) => {
	localPdf.value = value;
	if (!value) {
		emit('update:pdf', false);
	}
};

const closeDialog = () => {
	selectedFile.value = null;
	fileReady.value = false;
	selectedFileName.value = '';

  localPdf.value = false;
	emit('update:pdf', false);
};

const showSnackbar = (message, color) => {
  snackbar_info.value = message;
  snackbar_color.value = color;
  snackbar.value = true;
};
</script>

<style lang="scss" scoped>
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

.custom-dialog-position {
  position: fixed !important;
  top: 40px !important;
	//overflow-y: auto; 	// 確保對話框有滾動條
}

// 調整上內邊距離
//.custom-card {
//  padding-top: 0px !important;
//}

// 移除 v-img 上缘空白
.custom-img {
  margin-top: -4px;
}

// 移除 v-card-text 上內邊距離
.custom-card-text {
  padding-top: 10px !important;

	max-height: 60vh; 	// 限制文字區域高度以啟用滾動條
  overflow-y: auto;
}

// 禁用垂直scroll bar
.custom-container {
  overflow-y: hidden !important;
  overflow-x: hidden !important;
}

// 設定 radio button位置及對其方式
:deep(.v-input__control) {
	align-items: end;
	margin-top: 24px;
  margin-right: 24px;
}
</style>

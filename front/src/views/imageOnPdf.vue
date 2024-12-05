<template>
	<div>
		<!-- 使用 <v-text-field /> 作為 PDF 檔案名稱的輸入框 -->
		<v-text-field
			v-model="pdfFileName"
			label="請輸入 PDF 檔案名稱"
			outlined
			clearable
		/>

		<!-- PDF 和 Excel 檔案選擇按鈕 -->
		<v-file-input
			label="選擇 PDF 檔案"
			@change="onPdfSelect"
			accept=".pdf"
			prepend-icon="mdi-file-pdf-box"
			outlined
		/>
		<v-file-input
			label="選擇 Excel 檔案"
			@change="onExcelSelect"
			accept=".xlsx"
			prepend-icon="mdi-file-excel-box"
			outlined
		/>

		<!-- PDF 預覽 -->
		<div v-if="pdfBlob">
			<iframe :src="pdfBlob" width="600" height="800"></iframe>
		</div>

		<!-- 儲存按鈕 -->
		<v-btn @click="savePdf" :disabled="!pdfLoaded || !barcodeImage" color="primary">
			儲存修改後的 PDF
		</v-btn>
	</div>
</template>

<script setup>
import { ref } from 'vue'
import { PDFDocument } from 'pdf-lib'
import * as XLSX from 'xlsx'
import { saveAs } from 'file-saver'

const pdfFileName = ref('')
const pdfBlob = ref(null)
const pdfLoaded = ref(false)
const barcodeImage = ref(null)
const pdfDoc = ref(null)

// 處理 PDF 檔案選擇
async function onPdfSelect(file) {
	if (file) {
		const arrayBuffer = await file.arrayBuffer()
		pdfDoc.value = await PDFDocument.load(arrayBuffer)
		pdfLoaded.value = true
		renderPdf()  // 預覽載入的 PDF
	}
}

// 處理 Excel 檔案選擇
async function onExcelSelect(file) {
	if (file) {
		const arrayBuffer = await file.arrayBuffer()
		const workbook = XLSX.read(arrayBuffer, { type: 'array' })

		// 指定讀取 "工作表1" 工作表，並從 A3 儲存格讀取條碼資料
		const worksheet = workbook.Sheets['工作表1']
		const barcodeData = worksheet['A3']?.v
		if (barcodeData) {
			// 轉換條碼資料為 Image
			barcodeImage.value = new Image()
			barcodeImage.value.src = `data:image/jpeg;base64,${barcodeData}`
		}
	}
}

// 顯示並插入圖片到 PDF
async function renderPdf() {
	if (pdfDoc.value && barcodeImage.value) {
		const page = pdfDoc.value.getPages()[0]
		const { width, height } = page.getSize()

		// 讀取條碼圖片
		const barcodeBytes = await fetch(barcodeImage.value.src).then(res => res.arrayBuffer())
		const barcodeEmbed = await pdfDoc.value.embedJpg(barcodeBytes)

		// 將條碼圖片加入到 PDF 的右上角
		page.drawImage(barcodeEmbed, {
			x: width - barcodeEmbed.width - 50,
			y: height - barcodeEmbed.height - 100,
			width: 100, // 可根據需求調整大小
			height: 50,
		})

		// 顯示修改後的 PDF
		const pdfBytes = await pdfDoc.value.save()
		pdfBlob.value = URL.createObjectURL(new Blob([pdfBytes], { type: 'application/pdf' }))
	}
}

// 儲存修改後的 PDF
async function savePdf() {
	if (pdfDoc.value) {
		const pdfBytes = await pdfDoc.value.save()
		const blob = new Blob([pdfBytes], { type: 'application/pdf' })
		saveAs(blob, pdfFileName.value || 'modified.pdf')
	}
}
</script>

<style lang="scss" scoped>

</style>

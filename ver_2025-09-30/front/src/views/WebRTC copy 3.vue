<template>
	<div class="floating-container">
			<h1>設備選擇</h1>

	  <div class="select-container">
			<label for="videoSource">本地端攝影機:</label>
			<select id="videoSource" v-model="selectedVideoId">
				<option v-for="device in videoDevices" :key="device.deviceId" :value="device.deviceId">
				{{ device.label || `鏡頭 ${videoDevices.indexOf(device) + 1}` }}
				</option>
			</select>
			</div>

			<div class="select-container">
			<label for="audioSource">本地端麥克風:</label>
			<select id="audioSource" v-model="selectedAudioId">
				<option v-for="device in audioDevices" :key="device.deviceId" :value="device.deviceId">
				{{ device.label || `麥克風 ${audioDevices.indexOf(device) + 1}` }}
				</option>
			</select>
	  </div>

	  <video ref="videoElement" autoplay playsinline></video>

	  <div class="buttons">
			<button @click="start">開始</button>
			<button @click="stop">停止</button>
	  </div>
	</div>
</template>

<script setup>
  import { ref, onMounted, onBeforeUnmount } from 'vue'

  const videoElement = ref(null)
  const videoDevices = ref([])
  const audioDevices = ref([])
  const selectedVideoId = ref('')
  const selectedAudioId = ref('')
  const stream = ref(null)

  // 設備列表
  const getDevices = async () => {
	try {
	  const devices = await navigator.mediaDevices.enumerateDevices()
	  videoDevices.value = devices.filter(device => device.kind === 'videoinput')
	  audioDevices.value = devices.filter(device => device.kind === 'audioinput')

	  // 預設設備
	  if (videoDevices.value.length > 0) {
		selectedVideoId.value = videoDevices.value[0].deviceId
	  }
	  if (audioDevices.value.length > 0) {
		selectedAudioId.value = audioDevices.value[0].deviceId
	  }
	} catch (error) {
	  console.error(`設備列表錯誤: ${error}`)
	}
  }

  // 啟動媒體流
  const start = async () => {
	stop()

	const constraints = {
	  video: {
		deviceId: selectedVideoId.value ? { exact: selectedVideoId.value } : undefined,
		width: { ideal: 1280 },
		height: { ideal: 720 }
	  },
	  audio: selectedAudioId.value ? { deviceId: { exact: selectedAudioId.value } } : false
	}

	try {
	  stream.value = await navigator.mediaDevices.getUserMedia(constraints)
	  videoElement.value.srcObject = stream.value

	  // 當設備變更時, 重新進行設備列表
	  navigator.mediaDevices.addEventListener('devicechange', getDevices);
	} catch (error) {
	  console.error(`啟動媒體流錯誤: ${error}`);
	}
  }

  // 停止媒體流
  const stop = () => {
		if (stream.value) {
			stream.value.getTracks().forEach(track => track.stop())
			videoElement.value.srcObject = null
			stream.value = null
		}
		navigator.mediaDevices.removeEventListener('devicechange', getDevices)
  }

  // 初始化
  onMounted(async () => {
		// 請求權限
		try {
			await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
			await getDevices();
		} catch (error) {
			console.error(`初始化權限請求錯誤: ${error}`);
		}
  })

  onBeforeUnmount(() => {
		stop()
  })
</script>

<style lang="scss" scoped>
	@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

	.floating-container {
		position: fixed;
		top: 15vw;
		//left: 50%;
		transform: translate(-50%, -50%);
		background-color: rgba(255, 255, 255, 0.95); /* 不透明背景 */
		padding: 30px;
		border-radius: 12px;
		box-shadow: 0 10px 25px rgba(0, 0, 0, 0.2);
		z-index: 2001;
		//width: 80%;
		max-width: 600px;
		border: 1px solid #e0e0e0;
		font-family: '微軟正黑體', sans-serif;
	}

	h1 {
		font-size: 1rem;
		margin-bottom: 10px;
		color: #333;
		text-align: center;
	}
	/*
  .container {
		max-width: 800px;
		margin: 0 auto;
		padding: 10px;
		font-family: Arial, sans-serif;
		font-family: '微軟正黑體', sans-serif;
  }
	*/
  .select-container {
		margin: 15px 0;
  }

  select {
		margin-left: 10px;
		padding: 5px;
  }

  video {
		//width: 100%;
		//max-width: 600px;
		//background: #000;
		//margin: 20px 0;
		//border-radius: 4px;

    width: 300px;
    height: 200px;
    margin: 10px;
    border: 1px solid #ccc;
  }

  .buttons {
		margin-top: 10px;
  }

  button {
		padding: 8px 15px;
		margin-right: 10px;
		background: #007bff;
		color: white;
		border: none;
		border-radius: 4px;
		cursor: pointer;
  }

  button:hover {
		background: #0056b3;
  }
</style>
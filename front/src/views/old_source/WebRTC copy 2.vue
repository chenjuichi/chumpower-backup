<template>
	<div>
		<!--
		<h2>選擇攝影機:</h2>
    <select v-model="selectedDeviceId.video" @change="startMedia">
      <option v-for="device in devices.video" :key="device.deviceId" :value="device.deviceId">
        {{ device.label || "未命名攝影機" }}
      </option>
    </select>

    <h2>選擇麥克風:</h2>
    <select v-model="selectedDeviceId.audio" @change="startMedia">
      <option v-for="device in devices.audio" :key="device.deviceId" :value="device.deviceId">
        {{ device.label || "未命名麥克風" }}
      </option>
    </select>
		-->

		<!-- 本地視訊 -->
		<video ref="localVideo" autoplay muted></video>

		    <!-- 控制按鈕 -->
		<!--
		<div>
      <button @click="getResolution">獲取解析度</button>

      <button @click="setResolution(1280, 720)">設置解析度為 1280x720</button>
      <button @click="setResolution(1920, 1080)">設置解析度為 1920x1080</button>

    </div>
		-->
		<!-- 遠端視訊 -->
		<!--
		<div v-for="peer in peers" :key="peer.id">
      <video :ref="remoteVideos" autoplay></video>
    </div>
		-->
		<div v-for="peer in peers" :key="peer.id">
			<video :ref="el => remoteVideos[peer.id] = el" autoplay></video>
		</div>
	</div>
</template>

<script setup>
import { ref, defineComponent, onMounted, onUnmounted, onBeforeMount, nextTick } from 'vue';

import SimplePeer from 'simple-peer';

import { myMixin } from '../../mixins/common.js';
import { socket_server_ip }  from '../../mixins/crud.js';        //虛的socket_server_ip, 不會真的用到
import { useSocketio } from '../../mixins/SocketioService.js';
import { snackbar, snackbar_info, snackbar_color } from '../../mixins/crud.js';

//=== component name ==
defineComponent({  name: 'WebRTC' });

// === mix ==
const { initAxios } = myMixin();

//=== props ===

//=== data ===
const socketName = ref('');
const messages = ref([]);

//const userId = 'user_chumpower';
const userId = `user_${Math.random().toString(36).substr(2, 9)}`; // 生成唯一 ID
const roomId = 'room1'; 					// 指定房間
const clientAppName = 'WebRTC';
const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId, clientAppName);

const currentUser = ref({});

const localVideo = ref(null);				// 本地視訊元素
const localStream = ref(null);			// 本地媒體流
const resolution = ref(null);				// 當前解析度
const capabilities = ref(null);			// 設備支持的解析度範圍

const retryDelay = ref(500);

const devices = ref({
  video: [],
  audio: []
});
const selectedDeviceId = ref({
  video: "",
  audio: ""
});

const peers = ref([]);						// 遠端 peer連線 列表
//const remoteVideos = ref([]);			// 儲存所有遠端<video />
const remoteVideos = ref({});			// 儲存所有遠端<video />

//=== watch ===

//=== computed ===

//=== mounted ===
onMounted(async () => {
  console.log("WebRTC.vue, mounted()...");

  let user = localStorage.getItem("loginedUser");
  currentUser.value = user ? JSON.parse(user) : null;
  console.log("currentUser:", currentUser.value);

  //initialize();

  console.log('等待socket連線...');
  try {
		await checkPermissions();								// 強制請求權限
    await setupSocketConnection();					// 建立Socket.io實體
		//stopLocalStream();											// 先關閉舊的攝影機與麥克風（如果有的話）
		await initLocalStream();								// 初始化本地視訊
		socket.value.emit('join', roomId); 			// 加入房間
		setupSocketListenersForWebRTC();				//設定WebRTC
  } catch (error) {
    showSnackbar(`Socket初始化及連線失敗: ${error}`, 'red accent-2');
  }
}); //end of onMounted

//=== unmounted ===
onUnmounted(() => {
  stopAllPeers();
  stopLocalStream();
  if (socket.value) {
    socket.value.emit('leave', roomId);
    socket.value.disconnect();
  }
});

//=== created ===
onBeforeMount(() => {
  console.log("SocketTest.vue, created()...")

  initAxios();
  //initialize();
});

//=== method ===
const initialize = async () => {
  try {
    console.log("initialize()...");

  } catch (error) {
    console.error("Error during initialize():", error);
  }
};

// 初始化本地媒體流
const initLocalStream = async (retryCount = 0) => {

    // 先停止現有媒體流
		await stopLocalStream();

		retries.value = 0; // 初始化重試次數

		while (retries.value < maxRetries.value) {
			try {
				//準備約束條件
				const constraints = {
					video: true,
					audio: true,
				};

				localStream.value = await navigator.mediaDevices.getUserMedia(constraints);

				localVideo.value.srcObject = localStream.value;
				localVideo.value.play();

				console.log(`本地媒體流已取得: ${localStream.value}`);
			} catch (error) {
				if (error.name === 'NotReadableError') {
					showSnackbar('無法訪問攝像頭或麥克風，請檢查設備連接和權限!', 'red accent-2');
				} else if (error.name === 'PermissionDeniedError') {
					showSnackbar('請允許瀏覽器訪問攝像頭和麥克風!', 'red accent-2');
				} else if (error.name === 'NotFoundError') {
					showSnackbar('找不到指定的媒體設備!', 'red accent-2');
				} else if (error.name === 'OverconstrainedError') {
					showSnackbar('無法滿足指定的媒體約束條件!', 'red accent-2');
				} else {
					showSnackbar(`發生未知錯誤，請檢查控制台! ${error.name}`, 'red accent-2');
				}
				//throw error;
			}
		}
};

// 獲取當前解析度
const getResolution = () => {
  if (localStream.value) {
    const videoTrack = localStream.value.getVideoTracks()[0];
    if (videoTrack) {
      const settings = videoTrack.getSettings();
      resolution.value = { width: settings.width, height: settings.height };
      console.log('當前解析度:', resolution.value);
    } else {
      console.error('未找到視頻軌道');
    }
  } else {
    console.error('未取得媒體流');
  }
};

const stopAllPeers = () => {
  peers.value.forEach(({ peer, id }) => {
    peer.destroy();
    console.log(`Peer ${id} 已銷毀`);
  });
  peers.value = [];
};

const stopLocalStream =async () => {
	if (localStream.value) {
		localStream.value.getTracks().forEach(track =>{
			track.stop();
			localStream.value.removeTrack(track);
		});
		console.log("本地媒體流已關閉");

		//if (localVideo.value) {
		//	localVideo.value.srcObject = null; // 移除畫面
		//}

		localStream.value = null; // 清空媒體流

		await delay(retryDelay.value);  // 延遲後繼續重試
	} else {
		console.log("沒有可關閉的本地媒體流");
	}
};

// 設置解析度
const setResolution = async (width, height) => {
  if (localStream.value) {
    const videoTrack = localStream.value.getVideoTracks()[0];
    if (videoTrack) {
      try {
        await videoTrack.applyConstraints({
          width: { ideal: width },
          height: { ideal: height },
        });
        console.log('解析度已設置為:', width, 'x', height);
        getResolution(); // 更新解析度顯示
      } catch (error) {
        console.error('無法設置解析度:', error);
      }
    } else {
      console.error('未找到視頻軌道');
    }
  } else {
    console.error('未取得媒體流');
  }
};

// 取得所有攝影機裝置
const getDevices = async () => {
  try {
		// 🔹 確保已獲取權限 (部分瀏覽器要求)
		await navigator.mediaDevices.getUserMedia({ video: true });

    const mediaDevices = await navigator.mediaDevices.enumerateDevices();
    devices.value = mediaDevices.filter(d => d.kind === "videoinput");
		console.log("devices:", devices.value)
    if (devices.value.length > 0) {
      selectedDeviceId.value = devices.value[0].deviceId; // 預設選擇第一台攝影機
    }
		console.log("before selectedDeviceId:", selectedDeviceId.value);
  } catch (error) {
    console.error("取得攝影機失敗:", error);
  }
};

// 創建 Peer 連接
const createPeer = async (userId, initiator) => {
	return new Promise((resolve) => {
		let existingPeerIndex = peers.value.findIndex((p) => p.id === userId);
		if (existingPeerIndex !== -1) {
			console.log(`Peer ${userId} 已存在，不重複建立`);
			return resolve(peers.value[existingPeerIndex].peer);
		}

		const peer = new SimplePeer({
			initiator,									// true: 發起連線, false: 回應連線
			trickle: false, 						// 禁用 trickle ICE，等待完整的 ICE
			stream: localStream.value,
		});

		// 當有信號數據時，發送給對方
		// roomId 表示多人房間中的信令 (signaling)
		peer.on('signal', (data) => {
			if (data.type === 'offer') {
				socket.value.emit('offer', roomId, data);
			} else if (data.type === 'answer') {
				socket.value.emit('answer', roomId, data);
			} else {
				socket.value.emit('candidate', roomId, data);
			}
		});

		// 當收到遠端媒體流時，顯示在對應的 video 元素中
		peer.on('stream', async (stream) => {
			console.log('收到遠端媒體流:', stream);

			await nextTick();
			peers.value.push({ id: userId, peer, stream });

			setTimeout(() => {
				setRemoteVideo(userId, stream);
			}, 500);
		});

		// 處理錯誤
		peer.on('error', (error) => {
			console.error('Peer 連接錯誤:', error);
			//reject(error);
		});

		peer.on('close', () => {
			console.log('Peer 連線關閉:', userId);
			removePeer(userId);
		});

		peers.value.push({ id: userId, peer });		// 將 peer 加入列表
		resolve(peer);
	});
};

// 設置 Socket.io 監聽器
const setupSocketListenersForWebRTC =  async () => {
	// 當有新用戶加入時
	socket.value.on('user-connected', async (userId) => {
		console.log("收到 user-connected")

		console.log('新用戶加入:', userId);

		try {
			// 檢查是否已經為該用戶創建了 Peer 連接
			const existingPeer = peers.value.find((p) => p.id === userId);
			if (!existingPeer) {
				await createPeer(userId, true);	// 主動建立 WebRTC 連線
			}
		} catch (error) {
			console.error('創建 Peer 連接失敗:', error);
		}
	});

	socket.value.on('offer', async (userId, offer) => {
		console.log("收到 offer")

		console.log('遠地用戶:', userId);

		try {
			let peer = peers.value.find((p) => p.id === userId)?.peer;

			if (!peer || peer.destroyed) {
				console.warn(`Peer ${userId} 不存在或已銷毀，重新建立`);
				peer = await createPeer(userId, false);
			}

			peer.signal(offer);
		} catch (error) {
			console.error('處理 offer 失敗:', error);
		}
	});

	socket.value.on('answer', async (userId, answer) => {
		console.log("收到 answer");

		console.log('遠地用戶:', userId);

		try {
			const peer = peers.value.find((p) => p.id === userId)?.peer;
			if (peer) {
				peer.signal(answer);
			}
		} catch (error) {
			console.error('處理 answer 失敗:', error);
		}
	});

	// 當收到 ICE 候選者時
	socket.value.on('candidate', async (userId, candidate) => {
		console.log("收到 ICE candidate")

		console.log('遠地用戶:', userId);

		try {
			const peer = peers.value.find((p) => p.id === userId)?.peer;
			if (peer) {
				peer.signal(candidate);
			}
		} catch (error) {
      console.error('處理 candidate 失敗:', error);
    }
	});

	// 當用戶斷開連接時
	socket.value.on('user-disconnected', (userId) => {
		console.log("收到 user-disconnected");

		console.log('遠地用戶離開:', userId);

		removePeer(userId);
	});
};

// 檢查攝影機權限
const checkPermissions = async () => {
  try {
    const cameraPermission = await navigator.permissions.query({ name: "camera" });
    const micPermission = await navigator.permissions.query({ name: "microphone" });

    console.log("攝影機權限:", cameraPermission.state);
    console.log("麥克風權限:", micPermission.state);

    if (cameraPermission.state === "denied" || micPermission.state === "denied") {
			showSnackbar('請在瀏覽器設定中允許攝影機和麥克風存取！', 'red accent-2');
			return;
    }

    // 取得可用的攝影機與麥克風設備
    const devices = await navigator.mediaDevices.enumerateDevices();
    const videoDevices = devices.filter(device => device.kind === "videoinput");
    const audioDevices = devices.filter(device => device.kind === "audioinput");

		devices.forEach(device => {
			console.log(`${device.kind}: ${device.label} id = ${device.deviceId}`);
		});

    if (videoDevices.length === 0) {
        showSnackbar('沒有可用的攝影機，請檢查設備！', 'red accent-2');
    }
    if (audioDevices.length === 0) {
        showSnackbar('沒有可用的麥克風，請檢查設備！', 'red accent-2');
		}
  } catch (error) {
    console.warn("無法檢查權限:", error);
		showSnackbar(`無法檢查設備(攝影機/麥克風)權限: ${error}`, 'red accent-2');
  }
};

// 設置遠端視訊
const setRemoteVideo = async (remoteUserId, stream) => {
	await nextTick();
	setTimeout(() => {
		const videoElement = remoteVideos.value[remoteUserId]; // 直接從 Object 取值
		if (videoElement) {
			videoElement.srcObject = stream;
			videoElement.play();
			console.log(`成功綁定 remoteVideo 給 ${remoteUserId} 用戶`);
		} else {
			console.error(`找不到 remoteVideo (用戶: ${remoteUserId})`);
		}
	}, 500);
};

// 移除 Peer
const removePeer = (remoteUserId) => {
	const peerIndex = peers.value.findIndex((p) => p.id === remoteUserId);
	if (peerIndex !== -1) {
		console.log(`銷毀 Peer: ${remoteUserId}`);
		peers.value[peerIndex].peer.destroy();
		peers.value.splice(peerIndex, 1);
	}
};

const showSnackbar = (message, color) => {
	console.log("showSnackbar,", message, color)

	snackbar_info.value = message;
	snackbar_color.value = color;
	snackbar.value = true;
};
</script>

<style scoped>
  video {
    width: 300px;
    height: 200px;
    margin: 10px;
    border: 1px solid #ccc;
  }
</style>
<template>
<v-container fluid class="fill-height d-flex justify-center align-center">
	<v-row justify="space-between">
		<!-- 本地視訊 -->
		<v-col cols="12" md="6" class="d-flex justify-center align-center">
			<v-card class="pa-2 ma-2"	height="360" width="480" elevation-10 style="background:#E1F5FE;">
				<div style="text-align:left;">
					<label for="videoSource">攝影機:</label>
					<select
						id="videoSource"
						v-model="selectedVideoId"
						style="border: 1px solid #000; border-radius: 6px; padding: 4px; width: 85%;"
					>
						<option v-for="device in videoDevices" :key="device.deviceId" :value="device.deviceId">
							{{ device.label || `鏡頭 ${videoDevices.indexOf(device) + 1}` }}
						</option>
					</select>
				</div>
				<div style="text-align:left; margin-top: 1vw;">
					<label for="audioSource">麥克風:</label>
					<select
						id="audioSource"
						v-model="selectedAudioId"
						style="border: 1px solid #000; border-radius: 6px; padding: 4px; width: 85%;"
					>
						<option v-for="device in audioDevices" :key="device.deviceId" :value="device.deviceId">
							{{ device.label || `麥克風 ${audioDevices.indexOf(device) + 1}` }}
						</option>
					</select>
				</div>

				<video ref="localVideo" autoplay playsinline style="margin-bottom: 5px; margin-right:0px; margin-left:0px;"></video>

				<div class="buttons" style="margin: 5px 0px;">
					<button @click="start">開始</button>
					<button @click="stop">停止</button>
					<button @click="leavePage">離開</button>
				</div>
			</v-card>
		</v-col>
		<!-- 遠端視訊 -->
		<v-col cols="12" md="6" class="d-flex justify-center align-center">
			<v-card class="pa-2 ma-2"	height="360" width="480" elevation-10 style="background:#E1F5FE;">
				<div v-for="(stream, userId) in remoteVideos" :key="userId">
					<video ref="el => el && (el.srcObject = stream)" autoplay playsinline ></video>
        </div>
				<!--
				<div v-for="peer in peers" :key="peer.id">
					<video :ref="el => remoteVideos[peer.id] = el" autoplay></video>
				</div>
				-->
			</v-card>
		</v-col>
	</v-row>
</v-container>
</template>

<script setup>
  import { ref, defineComponent, onMounted, onBeforeUnmount, defineProps, onBeforeMount, nextTick } from 'vue'
	import { useRouter } from 'vue-router';
	import SimplePeer from 'simple-peer';

	import { myMixin } from '../mixins/common.js';
	import { socket_server_ip }  from '../mixins/crud.js';        //虛的socket_server_ip, 不會真的用到
	import { useSocketio } from '../mixins/SocketioService.js';
	import { snackbar, snackbar_info, snackbar_color } from '../mixins/crud.js';

	//=== component name ==
	defineComponent({  name: 'WebRTC' });

	// === mix ==
	const { initAxios } = myMixin();

	//=== props ===
	const props = defineProps({
		targetRouteName: String // 接收目標路由名稱
	});

	//=== data ===
	const userId = `user_${Math.random().toString(36).substr(2, 9)}`; // 生成唯一 ID
	const roomId = 'room1'; 					// 指定房間
	const clientAppName = 'WebRTC';
	const { socket, setupSocketConnection } = useSocketio(socket_server_ip.value, userId, clientAppName);

	const currentUser = ref({});

  const localVideo = ref(null);
	const remoteVideos = ref({});			// 所有遠端<video />
  const videoDevices = ref([]);
  const audioDevices = ref([]);
  const selectedVideoId = ref('');
  const selectedAudioId = ref('');
  const localStream = ref(null);
	const peers = ref([]);						// 遠端 peer連線 列表

	const router = useRouter(); // 直接使用 useRouter() 獲取 router

	//=== method ===
	const leavePage = () => {
		console.log("props.router:", props.targetRouteName);

		if (router.currentRoute.value.name === props.targetRouteName) {
			console.log("已經在此頁，重新渲染組件...");
			window.location.reload(true);   // true:強制從伺服器重新載入, false:從瀏覽器快取中重新載入頁面（較快，可能不更新最新內容,預設)
		} else {
			console.log("跳轉到新頁面...");
			router.push({ name: props.targetRouteName });
		}
	};

  // 設備列表
  const getDevices = async () => {
		try {
			const devices = await navigator.mediaDevices.enumerateDevices()
			videoDevices.value = devices.filter(device => device.kind === 'videoinput')
			audioDevices.value = devices.filter(device => device.kind === 'audioinput')

			// 預設設備
			if (videoDevices.value.length > 0) {
			selectedVideoId.value = videoDevices.value[0].deviceId || '';
			}
			if (audioDevices.value.length > 0) {
			selectedAudioId.value = audioDevices.value[0].deviceId || '';
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
			localStream.value = await navigator.mediaDevices.getUserMedia(constraints)
			localVideo.value.srcObject = localStream.value

			// 當設備變更時, 重新進行設備列表
			navigator.mediaDevices.addEventListener('devicechange', getDevices);
		} catch (error) {
			console.error(`啟動媒體流錯誤: ${error}`);
		}
  }

  // 停止媒體流
  const stop = () => {
		if (localStream.value) {
			localStream.value.getTracks().forEach(track => {
				track.stop();
			})
			//localVideo.value.srcObject = null;
			localStream.value = null;
		}

		if (localVideo.value) {
			localVideo.value.srcObject = null; // 移除 video 來源
		}

		// 移除 devicechange 事件監聽
		if (typeof getDevices === "function") {
      navigator.mediaDevices.removeEventListener('devicechange', getDevices);
    }
		console.log("媒體裝置已釋放");

		//navigator.mediaDevices.removeEventListener('devicechange', getDevices);

		// 強制請求權限來釋放攝影機和麥克風
		//navigator.mediaDevices.getUserMedia({ video: false, audio: false })
    //.then((silentStream) => {
    //  silentStream.getTracks().forEach(track => track.stop()); // 確保完全關閉
    //})
    //.catch(error => console.error("釋放媒體裝置錯誤:", error));
  }

	const stopAllPeers = () => {
		peers.value.forEach(({ peer, id }) => {
			if (peer) {
				try {
					// 銷毀 peer 連線,
					// 含關閉音視頻流的傳輸, 關閉與遠端用戶端的連接, 清除所有與該連接相關的事件監聽器和內部狀態
					peer.destroy();
					console.log(`Peer ${id} 已銷毀`);
				} catch (error) {
					console.error(`銷毀 Peer ${id} 時出現錯誤:`, error);
				}
			}
		});
		peers.value = []; // 清空 peers 列表
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

	// 創建 Peer 連接
	const createPeer = async (userId, initiator) => {
		console.log("createPeer()...");

		let existingPeerIndex = peers.value.findIndex((p) => p.id === userId);
		if (existingPeerIndex !== -1) {
			console.log(`Peer ${userId} 已存在，不重複建立`);
			return peers.value[existingPeerIndex].peer;
		}

		try {
			const peer = new SimplePeer({
				initiator,									// true: 發起連線, false: 回應連線
				trickle: false, 						// 禁用 trickle ICE，等待完整的 ICE
				stream: localStream.value,
			});

			peer.on('signal', (data) => handleSignal(data));
			peer.on('stream', (stream) => handleStream(userId, stream));
			peer.on('error', (error) => handlePeerError(userId, error));
			peer.on('close', () => handlePeerClose(userId));

			// 監聽 track 事件，處理遠端音視頻
			peer.on('track', (track, stream) => {
				console.log(`收到 track 事件來自: ${userId}, track類型: ${track.kind}`);

				// 確保這個 stream 只有一次被加入
				if (!remoteVideos.value[userId]) {
						remoteVideos.value[userId] = stream;
				}

				// 透過 nextTick 確保 Vue 3 DOM 已更新
				nextTick(() => {
					const videoElement = remoteVideos.value[userId];
					if (videoElement) {
							videoElement.srcObject = stream;
					}
				});
			});

			peers.value.push({ id: userId, peer });		// 將 peer 加入列表
			return peer;
		} catch (error) {
			console.error(`創建 Peer 連接失敗: ${error}`);
			throw error;
  	}
	};

	// 處理信號
	const handleSignal = (data) => {
		console.log('Peer on signal...', data);

		// 確保 socket 存在
		if (!socket.value) {
        console.warn('Socket is not connected, ignoring signal.');
        return;
    }

    // 確保 peer 仍然有效
    if (!peer || peer.destroyed) {
        console.warn('Peer is destroyed, ignoring signal.');
        return;
    }

		// 當有信號數據時，發送給對方, roomId 表示多人房間中的信令 (signaling)
		if (data.type === 'offer') {
			socket.value.emit('offer', roomId, data);
		} else if (data.type === 'answer') {
			socket.value.emit('answer', roomId, data);
		} else {
			socket.value.emit('candidate', roomId, data);
		}
	};

	// 處理遠端流
	const handleStream = async (userId, stream) => {
		console.log('收到遠端媒體流:', stream);
		await nextTick();
		peers.value.push({ id: userId, stream });
		setRemoteVideo(userId, stream);
	};

	// 處理錯誤
	const handlePeerError = (userId, error) => {
		console.error(`Peer 連接錯誤: ${error} (userId: ${userId})`);
	};

	// 處理連接關閉
	const handlePeerClose = (userId) => {
		console.log(`Peer 連線關閉: ${userId}`);
		removePeer(userId);
	};

	const setRemoteVideo = async (userId, stream) => {
		console.log(`設定遠端視訊: ${userId}`);

		await nextTick(); // 確保 DOM 已更新

		const videoElement = remoteVideos.value[userId];	// 取得對應的 <video> 元素

		if (!videoElement) {
			console.warn(`找不到 userId ${userId} 的 video 元素`);
			return;
		}

		videoElement.srcObject = stream;			// 綁定視訊流
		console.log(`已綁定視訊流到 userId ${userId}`);
	};

	// 註冊 Socket 事件
	const registerSocketEvents = () => {
		socket.value.on('user-connected', (userId) => handleUserConnected(userId));
		socket.value.on('offer', (userId, offer) => handleOffer(userId, offer));
		socket.value.on('answer', (userId, answer) => handleAnswer(userId, answer));
		socket.value.on('candidate', (userId, candidate) => handleCandidate(userId, candidate));
		socket.value.on('user-disconnected', (userId) => handleUserDisconnected(userId));
	};

	// 處理新用戶連接
	const handleUserConnected = async (userId) => {
		console.log("新用戶加入:", userId);
		try {
			const existingPeer = peers.value.find((p) => p.id === userId);
			if (!existingPeer) {
				await createPeer(userId, true);
			}
		} catch (error) {
			console.error('創建 Peer 連接失敗:', error);
		}
	};

	// 處理 offer 訊息
	const handleOffer = async (userId, offer) => {
		console.log('收到 offer', userId);
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
	};

	// 處理 answer 訊息
	const handleAnswer = (userId, answer) => {
		console.log('收到 answer', userId);
		const peer = peers.value.find((p) => p.id === userId)?.peer;
		if (peer) {
			peer.signal(answer);
		}
	};

	// 處理 candidate 訊息
	const handleCandidate = (userId, candidate) => {
		console.log('收到 ICE candidate', userId);
		const peer = peers.value.find((p) => p.id === userId)?.peer;
		if (peer) {
			peer.signal(candidate);
		}
	};

	// 處理用戶離開
	const handleUserDisconnected = (userId) => {
		console.log('遠地用戶離開:', userId);
		removePeer(userId);
		delete remoteVideos.value[userId]; // 删除相關的遠端視頻
	};

	//=== created ===
	onBeforeMount(() => {
		console.log("WebRTC.vue, created()...")

		initAxios();
		//initialize();
	});

	//=== mounted ===
	onMounted(async () => {
		console.log("WebRTC.vue, mounted()...");

		let user = localStorage.getItem("loginedUser");
		currentUser.value = user ? JSON.parse(user) : null;
		console.log("currentUser:", currentUser.value);

		window.addEventListener('beforeunload', stop);

		// 請求權限
		try {
			await setupSocketConnection();					// 建立Socket.io實體

			if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
				console.error("瀏覽器不支援 getUserMedia");
			} else {

			//await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
			const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      console.log("媒體流取得成功", stream);
			await getDevices();

			//---
			socket.value.emit('join', roomId); 			// 加入房間
			// 事件註冊
			registerSocketEvents();
			}
			/*
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
			*/
			//---
		} catch (error) {
			console.error(`初始化權限請求錯誤: ${error}`);
		}
  })

  onBeforeUnmount(() => {
		stop();
		stopAllPeers();
		window.removeEventListener('beforeunload', stop);
  })
</script>

<style lang="scss" scoped>
	@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

	h1 {
		font-size: 1rem;
		margin-bottom: 10px;
		color: #333;
		text-align: center;
	}

  select {
		margin-left: 10px;
		padding: 5px;
  }

  video {
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
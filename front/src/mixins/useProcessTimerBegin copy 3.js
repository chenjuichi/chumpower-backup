import { ref, nextTick, watch } from "vue";

import { apiOperation } from './crud.js';

import { materials }  from './crud.js';

// 封裝各 API
const dialog2StartProcess = apiOperation('post', '/dialog2StartProcessBegin');
const dialog2UpdateProcess = apiOperation('post', '/dialog2UpdateProcessBegin');
const dialog2ToggleProcess = apiOperation('post', '/dialog2ToggleProcessBegin');
const dialog2CloseProcess = apiOperation('post', '/dialog2CloseProcessBegin');

const updateMaterial = apiOperation('post', '/updateMaterial');

export function useProcessTimer(getTimerRef) {
//export function useProcessTimer(timerRef) {
	// 後端資料
	const processId = ref(null);

	// 與 TimerDisplay 同步的狀態
	const isPaused  = ref(true);
	const elapsedMs = ref(0);

	let _ticker = null;
	let _lastTs = null;
	let _autoUpd = null;

	let _frozenElapsedOnPause = null;

	let _updater = null  					// setInterval 的 handle
	const isClosed = ref(false)  	// 關閉後標記
	const displaySecs = ref(0)    // 只負責 UI 顯示，不做清零
	const elapsedSecs = ref(0)    // 內部運算/回寫用

	const pauseTime = ref(0);   // 後端回報的總暫停秒數（可顯示用）
	const pauseCount= ref(0);   // 後端回報的暫停次數（可顯示用）
	/*
	const for_vue3_has_started =ref(false)
	const for_vue3_pause_or_start_status =ref(false)
	*/
	const materialId  = ref(0);
	const processType = ref(0);
	const userId      = ref(null);
	const assembleId  = ref(0);

	//const elapsedMs = ref(0);
	//const isPaused = ref(true);
	const hasStarted = ref(false);

	function _startAutoUpdate() {
		_stopAutoUpdate();
		_autoUpd = setInterval(() => {
			// 不中斷：只要有 process 且沒暫停，就定期回寫
			//if (processId.value && !isPaused.value) {
			if (processId.value) {
				updateProcess().catch(() => {});
			}
		}, 5000); // 每 5 秒回寫一次；可依需要調整
	}

	function _stopAutoUpdate() {
		if (_autoUpd) clearInterval(_autoUpd);
		_autoUpd = null;
	}

	function _startLocalTicker() {
		_stopLocalTicker();
		_lastTs = Date.now();
		_ticker = setInterval(() => {
			const now = Date.now();
			const delta = now - (_lastTs || now);
			elapsedMs.value += delta;     // ✅ 就算沒有 TimerDisplay，也會自己累加
			_lastTs = now;
		}, 1000);
	}

	function _stopLocalTicker() {
		if (_ticker) clearInterval(_ticker);
		_ticker = null;
		_lastTs = null;
	}
	/*
	function timer() {
		// 每次要用時才取，避免還沒掛載時為 null
		return getTimerRef?.() || null;
	}
	*/
	function timer() {
		// 每次要用時才取，避免還沒掛載時為 null
		const t = getTimerRef?.() || null;
		if (!t) return null;

		// 兩種都支援：
		// 1) 直接就是元件實例（有 resume/pause/getElapsedMs）
		// 2) 是 Vue ref 包一層（value 才是實例）
		const inst = (typeof t?.getElapsedMs === 'function' || typeof t?.resume === 'function')
			? t : (t?.value ?? null);

		return inst || null;
	}

	// 給 <TimerDisplay @update:time> 綁的：每秒同步毫秒
	function onTick(ms) {
		elapsedMs.value = Number(ms) || 0;
	}

	async function restoreProcess(mId, pType, uId, aId = 0) {
		return startProcess(mId, pType, uId, aId, { restoreOnly: true })
	}

	// 進入 dialog：後端建立/還原 + 同步 TimerDisplay
	async function startProcess(mId, pType, uId, aId = 0, opts = {}) {
		console.log("startProcess()...")

		const assemble_id = Number(aId ?? 0);

		const restoreOnly = opts?.restoreOnly === true

		const payload = {
			material_id: mId,
			process_type: pType,
			user_id: uId,
			restore_only: restoreOnly,
		};
		if (assemble_id != 0)
			payload.assemble_id = assemble_id;

		materialId.value  = mId;
		processType.value = pType;
		userId.value      = uId;
		assembleId.value  = assemble_id;

		const res  = await dialog2StartProcess(payload);
		const data = res?.data ?? res;

		if (!data?.success) {
			// 還原模式下，沒資料就靜默結束；一般模式則回 false
			if (restoreOnly) return { success: true, restored: false, reason: 'no-active' }
			return { success: false, message: data?.message || 'startProcess failed' }
		}
		console.log("1. processId.value, :", processId.value, data?.process_id)

		// 後端回傳建議包含：process_id, elapsed_time(秒), is_paused
		processId.value = data?.process_id ?? processId.value;
		console.log("2. processId.value, :", processId.value, data?.process_id)

		// 還原 TimerDisplay（秒 → ms）
		//const seconds   = Number(res.elapsed_time || 0);
		//const seconds = Number(res.elapsed_time ?? 0);
		const seconds = Number(data?.elapsed_time ?? 0);
		const paused = !!data?.is_paused;
		//const paused = !!res.is_paused;
		const pauseTotal  = Number(data?.pause_time ?? 0);   // 總暫停秒數

		pauseTime.value  = Math.max(0, Number(data?.pause_time ?? 0));
		pauseCount.value = Math.max(0, Number(data?.pause_count ?? 0));

		//elapsed_time.value = data?.elapsed_time ?? 0
		elapsedMs.value = Math.max(0, (data?.elapsed_time ?? 0) * 1000);
		isPaused.value  = data?.is_paused ?? true;
		userId.value    = data?.started_user_id ?? uId;
		hasStarted.value = data?.has_started ?? false;

		// 同步到 TimerDisplay, 把狀態喂進子元件
		timer()?.setState(seconds, paused);
		isPaused.value = paused;

		// 若後端狀態是「暫停」，凍結當下秒數；否則清空
		_frozenElapsedOnPause = isPaused.value ? (data?.elapsed_time ?? 0) : null;

		// 用明確的 resume()/pause() 讓 UI 與本地 ticker 對齊
		/*
		if (paused) {
			timer()?.pause();
			_stopLocalTicker();
			_stopAutoUpdate();
		} else {
			await nudgeResume();
			_startLocalTicker();
			_startAutoUpdate();
		}
		*/
		if (paused) {
			timer()?.pause();
			_stopLocalTicker();
			_stopAutoUpdate();
		} else {
			if (restoreOnly) {
				// 還原模式：只讓 UI 動起來，不主動觸發 begin_time 寫入
				// 還原模式（restoreOnly）：頁面重整或換頁回來時
				timer()?.resume?.();    // 讓畫面開始跑
				_startLocalTicker();    // 啟動本地 setInterval
				// _startAutoUpdate();  // 要不要回寫 elapsed_time 看需求；如要以極小改動就保留在下面一起啟動
			} else {
				// 一般開始：照舊，用 nudgeResume() 走既有「寫 begin_time」的路
				await nudgeResume();
				_startLocalTicker();
			}
			_startAutoUpdate();       // 保留原本的自動回寫（最小更動）；若想完全不寫，移到上面 else 區塊
		}

		console.log("🔹 後端回傳 pause_time =", pauseTotal, "秒");

		return processId.value;
	}

	// 暫停/恢復切換
	async function toggleTimer() {
		if (!processId.value) return;

		console.log("toggleTimer()...")
		console.log("isPaused:",isPaused.value)
		if (isPaused.value) {
			console.log("toggleTimer() status: 開始", isPaused.value)

			//_frozenElapsedOnPause = null;     // ← 清掉凍結值，恢復改用 live ms

			// 開始
			//timer()?.resume();						// - 2025-09-23 modify
			//isPaused.value = false;				// -
			_frozenElapsedOnPause = null;		// +
			isPaused.value = false;					// +
			timer()?.resume?.();							// +
			/*
			if (!for_vue3_has_started.value) {
				for_vue3_has_started.value = true;

				await updateMaterial({
					id: materialId.value,
					record_name: "hasStarted",
					record_data: true,
				});

				await updateMaterial({
					id: materialId.value,
					record_name: "isOpenEmpId",
					record_data: userId.value,
				});

				// 記錄當前途程狀態
				const payload = {
					id: materialId.value,
					record_name: 'show2_ok',
					record_data: 1                //備料中
				};
				await updateMaterial(payload);
			}

			for_vue3_pause_or_start_status.value =true;
			*/
			console.log("toggle pause")
			await updateMaterial({
				id: materialId.value,
				record_name: "startStatus",
				record_data: true,
			});

			const idx = materials.value.findIndex(r => r.id === materialId.value);
			if (idx !== -1) {
				materials.value[idx] = {
					...materials.value[idx],
					//is_paused: false,
					//startStatus: true,
					hasStarted: true,
				};
			}

			_startLocalTicker();
			_startAutoUpdate();
		} else {
			console.log("toggleTimer() status: 暫停", isPaused.value)

			// 暫停
			//timer()?.pause();						// - 2025-09-23 modify
			//isPaused.value = true;			// -
			isPaused.value = true;				// +
			timer()?.pause?.();							// +
			/*
			for_vue3_pause_or_start_status.value =false;
			*/

			// ★ 暫停當下凍結秒數
			_frozenElapsedOnPause = Math.floor((timer()?.getElapsedMs?.() ?? elapsedMs.value) / 1000);

			console.log("toggle pause")
			await updateMaterial({
				id: materialId.value,
				record_name: "startStatus",
				record_data: false,
			});

			const idx = materials.value.findIndex(r => r.id === materialId.value);
			if (idx !== -1) {
				materials.value[idx] = {
					...materials.value[idx],
					//is_paused: true,
					startStatus: false,
				};
			}

			_stopLocalTicker();
			_stopAutoUpdate();
		}

		await nextTick();

		// 後端同步暫停狀態
		const res = await dialog2ToggleProcess({
			process_id: processId.value,
			is_paused: isPaused.value,
		});
		const data = res?.data ?? res;

		const pauseTotal = Number(data?.pause_time ?? 0);
		console.log("🔸 累計暫停時間:", pauseTotal, "秒");

		pauseTime.value  = Number(data?.pause_time ?? pauseTime.value);
		pauseCount.value = Number(data?.pause_count ?? pauseCount.value);
	}

	// 週期性/關閉前更新（把目前毫秒回傳）
	async function updateProcess() {
		if (!processId.value) return;

		if (isClosed.value) return;		// ✅ 關閉後不再回寫

		try {
			const ms = timer()?.getElapsedMs?.() ?? elapsedMs.value;

			const secs = isPaused.value && _frozenElapsedOnPause != null ? _frozenElapsedOnPause : Math.floor(ms / 1000);

			const res = await dialog2UpdateProcess({
				process_id: processId.value,
				elapsed_time: secs,
				//is_paused: isPaused.value,		// ⚠️ 不要再送 is_paused；避免另一個視窗「把暫停寫回去變成開始」
			});

			const data = res?.data ?? res;

			// 後端可能回傳校正後的 elapsed_time（秒）
			if (data?.elapsed_time != null) {
				elapsedMs.value = Number(data.elapsed_time) * 1000;
			}

			// is_paused/pause_time 只是回報，用得到就存下
			//if (typeof data?.is_paused === 'boolean') {
			//	isPaused.value = data.is_paused;
			//}
			// ★ 伺服器是唯一真相：偵測到 is_paused 變化就同步 UI 與本地 ticker
			if (typeof data?.is_paused === 'boolean' && data.is_paused !== isPaused.value) {
				isPaused.value = data.is_paused;
				if (isPaused.value) {
					// 變成暫停：凍結秒數、停畫面與本地計時
					_frozenElapsedOnPause = Math.floor((timer()?.getElapsedMs?.() ?? elapsedMs.value) / 1000);
					timer()?.pause?.();
					_stopLocalTicker();
					_stopAutoUpdate();
				} else {
					// 變成開始：清凍結、喚醒畫面、重啟本地計時與回寫
					_frozenElapsedOnPause = null;
					await nudgeResume();
					_startLocalTicker();
					_startAutoUpdate();
				}
			}

			pauseTime.value  = Number(data?.pause_time ?? pauseTime.value);
			pauseCount.value = Number(data?.pause_count ?? pauseCount.value);

		} catch (err) {
			// 400 大多是「process 已關」或「payload 不合法」
			// 直接停掉自動回寫，避免繼續打錯
			_stopAutoUpdate();
			console.warn('[updateProcess] stop auto update due to error', err);
		}

		//const pauseTotal = Number(data?.pause_time ?? 0);
		//console.log("🔸 累計暫停時間:", pauseTotal, "秒");

		//pauseTime.value  = Number(data?.pause_time ?? pauseTime.value);
		//pauseCount.value = Number(data?.pause_count ?? pauseCount.value);
	}

	// ESC/外點關閉時使用 —— 維持「計時中」
	async function updateActiveNoPause() {
		if (isPaused.value)             // 當前其實是暫停，誤用就轉成「維持暫停」
			return updateKeepPaused();

		if (!processId.value) return;

		_frozenElapsedOnPause = null;  // ← 確認維持在跑時，不再使用凍結值

		const ms = timer()?.getElapsedMs?.() ?? elapsedMs.value;
		const res = await dialog2UpdateProcess({
			process_id: processId.value,
			elapsed_time: Math.floor(ms / 1000),
			is_paused: false,              // 強制維持運行
		});

		// 前端也保守地維持「運行中」狀態，避免重開後 UI 以為是暫停
		isPaused.value = false;
		//timer()?.resume();
		await nudgeResume();
		_startLocalTicker();
		_startAutoUpdate();

		// 不改變前端的 isPaused / 不呼叫 pause()
		/*
		const data = res?.data ?? res;

		// 後端可能回傳校正後的 elapsed_time（秒）
		if (data?.elapsed_time != null) {
			elapsedMs.value = Number(data.elapsed_time) * 1000;
		}

		// is_paused/pause_time 只是回報，用得到就存下
		if (typeof data?.is_paused === 'boolean') {
			isPaused.value = data.is_paused;
		}

		const pauseTotal = Number(data?.pause_time ?? 0);
		console.log("🔸 累計暫停時間:", pauseTotal, "秒");

		pauseTime.value  = Number(data?.pause_time ?? pauseTime.value);
		pauseCount.value = Number(data?.pause_count ?? pauseCount.value);
		*/
	}

	async function updateKeepPaused() {
		if (!processId.value) return;

		// 取目前毫秒（沒有 TimerDisplay 也能用 elapsedMs）
		const ms = timer()?.getElapsedMs?.() ?? elapsedMs.value;

		// 前端狀態維持暫停
		timer()?.pause?.();
		isPaused.value = true;
		_stopLocalTicker();
		_stopAutoUpdate();

		// 先用 toggle → 強制讓後端進入「暫停」，並（必要時）設定 pause_started_at
		await dialog2ToggleProcess({
			 process_id: processId.value,
			 is_paused: true,
		});

		_frozenElapsedOnPause = Math.floor(ms / 1000); // 凍結這刻的秒數
		console.log('[ESC] freeze secs =', _frozenElapsedOnPause);

		// 後端也寫成暫停
		await dialog2UpdateProcess({
			process_id: processId.value,
			//elapsed_time: Math.floor(ms / 1000),
			elapsed_time: _frozenElapsedOnPause,
			is_paused: true,   // ← 關鍵：維持暫停
		});
	}

	async function forceResume() {
		const t = timer();
		if (!t) return;
		// 先喚醒一次
		t.resume?.();
		// 若元件需要 start() 才真正跑，補打一槍
		if (t.start && (t.isRunning === false || typeof t.isRunning === 'undefined')) {
			t.start?.();
		}
	}

	async function nudgeResume() {
		// 有些元件第一次 resume 還沒掛到 raf，用 nextTick/微延遲再喚一次
		await nextTick();
		await forceResume();
		setTimeout(() => { forceResume(); }, 0);
	}

	async function closeProcess(extra = {}) {
		if (!processId.value) return { success: false, message: 'no process' };
		console.log("closeProcess(), processId.value...", processId.value)

		//displaySecs.value = elapsedSecs.value	// 先把顯示秒數定格在最後值，並標記已關閉
		//isClosed.value = true;								// 標記已關閉，切斷殘留 interval / 誤觸

		// ---- 1) 取得本次要結算的「最後毫秒」 -----------------------------------
  		// 外部傳入(頁面已凍結的毫秒)優先；再退回計時元件的 live；再退回本地狀態
		// ✅ 以「欲結束的最終毫秒」凍結顯示（優先用外部傳入的 elapsed_ms）
		const live = timer()?.getElapsedMs?.();                  // 計時元件當前毫秒（若有）
		const extMs = Number.isFinite(Number(extra?.elapsed_ms)) // 外部傳入毫秒（PickReport 先算好）
								? Number(extra.elapsed_ms)
								: null;
		// 以 extMs 為最高優先，其次 live，再其次本地 elapsedMs
  		const ms = extMs ?? (live ?? elapsedMs.value ?? 0);

		// ---- 2) 凍結 UI 與本地狀態（不要清為 0）
		//displaySecs.value = ms;          	// 「顯示用」最後值（凍結 UI）
		displaySecs.value = Math.floor(ms / 1000);  // ✅ 顯示用為「秒」
  		isClosed.value = true;           	// 標記已關閉（切斷殘留 interval / 誤觸）
		_frozenElapsedOnPause = null;  		// 這筆作業收掉，清乾淨

		// 先停本地 ticker + 自動回寫
		_stopLocalTicker();
		_stopAutoUpdate();

		// 先停表（視覺）
		timer()?.pause();
		isPaused.value = true;

		//console.log("processId:", processId)
		//console.log("processId.value:", processId.value)

		// ---- 3) 記錄快取（刷新後也能還原最後時間；可選，但建議保留） ----------
		try {
			const pid = processId.value;
			const mat = (typeof materialId?.value !== 'undefined') ? materialId.value
								: (typeof extra?.material_id !== 'undefined') ? extra.material_id
								: null;
			const pty = (typeof processType?.value !== 'undefined') ? processType.value
								: (typeof extra?.process_type !== 'undefined') ? extra.process_type
								: (typeof extra?.process_step_code !== 'undefined') ? extra.process_step_code
								: null;
			const asm = (typeof assembleId?.value !== 'undefined') ? (assembleId.value ?? 0)
								: (typeof extra?.assemble_id !== 'undefined') ? (extra.assemble_id ?? 0)
								: 0;

			const rec = JSON.stringify({
				ms: Number(ms) || 0,
				at: Date.now(),
				uid: (typeof userId?.value !== 'undefined') ? (userId.value ?? null) : null,
			});

			if (pid) localStorage.setItem(`cp:lastClosedMs:pid:${pid}`, rec);
			if (mat && pty != null) {
				localStorage.setItem(`cp:lastClosedMs:mat:${mat}:pt:${pty}:asm:${asm}`, rec);
			}
		} catch (e) {
			console.warn('save lastClosedMs failed', e);
		}

		// ---- 4) 組 payload 並通知後端關閉（冪等、安全）
		// 通知後端關閉
		const payload = {
			// 先展開 extra
			...extra,
			// 再覆蓋為正確值（確保不被 extra 蓋掉）
			process_id: processId.value,
			elapsed_time: Math.floor(ms / 1000),
		}
		const res = await dialog2CloseProcess(payload)
		const data = res?.data ?? res;

		// 視覺重置（可選）
		//timer()?.reset();					// ⚠️ 不要 reset / 清零，否則畫面會回 00:00:00

		//elapsedMs.value = 0;			// ⚠️ 不要 reset / 清零，否則畫面會回 00:00:00

		// ---- 5) 更新暫停統計；不要 reset/清零（否則畫面會回 00:00:00）
		const pauseTotal = Number(data?.pause_time ?? 0);
		console.log("🔸 累計暫停時間:", pauseTotal, "秒");

		pauseTime.value  = Number(data?.pause_time ?? pauseTime.value);
		pauseCount.value = Number(data?.pause_count ?? pauseCount.value);

		// 若確定這個 hook 之後不再使用，就把 processId 置空
  	processId.value = null;

		return {
			success:  (data?.success !== false),
			elapsed_time: Number.isFinite(Number(data?.elapsed_time))
                    ? Number(data.elapsed_time)
                    : Math.floor(ms / 1000),
			//elapsed_time: Number(data?.elapsed_time ?? Math.floor(ms / 1000)),
			//pause_time: Number(data?.pause_time ?? 0)
			pause_time: pauseTotal
		};
		//return {
		//	processId, isPaused, elapsedMs, pauseTime, pauseCount,
		//	onTick,
		//	startProcess, toggleTimer, updateProcess, closeProcess
		//};
	}

	// 👉 新增：釋放資源
	function dispose() {
		try { timer()?.pause?.(); } catch (e) {}
		_stopLocalTicker();
		_stopAutoUpdate();
	}

	watch(elapsedSecs, (v) => {
		if (!isClosed.value) displaySecs.value = v
	})

	return {
		// 狀態
		processId,
		isPaused,
		elapsedMs,
		pauseTime,
		pauseCount,
		/*
		for_vue3_has_started,
		for_vue3_pause_or_start_status,
		*/
		materialId,
		processType,
		userId,
		assembleId,

		hasStarted,

		displaySecs,   // 提供給UI顯示
    elapsedSecs,
    isClosed,

		// 提供給 <TimerDisplay @update:time>
		onTick,
		// 動作
		startProcess,
		toggleTimer,
		updateProcess,
		closeProcess,
		restoreProcess,

		updateActiveNoPause,
		updateKeepPaused,
		nudgeResume,

		dispose,
	};
}
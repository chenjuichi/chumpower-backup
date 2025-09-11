import { ref, nextTick } from "vue";

import { apiOperation } from './crud.js';

import { materials }  from './crud.js';

// 封裝各 API
const dialog2StartProcess = apiOperation('post', '/dialog2StartProcess');
const dialog2UpdateProcess = apiOperation('post', '/dialog2UpdateProcess');
const dialog2ToggleProcess = apiOperation('post', '/dialog2ToggleProcess');
const dialog2CloseProcess = apiOperation('post', '/dialog2CloseProcess');

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

	const pauseTime = ref(0);   // 後端回報的總暫停秒數（可顯示用）
  const pauseCount= ref(0);   // 後端回報的暫停次數（可顯示用）
  const for_vue3_has_started =ref(false)
  const for_vue3_pause_or_start_status =ref(false)

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
      if (processId.value && !isPaused.value) {
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
      ? t
      : (t?.value ?? null);

    return inst || null;
  }

  // 給 <TimerDisplay @update:time> 綁的：每秒同步毫秒
  function onTick(ms) {
    elapsedMs.value = Number(ms) || 0;
  }

  // 進入 dialog：後端建立/還原 + 同步 TimerDisplay
  async function startProcess(mId, pType, uId, aId=0) {
		const assemble_id = Number(aId ?? 0);
    const payload = {
      material_id: mId,
      process_type: pType,
      user_id: uId,
    };
    if (assemble_id != 0) payload.assemble_id = assemble_id;

		materialId.value  = mId;
  	processType.value = pType;
  	userId.value      = uId;
  	assembleId.value  = assemble_id;

    const res  = await dialog2StartProcess(payload);
		const data = res?.data ?? res;

    console.log("startProcess:", data)

    // 後端回傳建議包含：process_id, elapsed_time(秒), is_paused
		processId.value = data?.process_id ?? processId.value;

    // 還原 TimerDisplay（秒 → ms）
    //const seconds   = Number(res.elapsed_time || 0);
		//const seconds = Number(res.elapsed_time ?? 0);
		const seconds = Number(data?.elapsed_time ?? 0);
		const paused = !!data?.is_paused;
    //const paused = !!res.is_paused;
		const pauseTotal  = Number(data?.pause_time ?? 0);   // 總暫停秒數

		pauseTime.value  = Number(data?.pause_time ?? 0);
    pauseCount.value = Number(data?.pause_count ?? 0);

    //elapsed_time.value = data?.elapsed_time ?? 0
    elapsedMs.value = (data?.elapsed_time ?? 0) * 1000;
    isPaused.value  = data?.is_paused ?? true;
    userId.value    = data?.started_user_id ?? uId;
    hasStarted.value = data?.has_started ?? false;

    // 先把狀態喂進子元件
    timer()?.setState(seconds, paused);
    isPaused.value = paused;

    // 用明確的 resume()/pause() 讓 UI 與本地 ticker 對齊
    if (paused) {
      timer()?.pause();
      _stopLocalTicker();
      _stopAutoUpdate();
    } else {
      await nudgeResume();
      _startLocalTicker();
      _startAutoUpdate();
    }

		console.log("🔹 後端回傳 pause_time =", pauseTotal, "秒");

		return processId.value;
  }

  // 暫停/恢復切換
  async function toggleTimer() {
    if (!processId.value) return;

    console.log("toggleTimer()...")

    if (isPaused.value) {
      console.log("toggleTimer() status: 開始", isPaused.value)

      // 開始
      timer()?.resume();
      isPaused.value = false;

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
      timer()?.pause();
      isPaused.value = true;

      for_vue3_pause_or_start_status.value =false;
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

    const ms = timer()?.getElapsedMs?.() ?? elapsedMs.value;
    const res = await dialog2UpdateProcess({
      process_id: processId.value,
      elapsed_time: Math.floor(ms / 1000),
      is_paused: isPaused.value,
    });
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
  }

	// ESC/外點關閉時使用 —— 維持「計時中」
  async function updateActiveNoPause() {
    if (!processId.value) return;

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

    // 後端也寫成暫停
    await dialog2UpdateProcess({
      process_id: processId.value,
      elapsed_time: Math.floor(ms / 1000),
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

  // 結束（關閉 dialog 時用）
  //async function closeProcess() {
  async function closeProcess() {
    if (!processId.value) return;

    const ms = timer()?.getElapsedMs?.() ?? elapsedMs.value;

    // 先停本地 ticker + 自動回寫
    _stopLocalTicker();
    _stopAutoUpdate();

    // 先停表（視覺）
    timer()?.pause();
    isPaused.value = true;

    console.log("processId:", processId)
    console.log("processId.value:", processId.value)
    // 通知後端關閉
    const res = await dialog2CloseProcess({
      process_id: processId.value,
      elapsed_time: Math.floor(ms / 1000),

    });
		const data = res?.data ?? res;

    // 視覺重置（可選）
    timer()?.reset();
    processId.value = null;
    elapsedMs.value = 0;

		const pauseTotal = Number(data?.pause_time ?? 0);
		console.log("🔸 累計暫停時間:", pauseTotal, "秒");

		pauseTime.value  = Number(data?.pause_time ?? pauseTime.value);
    pauseCount.value = Number(data?.pause_count ?? pauseCount.value);

		//return {
		//	processId, isPaused, elapsedMs, pauseTime, pauseCount,
		//	onTick,
		//	startProcess, toggleTimer, updateProcess, closeProcess
    //};
  }

  return {
    // 狀態
    processId,

    isPaused,
    elapsedMs,

		pauseTime, pauseCount,
    for_vue3_has_started, for_vue3_pause_or_start_status,

		materialId,
    processType,
    userId,
    assembleId,

    elapsedMs,
    hasStarted,

    // 提供給 <TimerDisplay @update:time>
    onTick,
    // 動作
    startProcess,
    toggleTimer,
    updateProcess,
    closeProcess,

		updateActiveNoPause,
    updateKeepPaused,
    nudgeResume,

  };
}
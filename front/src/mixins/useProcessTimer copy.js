import { ref } from "vue";

import { apiOperation } from './crud.js';

// 封裝各 API
const dialog2StartProcess = apiOperation('post', '/dialog2StartProcess');
const dialog2UpdateProcess = apiOperation('post', '/dialog2UpdateProcess');
const dialog2ToggleProcess = apiOperation('post', '/dialog2ToggleProcess');
const dialog2CloseProcess = apiOperation('post', '/dialog2CloseProcess');

export function useProcessTimer(timerRef) {
  const processId = ref(null);

  // 與 TimerDisplay 同步的狀態
  const isPaused  = ref(true);
  const elapsedMs = ref(0);

  // 給 <TimerDisplay @update:time> 綁的：每秒同步毫秒
  function onTick(ms) {
    elapsedMs.value = Number(ms) || 0;
  }

  // 開啟或還原 process
  async function startProcess(material_id, process_type, user_id) {
    const payload = { material_id, process_type, user_id };
    const res = await dialog2StartProcess(payload);

    processId.value = res.process_id ?? processId.value;
    isPaused.value = res.is_paused;

    // 將時間同步到 TimerDisplay
    timerRef.value?.setState(res.elapsed_time || 0, res.is_paused);
  }

  // 暫停 / 恢復
  async function toggleTimer() {
    if (!processId.value) return;

    if (isPaused.value) {
      timerRef.value?.resume();
      isPaused.value = false;
    } else {
      timerRef.value?.pause();
      isPaused.value = true;
    }

    await dialog2ToggleProcess({
      process_id: processId.value,
      is_paused: isPaused.value,
    });
  }

  // 定時更新 elapsed_time
  async function updateProcess() {
    if (!processId.value) return;

    const elapsed = timerRef.value?.displayTimeMs || 0;
    await dialog2UpdateProcess({
      process_id: processId.value,
      elapsed_time: Math.floor(elapsed / 1000),
      is_paused: isPaused.value,
    });
  }

  // 結束 process
  async function closeProcess() {
    if (!processId.value) return;

    const elapsed = timerRef.value?.displayTimeMs || 0;
    await dialog2CloseProcess({
      process_id: processId.value,
      elapsed_time: Math.floor(elapsed / 1000),
    });

    timerRef.value?.reset();
    processId.value = null;
    isPaused.value = true;
  }

  return {
    processId,
    isPaused,
    startProcess,
    toggleTimer,
    updateProcess,
    closeProcess,
  };
}
import { ref, onMounted, onUnmounted } from 'vue'

//export function useAvoidBrowserPrevBtn() {
export function useAvoidBrowserPrevBtn(options = {}) {
  const {
    warningText = '後退功能已禁用，請使用頁面内的導航按鍵',
    color = 'red accent-2'
  } = options;

  //=== data ===
	const showBackWarning = ref(true);

  const snackbar = ref(false);
  const snackbar_info = ref('');
  const snackbar_color = ref('red accent-2');

  //=== method ===
  const showSnackbar = (message, color) => {
    snackbar_info.value = message;
    snackbar_color.value = color;
    snackbar.value = true;
  };
  /*
  const handlePopState = () => {
    // 重新添加歷史紀錄以阻止實際後退
    history.pushState(null, null, document.URL)

    // 只在第一次顯示警告
    if (showBackWarning.value) {
      //showSnackbar('後退功能已禁用，請使用頁面内的導航按鍵', 'red accent-2');
      showSnackbar(warningText, color);
      showBackWarning.value = false
    }
  }
  */
  const handlePopState = () => {
    // ✅ 正確方式：保留 Vue Router 的 state
    history.pushState(history.state, '', document.URL)

    if (showBackWarning.value) {
      showSnackbar('後退功能已禁用，請使用頁面內的導航按鍵', 'red accent-2')
      showBackWarning.value = false
    }
  }

	onMounted(() => {
    console.log('handlePopState mounted');

		// 阻止直接後退
    window.history.pushState(null, null, document.URL); //呼叫到瀏覽器原生的 history 物件
		//history.pushState(null, null, document.URL);
		window.addEventListener('popstate', handlePopState);
  })

	onUnmounted(() => {
    console.log('handlePopState unmounted');

		window.removeEventListener('popstate', handlePopState);
	});

  return {
    showBackWarning,
    snackbar,
    snackbar_info,
    snackbar_color,

    handlePopState,
    showSnackbar
  }
}
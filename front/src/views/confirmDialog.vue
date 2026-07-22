<template>
  <v-dialog  v-model="isOpen" :max-width="props.maxWidth">
    <v-card>
      <v-toolbar dense flat color="purple-lighten-1">
        <v-toolbar-title class="text-body-2 font-weight-bold text-center w-100">
          {{ opts.title }}
        </v-toolbar-title>
      </v-toolbar>

      <v-card-text
        v-html="opts.message"
        class="confirm-message"
      />

      <v-card-actions class="justify-center">
        <v-btn
          variant="flat"
          color="#ff4444"
          class="mx-2"
          style="width:70px"
          @click="close(false)"
        >
          <v-icon start size="24px" color="#ffffff">mdi-close-circle-outline</v-icon>
          <span style="color:#ffffff">{{ opts.cancelText }}</span>
        </v-btn>

        <v-btn
          variant="flat"
          color="#00c851"
          class="mx-2"
          style="width:70px"
          @click="close(true)"
        >
          <v-icon start size="24px" color="#ffffff">mdi-check-circle-outline</v-icon>
          <span style="color:#ffffff">{{ opts.okText }}</span>
        </v-btn>
      </v-card-actions>

    </v-card>
  </v-dialog>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  maxWidth: {
    type: [Number, String],
    default: 320
  }
})

const isOpen = ref(false)
const opts = ref({
  title: '確認',
  message: '確定要執行嗎？',
  okText: '確定',
  cancelText: '取消',
})

let _resolve = null

function open(options = {}) {
  opts.value = { ...opts.value, ...options }
  isOpen.value = true
  return new Promise(resolve => { _resolve = resolve })
}

function close(ok) {
  isOpen.value = false
  _resolve?.(ok)
  _resolve = null
}

defineExpose({ open })
</script>

<style lang="scss" scoped>

* {
  font-family:
    "Microsoft JhengHei",
    "微軟正黑體",
    "Noto Sans TC",
    sans-serif;
}

.confirm-message{
  white-space: pre-line;
  line-height: 1.8;
  font-size:16px;
}

</style>
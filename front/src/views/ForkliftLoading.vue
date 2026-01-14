<template>
  <!-- 加工完成送出中動畫：箱子 + 堆高機 -->
  <div
    class="forklift-wrap"
    :style="wrapStyle"
  >
    <div class="forklift-moving">
      <!-- 小箱子 -->
      <v-icon class="forklift-box" size="18" color="orange">
        mdi-package-variant
      </v-icon>

      <!-- 堆高機 -->
      <v-icon class="forklift-icon" size="22" color="blue">
        mdi-forklift
      </v-icon>
    </div>

    <!-- 軌道（可選） -->
    <div class="forklift-track"></div>
  </div>
</template>

<script setup>
import { ref, defineComponent, defineProps, computed, watch, onMounted, onBeforeUnmount, onUnmounted, onBeforeMount, onDeactivated } from 'vue';

//=== component name ==
defineComponent({ name: 'PickReportForProcessBegin' });

/**
 * props：讓你可以微調位置、寬度
 */
const props = defineProps({
  width: { type: Number, default: 200 },
  top: { type: Number, default: 30 },
  left: { type: Number, default: 180 },
})

const wrapStyle = computed(() => ({
  position: 'relative',
  width: props.width + 'px',
  height: '28px',
  top: props.top + 'px',
  left: props.left + 'px',
}))
</script>

<style scoped>
.forklift-wrap {
  overflow: hidden;
}

/* 軌道 */
.forklift-track {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 6px;
  height: 2px;
  background: currentColor;
  opacity: 0.25;
}

/* 整組一起移動 */
.forklift-moving {
  position: absolute;
  left: 0;
  top: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  animation: forklift-move 1.6s linear infinite;
}

/* 箱子微晃 */
.forklift-box {
  animation: box-bounce 0.6s ease-in-out infinite alternate;
}

/* 堆高機微震 */
.forklift-icon {
  animation: forklift-bump 0.4s linear infinite;
}

/* 左 → 右 */
@keyframes forklift-move {
  0% {
    transform: translateX(-30px);
    opacity: 0;
  }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% {
    transform: translateX(190px);
    opacity: 0;
  }
}

@keyframes box-bounce {
  from { transform: translateY(2px); }
  to   { transform: translateY(0); }
}

@keyframes forklift-bump {
  0%   { transform: translateY(0); }
  50%  { transform: translateY(1px); }
  100% { transform: translateY(0); }
}
</style>

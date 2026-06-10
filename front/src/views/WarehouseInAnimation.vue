<template>
<!--
  <div
    class="warehouse-animation-wrap"
    :style="cssVars"
  >
-->
  <div
    class="warehouse-animation-wrap"
		:style="{
			...cssVars,
			left: `${left}px`
		}"
  >
    <svg
      class="warehouse-animation-svg"
      viewBox="0 0 420 220"
      xmlns="http://www.w3.org/2000/svg"
    >
      <rect width="420" height="220" rx="18" fill="#f4f7fb" />

      <!-- 地板 -->
      <rect
        :x="floorX"
        y="170"
        :width="floorWidth"
        height="8"
        rx="4"
        fill="#cfd8dc"
      />

      <!-- 倉庫 -->
      <g>
        <rect x="255" y="50" width="120" height="120" rx="10" fill="#607d8b" />
        <line x1="275" y1="50" x2="275" y2="170" stroke="#78909c" stroke-width="3" />
        <line x1="295" y1="50" x2="295" y2="170" stroke="#78909c" stroke-width="3" />
        <line x1="315" y1="50" x2="315" y2="170" stroke="#78909c" stroke-width="3" />
        <line x1="335" y1="50" x2="335" y2="170" stroke="#78909c" stroke-width="3" />

        <rect x="290" y="90" width="50" height="80" rx="4" fill="#263238" />
        <rect class="warehouse-door" x="290" y="90" width="50" height="80" rx="4" fill="#90a4ae" />

        <text x="315" y="78" text-anchor="middle" font-size="16" font-weight="700" fill="white">
          入庫區
        </text>
      </g>

      <!-- 箭頭 -->
      <g class="warehouse-arrow" fill="#1976d2">
        <rect x="145" y="113" width="78" height="12" rx="6" />
        <polygon points="223,101 252,119 223,137" />
      </g>

      <!-- 箱子 -->
      <g class="warehouse-box">
        <rect x="55" y="105" width="64" height="55" rx="5" fill="#ffb74d" stroke="#ef6c00" stroke-width="3" />
        <line x1="55" y1="125" x2="119" y2="125" stroke="#ef6c00" stroke-width="3" />
        <line x1="87" y1="105" x2="87" y2="160" stroke="#ef6c00" stroke-width="3" />
        <text x="87" y="145" text-anchor="middle" font-size="15" font-weight="700" fill="#5d4037">
          入庫
        </text>
      </g>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  startX: {
    type: Number,
    default: -120,
  },
  timeX: {
    type: Number,
    default: 3,
  },
  lengthX: {
    type: Number,
    default: 520,
  },
  floorX: {
    type: Number,
    default: -270,
  },
  floorWidth: {
    type: Number,
    default: 660,
  },
  left: {
    type: Number,
    default: 0
	},
})

const cssVars = computed(() => ({
  '--start-x': `${props.startX}px`,
  '--move-time': `${props.timeX}s`,
  '--move-length': `${props.lengthX}px`,
}))
</script>

<style scoped>
/*
.warehouse-animation-wrap {
  width: 300px;
  height: 80px;
  overflow: visible;
  pointer-events: none;
}
*/

/*
.warehouse-animation-wrap {
  position: fixed;

  top: 120px;

  z-index: 9999;
}
*/
.warehouse-animation-wrap {
  width: 300px;
  height: 80px;
  overflow: visible;
  pointer-events: none;
}

.warehouse-animation-svg {
  width: 300px;
  height: 80px;
  display: block;
  overflow: visible;
}

.warehouse-box {
  animation: warehouseMoveBox var(--move-time) ease-in-out infinite;
}

.warehouse-arrow {
  animation: warehouseArrowBlink 1.1s ease-in-out infinite;
}

.warehouse-door {
  animation: warehouseDoorOpen var(--move-time) ease-in-out infinite;
  transform-origin: 315px 105px;
}

@keyframes warehouseMoveBox {
  0% {
    transform: translateX(var(--start-x));
    opacity: 1;
  }

  55% {
    transform: translateX(calc(var(--start-x) + var(--move-length)));
    opacity: 1;
  }

  60% {
    transform: translateX(calc(var(--start-x) + var(--move-length)));
    opacity: 0;
  }

  100% {
    transform: translateX(var(--start-x));
    opacity: 0;
  }
}

@keyframes warehouseArrowBlink {
  0%, 100% {
    opacity: .3;
  }

  50% {
    opacity: 1;
  }
}

@keyframes warehouseDoorOpen {
  0%, 35% {
    transform: scaleX(1);
  }

  55%, 80% {
    transform: scaleX(.2);
  }

  100% {
    transform: scaleX(1);
  }
}
</style>
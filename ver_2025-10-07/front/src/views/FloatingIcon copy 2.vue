<template>
  <div class="is-flex is-justify-content-center is-align-items-center">
    <div class="options box container">
      <button
        :class="['button is-info', { 'is-light': !isEnabled }]"
        @click="toggleDraggable"
      >
        Drag is {{ isEnabled ? "enabled" : "disabled" }}
      </button>
      <button
        :class="['button is-info', { 'is-light': !isRestricted }]"
        @click="toggleRestriction"
      >
        Dropzone zone restriction is {{ isRestricted ? "enabled" : "disabled" }}
      </button>
    </div>

    <div class="box container dropzone">
      <button class="button is-primary draggable" :style="getPosition">
				<i class="fa-solid fa-bars fa-fade fa-xl" style="color: #74C0FC;"></i>
      </button>
    </div>
  </div>
</template>

<script setup>
import { reactive, computed, onMounted, defineComponent } from "vue";
import interact from "interactjs";

//=== component name ==
defineComponent({
  name: 'FloatingIcon'
});

//=== data ===
const state = reactive({
  isEnabled: true,
  isRestricted: true,
  item: {
    x: 0,
    y: 0,
  },
});

//=== computed ===
const getPosition = computed(() => {
  return `transform: translate(${state.item.x}px, ${state.item.y}px)`;
});

//=== mounted ===
onMounted(() => {
  initDraggable();
});

//=== method ===
const initDraggable = () => {
  let restriction = null;
  if (state.isRestricted) {
    restriction = {
      restriction: ".dropzone",
      elementRect: { top: 0, left: 0, bottom: 1, right: 1 },
    };
  }

  interact(".draggable").draggable({
    restrict: restriction,
    onmove: (e) => {
      state.item.x += e.dx;
      state.item.y += e.dy;
    },
  });
};

const toggleDraggable = () => {
  if (state.isEnabled) {
    interact(".draggable").unset();
  } else {
    initDraggable();
  }
  state.isEnabled = !state.isEnabled;
};

const toggleRestriction = () => {
  state.isRestricted = !state.isRestricted;
  interact(".draggable").unset();
  initDraggable();
};

</script>

<style lang="scss" scoped>

.options {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  margin: auto !important;
  z-index: 10;
}

.dragzone, .dropzone {
  height: 50vh;
}

.draggable {
  touch-action: none;
  user-select: none;
}

.button + .button {
  margin-left: 0.5rem;
}
</style>

<template>
  <div>

  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, defineComponent } from 'vue';
import { eventBus } from '../mixins/enentBus.js';

//=== component name ==
defineComponent({
  name: 'Receiver'
});

const eventData = ref(null);

//=== method ===
const handleEvent = (data) => {
  eventData.value = data;
  console.log("eventData:", eventData.value)
};

//=== mounted ===
onMounted(() => {
  eventBus.on('myEvent', handleEvent);
});

onUnmounted(() => {
  eventBus.off('myEvent', handleEvent);
});

</script>

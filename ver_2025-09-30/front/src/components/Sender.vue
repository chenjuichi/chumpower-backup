<template>
    <div>

    </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, defineComponent } from 'vue';
import eventBus from '../mixins/enentBus.js';

//=== component name ==
defineComponent({
  name: 'Sender'
});

//=== method ===
const sendEvent = () => {
  eventBus.emit('idleTimeout');
};

//=== mounted ===
onMounted(() => {
    sendEvent();
});
</script>
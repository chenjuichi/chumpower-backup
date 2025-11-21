<template>
    <div>
      <input
        type="checkbox"
        v-model="isChecked"
        @click="handleChange"
      />
      <label>{{ label }}</label>
    </div>
  </template>

  <script setup>
  import { ref, defineComponent } from 'vue';

  //=== component name ==
  defineComponent({
    name: 'VCheckbox'
  });

  //=== props ==
  const props = defineProps({
    modelValue: Boolean,
    label: String
  });

  const isChecked = ref(props.modelValue);

  const emit = defineEmits(['update:modelValue']);

  const handleChange = () => {
    console.log("VCheckbox.vue, handleChange(),", !isChecked.value)
    emit('update:modelValue', !isChecked.value);
  };
  </script>

  <style scoped>

  </style>

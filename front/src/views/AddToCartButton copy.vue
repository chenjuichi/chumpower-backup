<template>
  <button
    ref="btnRef"
    class="add-to-cart"
    :class="{ active: isAnimating }"
    @pointerdown="pressButton"
    @click="handleClick"
  >
    <span>{{ text }}</span>

    <!--<div class="shirt">👕</div>-->
    <div class="package">📦</div>

    <div class="cart">
      <svg viewBox="0 0 36 26">
        <path
          d="M1 2.5H6L10 18.5H25.5L28.5 7.5L7.5 7.5"
          class="shape"
        />
        <circle cx="11.5" cy="23" r="2" class="wheel" />
        <circle cx="24" cy="23" r="2" class="wheel" />
        <path d="M14.5 13.5L16.5 15.5L21.5 10.5" class="tick" />
      </svg>
    </div>
  </button>
</template>

<script setup>
import { ref } from 'vue'
import gsap from 'gsap'

const props = defineProps({
  text: {
    type: String,
    default: 'Add to cart'
  }
})

const emit = defineEmits(['added'])

const btnRef = ref(null)
const isAnimating = ref(false)

const pressButton = () => {
  if (isAnimating.value) return

  gsap.to(btnRef.value, {
    '--background-scale': 0.97,
    duration: 0.15
  })
}

const handleClick = async (e) => {
  e.preventDefault()
  if (isAnimating.value) return

  isAnimating.value = true
  const btn = btnRef.value

  gsap.set(btn, {
    overflow: 'visible',
    '--cart-x': '-48px',
    '--cart-y': '0px',
    '--cart-scale': 0.75,
    '--cart-rotate': '0deg',
    '--shirt-y': '-16px',
    '--shirt-scale': 0,
    '--text-o': 1,
    '--text-x': '12px',
    '--cart-tick-offset': '10px'
  })

  const tl = gsap.timeline({
    onComplete: () => {
      isAnimating.value = false
      emit('added')

      gsap.set(btn, {
        overflow: '',
        clearProps: 'all'
      })
    }
  })

  tl.to(btn, {
    '--background-scale': 0.97,
    duration: 0.15
  })
    .to(btn, {
      '--background-scale': 1,
      duration: 0.6,
      ease: 'elastic.out(1, .6)'
    })
    .to(btn, {
      '--text-o': 0,
      duration: 0.2
    }, 0)
    .to(btn, {
      '--shirt-scale': 1,
      '--shirt-y': '-42px',
      '--cart-x': '0px',
      '--cart-scale': 1,
      duration: 0.4,
      ease: 'power1.in'
    }, 0.05)

    .to(btn, {
      '--shirt-y': '-4px',
      '--shirt-scale': 0.9,
      duration: 0.25
    })
    .to(btn, {
      '--shirt-scale': 0,
      duration: 0.2
    })
    .to(btn, {
      '--cart-tick-offset': '0px',
      duration: 0.2
    })
    .to(btn, {
      '--cart-x': '52px',
      '--cart-rotate': '-15deg',
      duration: 0.2
    })
    .to(btn, {
      '--cart-x': '104px',
      '--cart-rotate': '0deg',
      duration: 0.2
    })
    .set(btn, {
      '--text-x': '0px',
      '--cart-x': '-104px'
    })
    .to(btn, {
      '--text-o': 1,
      '--text-x': '12px',
      '--cart-x': '-48px',
      '--cart-scale': 0.75,
      duration: 0.25
    })
}
</script>

<style lang="scss" scoped>
.add-to-cart {
  --background-default: #17171b;
  --background-hover: #0a0a0c;
  --background-scale: 1;

  --text-color: #fff;
  --text-o: 1;
  --text-x: 12px;

  --cart: #fff;
  --cart-x: -48px;
  --cart-y: 0px;
  --cart-rotate: 0deg;
  --cart-scale: 0.75;
  --cart-tick-offset: 10px;

  --shirt-y: -16px;
  --shirt-scale: 0;

  width: 164px;
  padding: 12px 0;
  border: none;
  outline: none;
  background: none;
  cursor: pointer;
  position: relative;
  font-family: inherit;
}

.add-to-cart::before {
  content: "";
  position: absolute;
  inset: 0;
  border-radius: 5px;
  background: var(--background, var(--background-default));
  transform: scaleX(var(--background-scale));
  transition: background 0.25s;
}

.add-to-cart:not(.active):hover {
  --background: var(--background-hover);
}

.add-to-cart span {
  display: block;
  position: relative;
  top: 2px;
  z-index: 2;
  color: var(--text-color);
  font-size: 14px;
  font-weight: 600;
  line-height: 24px;
  opacity: var(--text-o);
  transform: translateX(var(--text-x));
}
/*
.shirt {
  position: absolute;
  left: 50%;
  top: 10px;
  z-index: 3;
  font-size: 22px;
  margin-left: -11px;
  transform:
    translateY(var(--shirt-y))
    scale(var(--shirt-scale));
  pointer-events: none;
}
*/
.package {
  position: absolute;
  left: 50%;
  top: 10px;
  z-index: 3;
  font-size: 22px;
  /*margin-left: -11px;*/
  margin-left: -16px;
  transform:
    translateY(var(--shirt-y))
    scale(var(--shirt-scale));
  pointer-events: none;
}

.cart {
  position: absolute;
  left: 50%;
  top: 10px;
  z-index: 3;
  width: 36px;
  height: 26px;
  margin-left: -18px;
  transform:
    translate(var(--cart-x), var(--cart-y))
    rotate(var(--cart-rotate))
    scale(var(--cart-scale));
  pointer-events: none;
}

.cart svg {
  width: 36px;
  height: 26px;
  fill: none;
  stroke: var(--cart);
  stroke-width: 2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.cart .wheel {
  fill: none;
  stroke-width: 1.5;
}

.cart .tick {
  stroke: #ff328b;
  stroke-dasharray: 10px;
  stroke-dashoffset: var(--cart-tick-offset);
}
</style>
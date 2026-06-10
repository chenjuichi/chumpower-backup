<template>
	<button
		ref="btnRef"
		class="add-to-cart"
		:disabled="disabled"
		:class="{	active:isAnimating,	disabled:disabled	}"
		@pointerdown="pressButton"
		@click="handleClick"
	>
    <span>{{ text }}</span>

    <div class="package">📦</div>

    <div class="cart">
<svg viewBox="0 0 60 40">

  <!-- 平板 -->
  <rect
    x="16"
    y="18"
    width="36"
    height="8"
    rx="2"
    class="platform"
  />

  <!-- 左側扶手 -->
  <path
    d="M16 18 L16 4"
    class="handle"
  />

  <path
    d="M16 4 L4 4"
    class="handle"
  />

  <!-- 輪子 -->
  <circle cx="24" cy="32" r="4" class="wheel" />
  <circle cx="48" cy="32" r="4" class="wheel" />

  <!-- 打勾 -->
  <path
    d="M22 13 L28 19 L38 8"
    class="tick"
  />
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
    default: '入庫登記'
  },

	disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['added'])

const btnRef = ref(null)
const isAnimating = ref(false)

const pressButton = () => {
  if (props.disabled) return
  if (isAnimating.value) return

  gsap.to(btnRef.value, {
    '--background-scale': 0.97,
    duration: 0.15
  })
}

const handleClick = async (e) => {
	if (props.disabled) return

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
    '--cart-tick-offset': '30px',
		'--tick-opacity': 0,
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
		/*
    .to(btn, {
      '--shirt-y': '-4px',
      '--shirt-scale': 0.9,
      duration: 0.25
    })
		*/
		.to(btn, {
			'--shirt-y': '-8px',
			'--shirt-scale': 0.75,
			duration: 0.25
		})

    .to(btn, {
      '--shirt-scale': 0,
      duration: 0.2
    })
    .to(btn, {
      '--cart-tick-offset': '0px',
			'--tick-opacity': 1,
      duration: 0.25
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
	--background-default: transparent;
  --background-hover: rgba(25,118,210,.08);

  --text-color: #1976d2;
  --cart: #1976d2;

  //--background-default: #17171b;
  //--background-hover: #0a0a0c;
  --background-scale: 1;

  //--text-color: #fff;
  --text-o: 1;
  --text-x: 12px;

  //--cart: #fff;
  --cart-x: -48px;
  --cart-y: 0px;
  --cart-rotate: 0deg;
  --cart-scale: 0.75;
  --cart-tick-offset: 30px;
	--tick-opacity:0;

  --shirt-y: -16px;
  --shirt-scale: 0;

  //width: 164px;
  width: 150px;
	height: 40px;
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
  //border-radius: 5px;
  background: var(--background, var(--background-default));
  transform: scaleX(var(--background-scale));
  //transition: background 0.25s;

	border-radius: 4px;
  border: 1px solid #1976d2;
  transition:
    background .25s,
    border-color .25s;
}
/*
.add-to-cart:not(.active):hover {
  //--background: var(--background-hover);
	--background: rgba(25,118,210,.08);
}
*/
.add-to-cart:not(.active):not(.disabled):hover {
  --background: rgba(25,118,210,.08);
}

.add-to-cart span {
  display: block;
  position: relative;
  //top: 2px;
  top: -1px;
  z-index: 2;
  //color: var(--text-color);
  font-size: 16px;
  //font-weight: 600;
	color: #1976d2;
  font-weight: 700;
  line-height: 24px;
  opacity: var(--text-o);
  transform: translateX(var(--text-x));
}

.add-to-cart.disabled {
  cursor: not-allowed;

  --text-color: #9e9e9e;
  --cart: #bdbdbd;
}

.add-to-cart.disabled::before {
  border-color: #bdbdbd;
  background: #f5f5f5;
}

.add-to-cart.disabled span {
  color: #9e9e9e !important;
}

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
  //top: 2px;
	top: 1px;				//車子起始垂直位置
  z-index: 3;

  width: 60px;
  height: 40px;

  margin-left: -30px;

  transform:
    translate(var(--cart-x), var(--cart-y))
    rotate(var(--cart-rotate))
    scale(var(--cart-scale));

  pointer-events: none;
}

.cart svg {
  width: 60px;
  height: 40px;

  fill: none;
  stroke: var(--cart);
  stroke-width: 2.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.platform {
  fill: rgba(255,255,255,.15);
}

.handle {
  stroke: var(--cart);
}

.cart .wheel {
  fill: none;
  stroke-width: 2;
}


.cart .tick {
  stroke: #4caf50;
  stroke-width: 3;

  fill: none;

  stroke-dasharray: 30;
  stroke-dashoffset: var(--cart-tick-offset);

  opacity: var(--tick-opacity);
}

.add-to-cart.disabled {
  cursor: not-allowed;

  --text-color: #9e9e9e;
  --cart: #bdbdbd;
}

.add-to-cart.disabled::before {
  border-color: #bdbdbd;
  background: #f5f5f5;
}
</style>
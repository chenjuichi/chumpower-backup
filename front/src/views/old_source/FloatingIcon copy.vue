<template>
  <div ref="menuContainer" class="floating-icon-container">
    <component :is="activeComponent" v-if="activeComponent"></component>
  </div>
</template>

<script setup>
import { ref, defineComponent, onMounted } from 'vue';
import anime from 'animejs/lib/anime.js';

// 導入組件
import AComponent from '../VCheckbox.vue';
import BComponent from '../VCheckbox.vue';
import CComponent from '../VCheckbox.vue';
import DComponent from '../VCheckbox.vue';

// 設定組件名稱
defineComponent({
  name: 'FloatingIcon',
});

// 控制當前激活的組件
const menuContainer = ref(null);
const activeComponent = ref(null);

// 點擊圖標時執行的操作
const handleIconClick = (index) => {
  switch (index) {
    case 2:
      activeComponent.value = AComponent;
      break;
    case 3:
      activeComponent.value = BComponent;
      break;
    case 4:
      activeComponent.value = CComponent;
      break;
    case 5:
      activeComponent.value = DComponent;
      break;
    default:
      activeComponent.value = null;
  }
};

// Item 物件工廠函數
const createItem = (icon, backgroundColor = 'white', clickHandler = null) => {
  const element = document.createElement('div');
  element.style.backgroundColor = backgroundColor;

  // 創建並設置 MDI 圖標
  const iconElement = document.createElement('i');
  iconElement.classList.add('mdi', icon);
  element.appendChild(iconElement);

  return {
    element,
    prev: null,
    next: null,
    isMoving: false,
    moveTo(targetItem) {
      anime({
        targets: this.element,
        left: targetItem.element.style.left,
        top: targetItem.element.style.top,
        duration: 700,
        elasticity: 500,
      });

      if (this.next) {
        this.next.moveTo(targetItem);
      }
    },
    updatePosition() {
      anime({
        targets: this.element,
        left: this.prev.element.style.left,
        top: this.prev.element.style.top,
        duration: 80,
      });

      if (this.next) {
        this.next.updatePosition();
      }
    },
  };
};

// Menu 物件工廠函數
const createMenu = (menuContainer) => {
  const element = menuContainer;
  let first = null;
  let last = null;
  let status = 'closed';

  const add = (item) => {
    if (!first) {
      first = item;
      last = item;

      first.element.addEventListener('dragstart', () => {
        close();
        first.isMoving = true;
      });

      first.element.addEventListener('dragend', () => {
        first.isMoving = false;
        first.next?.moveTo(first);
      });

      // 第一個元素可拖曳
      first.element.draggable = true;
    } else {
      last.next = item;
      item.prev = last;
      last = item;

      // 其他元素不可拖曳
      last.element.draggable = false;
    }

    element.appendChild(item.element);
  };

  const open = () => {
    status = 'open';
    let current = first.next;
    let iterator = 1;

    while (current) {
      anime({
        targets: current.element,
        left: `${parseInt(first.element.style.left, 10) + iterator * 50}px`,
        top: first.element.style.top,
        duration: 500,
      });
      iterator++;
      current = current.next;
    }
  };

  const close = () => {
    status = 'closed';
    let current = first.next;

    while (current) {
      anime({
        targets: current.element,
        left: first.element.style.left,
        top: first.element.style.top,
        duration: 500,
      });
      current = current.next;
    }
  };

  const click = () => {
    if (status === 'closed') {
      open();
    } else {
      close();
    }
  };

  return { element, add, open, close, click };
};

onMounted(() => {
  if (!menuContainer.value) return;

  const menu = createMenu(menuContainer.value);

  // 建立圖標
  const item1 = createItem('mdi-menu');
  const item2 = createItem('mdi-account', '#FF5C5C', () => handleIconClick(2));
  const item3 = createItem('mdi-page-layout-footer', '#5CD1FF', () => handleIconClick(3));
  const item4 = createItem('mdi-palette', '#FFF15C', () => handleIconClick(4));
  const item5 = createItem('mdi-link-variant', '#64F592', () => handleIconClick(5));

  menu.add(item1);
  menu.add(item2);
  menu.add(item3);
  menu.add(item4);
  menu.add(item5);

  // 初始化菜單
  menuContainer.value.style.position = 'absolute';
  menuContainer.value.style.top = `${window.scrollY + 300}px`;
  //menuContainer.value.style.top = '300px'; // 固定到 300px
  //menuContainer.value.style.left = '1050px'; // 固定到 1050px

  window.addEventListener('scroll', () => {
    menuContainer.value.style.top = `${window.scrollY + 10}px`;
  });

  setTimeout(() => {
    menu.open();
    setTimeout(() => {
      menu.close();
    }, 1000);
  }, 50);
});
</script>

<style scoped>
@import url('https://fonts.googleapis.com/css?family=Noto+Sans+TC:400,500&display=swap&subset=chinese-traditional');
@import url('https://fonts.googleapis.com/earlyaccess/cwtexyen.css');

i {
  font-size: 24px;
  color: #222222;
}

.floating-icon-container {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 19 !important;
  width: 40px;
  height: 40px;
  background-color: #f0f0f0;
  border-radius: 50%;
}
</style>

import { computed } from 'vue';

// MenuConstants.js
export const empPermMapping = {
  4: '員工',
  3: '主管',
  2: '管理人員',
  1: '系統人員',
};

export const roleMappings = {
  '系統人員': Array.from({ length: 26 }, (_, i) => i + 1),
  '管理人員': [1, 2, 3, 4, 5, 21, 22, 23, 24, 25],
  '主管': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25],
  '員工': [6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]
};

export const menuData = [
  {
    id: 1,
    text: '在製品生產資訊',
    to: '',
    isEnabled: false,
    isSegment: false,
    children: [
      { id: 2, text: "1.備料區", to: '/a', isEnabled: false, isSegment: false },
      { id: 3, text: "2.加工區", to: '/b', isEnabled: false, isSegment: false },
      { id: 4, text: "3.組裝區", to: '/c', isEnabled: false, isSegment: false },
      { id: 5, text: "4.出貨區", to: '/d', isEnabled: false, isSegment: false },
    ]
  },
  {
    id: 6,
    text: '備料清單',
    to: '',
    isEnabled: true,
    isSegment: false,
    children: [
      { id: 7, text: "1.加工區", to: '/e', isEnabled: false, isSegment: false },
      { id: 8, text: "2.組裝區", to: '/f', isEnabled: false, isSegment: false },
    ]
  },
  {
    id: 9,
    text: '組裝生產',
    to: '',
    isEnabled: false,
    isSegment: false,
    children: [
      { id: 10, text: "1.領料生產報工", to: '/g01', isEnabled: false, isSegment: false },
      { id: 11, text: "2.完成生產報工", to: '/g01c', isEnabled: false, isSegment: false },
      { id: 12, text: "3.異常填報", to: '/g01d', isEnabled: false, isSegment: false },
    ]
  },
  {
    id: 13,
    text: '成品入庫',
    to: '',
    isEnabled: false,
    isSegment: false,
    children: [
      { id: 14, text: "1.檢料生產報工", to: '/g1', isEnabled: false, isSegment: false },
      { id: 15, text: "2.完成生產報工", to: '/g2', isEnabled: false, isSegment: false },
      { id: 16, text: "3.異常填報", to: '/g3', isEnabled: false, isSegment: false },
    ]
  },
  {
    id: 17,
    text: '加工生產',
    to: '',
    isEnabled: false,
    isSegment: false,
    children: [
      { id: 18, text: "1.領料生產報工", to: '/h1', isEnabled: false, isSegment: false },
      { id: 19, text: "2.完成生產報工", to: '/h2', isEnabled: false, isSegment: false },
      { id: 20, text: "3.異常填報", to: '/h3', isEnabled: false, isSegment: false },
    ]
  },
  {
    id: 21,
    text: '系統設定',
    to: '',
    isEnabled: false,
    isSegment: false,
    children: [
      { id: 22, text: "1.機台資料維護", to: '/j1', isEnabled: false, isSegment: false },
      { id: 23, text: "2.組裝站資料維護", to: '/j2', isEnabled: false, isSegment: false },
      { id: 24, text: "3.加工異常原因維護", to: '/j3', isEnabled: false, isSegment: false },
      { id: 25, text: "4.組裝異常原因維護", to: '/j4', isEnabled: false, isSegment: false },
      { id: 26, text: "5.人員資料維護", to: '/employer', isEnabled: false, isSegment: false },
    ]
  }
];

export function flattenMenuData(menuData) {
  return menuData.reduce((flatMenus, item) => {
    flatMenus.push({ text: item.text, to: item.to, isEnabled: item.isEnabled, isSegment: item.isSegment });
    if (item.children) {
      item.children.forEach(child => {
        flatMenus.push({ text: child.text, to: child.to, isEnabled: child.isEnabled, isSegment: child.isSegment });
      });
    }
    return flatMenus;
  }, []);
}

export function generateTreeViewItems(menuData) {
  return menuData.map(item => ({
    id: item.id,
    name: item.text,
    children: item.children ? item.children.map(child => ({
      id: child.id,
      name: child.text,
    })) : []
  }));
}

export const flatItems = computed(() => flattenMenuData(menuData));
export const treeViewItems = computed(() => generateTreeViewItems(menuData));

/*
export const menus = [
  {
    id: 1,
    text: '在製品生產',
    to: '',
    isEnabled: false,
    children: [
      { id: 2, text: "1.備料區", to: '/a', isEnabled: false },
      { id: 3, text: "2.加工區", to: '/b', isEnabled: false },
      { id: 4, text: "3.組裝區", to: '/c', isEnabled: false },
      { id: 5, text: "4.出貨區", to: '/d', isEnabled: false },
    ]
  },
  {
    id: 6,
    text: '備料清單',
    to: '',
    isEnabled: true,
    children: [
      { id: 7, text: "1.加工區", to: '/a', isEnabled: false },
      { id: 8, text: "2.組裝區", to: '/b', isEnabled: false },
    ]
  },
  {
    id: 9,
    text: '組裝生產',
    to: '',
    isEnabled: false,
    children: [
      { id: 10, text: "1.領料生產報工", to: '/d', isEnabled: false },
      { id: 11, text: "2.完成生產報工", to: '/d', isEnabled: false },
      { id: 12, text: "3.異常填報", to: '/d', isEnabled: false },
    ]
  },
  {
    id: 13,
    text: '成品入庫',
    to: '',
    isEnabled: false,
    children: [
      { id: 14, text: "1.檢料生產報工", to: '/d', isEnabled: false },
      { id: 15, text: "2.完成生產報工", to: '/d', isEnabled: false },
      { id: 16, text: "3.異常填報", to: '/d', isEnabled: false },
    ]
  },
  {
    id: 17,
    text: '加工生產',
    to: '',
    isEnabled: false,
    children: [
      { id: 18, text: "1.領料生產報工", to: '/d', isEnabled: false },
      { id: 19, text: "2.完成生產報工", to: '/d', isEnabled: false },
      { id: 20, text: "3.異常填報", to: '/d', isEnabled: false },
    ]
  },
  {
    id: 21,
    text: '系統設定',
    to: '',
    isEnabled: false,
    children: [
      { id: 22, text: "1.機台資料維護", to: '/a', isEnabled: false },
      { id: 23, text: "2.組裝站資料維護", to: '/b', isEnabled: false },
      { id: 24, text: "3.加工異常原因維護", to: '/c', isEnabled: false },
      { id: 25, text: "4.組裝異常原因維護", to: '/d', isEnabled: false },
      { id: 26, text: "5.人員資料維護", to: '/employer', isEnabled: false },
    ]
  }
];
*/
/*
export const menus = [
  // menu item 1
  { //menu 1
    text: '在製品生產',
    to: '',
    isEnabled: false,
  },
  { //menu 2
    text: '1.備料區',
    to: '/a',
    isEnabled: false,
  },
  { //menu 3
    text: '2.加工區',
    to: '/b',
    isEnabled: false,
  },
  { //menu 4
    text: '3.組裝區',
    to: '/c',
    isEnabled: false,
  },
  { //menu 5
    text: '4.出貨區',
    to: '/d',
    isEnabled: false,
  },
  // menu item 2
  { //menu 6
    text: '備料清單',
    to: '',
    isEnabled: true,
  },
  { //menu 7
    text: '1.加工區',
    to: '/a',
    isEnabled: false,
  },
  { //menu 8
    text: '2.組裝區',
    to: '/b',
    isEnabled: false,
  },
  // menu item 3
  { //menu 9
    text: '組裝生產',
    to: '/c',
    isEnabled: false,
  },
  { //menu 10
    text: '1.領料生產報工',
    to: '/d',
    isEnabled: false,
  },
  { //menu 11
    text: '2.完成生產報工',
    to: '/d',
    isEnabled: false,
  },
  { //menu 12
    text: '3.異常填報',
    to: '/d',
    isEnabled: false,
  },
  // menu item 3
  { //menu 13
    text: '成品入庫',
    to: '/c',
    isEnabled: false,
  },
  { //menu 14
    text: '1.檢料生產報工',
    to: '/d',
    isEnabled: false,
  },
  { //menu 15
    text: '2.完成生產報工',
    to: '/d',
    isEnabled: false,
  },
  { //menu 16
    text: '3.異常填報',
    to: '/d',
    isEnabled: false,
  },
  // menu item 4
  { //menu 17
    text: '加工生產',
    to: '',
    isEnabled: false,
  },
  { //menu 18
    text: '1.領料生產報工',
    to: '/d',
    isEnabled: false,
  },
  { //menu 19
    text: '2.完成生產報工',
    to: '/d',
    isEnabled: false,
  },
  { //menu 20
    text: '3.異常填報',
    to: '/d',
    isEnabled: false,
  },
  // menu item 5
  { //menu 21
    text: '系統設定',
    to: '',
    isEnabled: false,
  },
  { //menu 22
    text: '1.機台資料維護',
    to: '/a',
    isEnabled: false,
  },
  { //menu 23
    text: '2.組裝站資料維護',
    to: '/b',
    isEnabled: false,
  },
  { //menu 24
    text: '3.加工異常原因維護',
    to: '/c',
    isEnabled: false,
  },
  { //menu 25
    text: '4.組裝異常原因維護',
    to: '/d',
    isEnabled: false,
  },
  { //menu 26
    text: '5.人員資料維護',
    to: '/employer',
    isEnabled: false,
  },
];
*/

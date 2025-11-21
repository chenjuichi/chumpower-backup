import { h } from "vue";
import loginIcon from "./icon.vue";

/** @typedef {import("vuetify").IconSet} IconSet */
/** @typedef {import("vuetify").IconProps} IconProps */

const customSvgNameToComponent = {
  loginIcon,
};

/** @type {IconSet} */
const customSVGs = {
  component: (props) => h(customSvgNameToComponent[props.icon]),
};

export { customSVGs /* aliases */ };
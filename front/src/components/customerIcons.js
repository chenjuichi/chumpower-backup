//customSvgs.js
import { h } from "vue";
import type { IconSet, IconProps } from "vuetify";
import loginIcon from "./icon.vue";

const customSvgNameToComponent: any = {
  loginIcon,
};

const customerIcons: IconSet = {
  component: (props: IconProps) => h(customSvgNameToComponent[props.icon]),
};

export { customerIcons /* aliases */ };
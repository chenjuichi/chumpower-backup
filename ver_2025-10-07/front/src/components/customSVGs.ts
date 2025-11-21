import { h } from "vue";
import type { IconSet, IconAliases, IconProps } from "vuetify";
import loginIcon from "./icon.vue";

const customSvgNameToComponent: any = {
  loginIcon,
};

const customSVGs: IconSet = {
  component: (props: IconProps) => h(customSvgNameToComponent[props.icon]),
};

export { customSVGs /* aliases */ };

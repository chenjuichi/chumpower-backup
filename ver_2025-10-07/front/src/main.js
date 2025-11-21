import { createApp } from 'vue'
import App from './App.vue'
import { router } from './router'
import store from './store'

// Vuetify
import 'vuetify/styles'
import { createVuetify } from 'vuetify'
import * as components from 'vuetify/components'
import * as directives from 'vuetify/directives'

// for bootstrap
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap/dist/js/bootstrap.bundle.min.js';

import { mdi } from 'vuetify/lib/iconsets/mdi';
import { fa } from 'vuetify/lib/iconsets/fa';
import '@mdi/font/css/materialdesignicons.css';
import '@fortawesome/fontawesome-free/css/all.css';

const vuetify = createVuetify({
    components,
    directives,
  })

const app = createApp(App)

app.use(router)

app.use(vuetify, {
    icons: {
      defaultSet: 'mdi',
      sets: {
        mdi,
        fa,
      },
	}
})

app.mount('#app')

//createApp(App).use(store).use(router).mount('#app')

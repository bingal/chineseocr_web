import { createApp } from 'vue'
import Antd from 'ant-design-vue';
import App from './App.vue'
import 'ant-design-vue/dist/antd.css';
import axios from 'axios'
import VueAxios from 'vue-axios'

const app = createApp(App);
app.config.productionTip = false;
// app.config.globalProperties.$axios = axios
app.use(Antd, VueAxios, axios).mount('#app');

// app.config.globalProperties.$message = message;
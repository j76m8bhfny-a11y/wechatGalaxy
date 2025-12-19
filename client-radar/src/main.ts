import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";

// 👇 关键：必须引入这个 CSS 文件！
// 如果你的 CSS 文件在 src/assets/main.css，就写 import "./assets/main.css";
import "./style.css"; 

const app = createApp(App);
app.use(createPinia()); // 👈 挂载
app.mount("#app");

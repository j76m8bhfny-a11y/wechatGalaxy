<script setup lang="ts">
import { ref, computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';

const store = useMomentsStore();
const contactStore = useContactsStore(); // 用于获取头像等信息(如果将来需要)

// 🔍 搜索关键词
const searchQuery = ref('');

// 🧠 计算属性：根据搜索词过滤联系人
const filteredContacts = computed(() => {
  const allContacts = store.contacts; // 这是从 moments 聚合出来的发帖人列表

  if (!searchQuery.value) {
    return allContacts;
  }

  const query = searchQuery.value.toLowerCase();
  
  return allContacts.filter(c => {
    // 匹配规则：搜名字(备注/昵称) 或者 搜ID
    const nameMatch = c.name && c.name.toLowerCase().includes(query);
    const idMatch = c.id && c.id.toLowerCase().includes(query);
    return nameMatch || idMatch;
  });
});

// 处理点击
const selectContact = (wxid: string) => {
  if (store.selectedWxid === wxid) {
    // 如果再次点击已选中的人，取消选中（可选逻辑，目前保持选中状态更好）
    // store.selectedWxid = ''; 
  } else {
    store.selectedWxid = wxid;
    // 切换人时，顺便把中间的筛选也清空，重置视图
    store.filterWxid = '';
  }
};

// 清空搜索
const clearSearch = () => {
  searchQuery.value = '';
};
</script>

<template>
  <div class="flex flex-col h-full bg-white">
    
    <div class="p-4 border-b border-slate-100 bg-white z-10 sticky top-0">
      <h2 class="text-xl font-bold text-slate-800 mb-3 flex items-center">
        <span class="bg-blue-600 w-1.5 h-6 rounded-full mr-2"></span>
        通讯录
        <span class="ml-2 text-xs font-normal text-slate-400 bg-slate-100 px-2 py-0.5 rounded-full">
          {{ store.contacts.length }}人
        </span>
      </h2>
      
      <div class="relative group">
        <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
          <svg class="h-4 w-4 text-slate-400 group-focus-within:text-blue-500 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
        <input 
          v-model="searchQuery"
          type="text" 
          class="block w-full pl-9 pr-8 py-2 border border-slate-200 rounded-lg leading-5 bg-slate-50 text-slate-700 placeholder-slate-400 focus:outline-none focus:bg-white focus:ring-2 focus:ring-blue-100 focus:border-blue-400 transition-all duration-200 sm:text-sm" 
          placeholder="搜索姓名或 ID..." 
        />
        <button 
          v-if="searchQuery" 
          @click="clearSearch"
          class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-300 hover:text-slate-500 cursor-pointer"
        >
          <svg class="h-4 w-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /></svg>
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto scrollbar-thin">
      
      <div v-if="filteredContacts.length === 0" class="flex flex-col items-center justify-center pt-20 text-slate-400">
        <div class="text-3xl mb-2">🔍</div>
        <p class="text-sm">未找到相关联系人</p>
      </div>

      <div 
        v-for="contact in filteredContacts" 
        :key="contact.id"
        @click="selectContact(contact.id)"
        class="group relative flex items-center px-4 py-3 cursor-pointer transition-all duration-200 border-b border-slate-50 hover:bg-slate-50"
        :class="{ 'bg-blue-50/60': store.selectedWxid === contact.id }"
      >
        <div 
          v-if="store.selectedWxid === contact.id" 
          class="absolute left-0 top-0 bottom-0 w-[3px] bg-blue-500 rounded-r-md"
        ></div>

        <div 
          class="h-10 w-10 rounded-xl flex items-center justify-center text-white font-bold text-sm shadow-sm mr-3 shrink-0 transition-transform group-hover:scale-105"
          :class="store.selectedWxid === contact.id ? 'bg-blue-500 ring-2 ring-blue-200' : 'bg-slate-300'"
          :style="store.selectedWxid !== contact.id ? { backgroundColor: stringToColor(contact.name) } : {}"
        >
          {{ contact.name.charAt(0) }}
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex justify-between items-baseline mb-0.5">
            <h3 
              class="text-sm font-medium truncate pr-2"
              :class="store.selectedWxid === contact.id ? 'text-blue-700' : 'text-slate-700'"
            >
              {{ contact.name }}
            </h3>
            <span class="text-[10px] text-slate-400 font-mono">{{ formatDate(contact.latestDate) }}</span>
          </div>
          <p class="text-xs text-slate-400 truncate flex items-center">
            <span class="bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded mr-1.5 text-[10px]">
              {{ contact.momentCount }}条动态
            </span>
            </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
// 工具函数：根据名字生成固定颜色 (让头像看起来不那么单调)
function stringToColor(str: string) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
  return '#' + '00000'.substring(0, 6 - c.length) + c;
}

// 简单的日期格式化 (显示 月/日)
function formatDate(dateStr: string) {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  return `${date.getMonth() + 1}/${date.getDate()}`;
}
</script>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
</style>
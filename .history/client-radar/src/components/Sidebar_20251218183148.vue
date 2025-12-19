<script setup lang="ts">
import { ref, computed } from 'vue';
import { Search, Settings, User } from 'lucide-vue-next';
import { useMomentsStore } from '../stores/moments'; // 👈 引入 Store

// 1. 启用 Store
const store = useMomentsStore();

// 2. 搜索逻辑
const searchText = ref('');

// 3. 过滤联系人 (支持搜 wxid)
const filteredContacts = computed(() => {
  let list = store.contacts;
  
  if (searchText.value) {
    const key = searchText.value.toLowerCase();
    list = list.filter(c => c.name.toLowerCase().includes(key));
  }
  
  return list;
});

// 处理点击
const selectContact = (id: string) => {
  store.selectedWxid = id;
};
</script>

<template>
  <div class="flex flex-col h-full w-full select-none text-sm bg-white">
    
    <div class="p-3 border-b border-slate-100 space-y-2">
      <div class="relative">
        <Search class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
        <input 
          v-model="searchText"
          type="text" 
          placeholder="搜索 WXID..." 
          class="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-400"
        />
      </div>
      <div class="text-[10px] text-slate-400 px-1">
        共发现 {{ store.contacts.length }} 位好友动态
      </div>
    </div>

    <div class="flex-1 overflow-y-auto scrollbar-thin">
      <div 
        v-for="contact in filteredContacts" 
        :key="contact.id"
        @click="selectContact(contact.id)"
        :class="['flex items-center px-3 py-2.5 cursor-pointer border-l-[3px] transition-colors', 
          store.selectedWxid === contact.id ? 'bg-blue-50 border-blue-600' : 'border-transparent hover:bg-slate-50']"
      >
        <div class="h-9 w-9 rounded bg-slate-200 flex items-center justify-center text-slate-500 font-bold text-xs shrink-0 overflow-hidden">
           {{ contact.avatar }}
        </div>
        
        <div class="ml-2.5 overflow-hidden flex-1">
          <div class="flex items-center justify-between">
            <span class="text-sm font-bold text-slate-700 truncate w-24" :title="contact.name">
              {{ contact.name }}
            </span>
            <span class="text-[10px] text-slate-400 bg-slate-100 px-1 rounded">
              {{ contact.momentCount }}条
            </span>
          </div>
          <div class="text-[10px] text-slate-400 truncate mt-0.5">
            最近更新: {{ contact.latestDate.substring(5, 10) }}
          </div>
        </div>
      </div>
    </div>

    <div class="p-2 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <User class="h-4 w-4 text-slate-400"/>
        <div class="text-xs text-slate-600 font-medium">本机数据</div>
      </div>
      <button class="p-1 hover:bg-slate-200 rounded text-slate-400">
        <Settings class="h-3.5 w-3.5" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  width: 3px;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 4px;
}
</style>
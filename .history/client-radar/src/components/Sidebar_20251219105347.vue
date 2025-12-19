<script setup lang="ts">
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts'; // 👈 1. 引入联系人仓库
import { Search } from 'lucide-vue-next';

const store = useMomentsStore();
const contactStore = useContactsStore(); // 👈 2. 启用

const selectContact = (wxid: string) => {
  store.selectedWxid = wxid;
  // 切换联系人时，同时也清空筛选状态，避免逻辑混乱
  store.filterWxid = '';
};
</script>

<template>
  <div class="flex flex-col h-full bg-slate-50 border-r border-slate-200">
    <div class="p-4 border-b border-slate-200 bg-white">
      <div class="relative">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="搜索联系人..." 
          class="w-full pl-9 pr-4 py-2 bg-slate-100 border-none rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
        />
      </div>
    </div>

    <div class="flex-1 overflow-y-auto scrollbar-hide">
      <div 
        v-for="contact in store.contacts" 
        :key="contact.id"
        @click="selectContact(contact.id)"
        :class="['flex items-center p-3 cursor-pointer transition-colors hover:bg-white', 
          store.selectedWxid === contact.id ? 'bg-white border-l-4 border-blue-500 shadow-sm' : 'border-l-4 border-transparent text-slate-500']"
      >
        <div :class="['w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold mr-3 shrink-0 transition-colors',
          store.selectedWxid === contact.id ? 'bg-blue-100 text-blue-600' : 'bg-slate-200 text-slate-400']">
          {{ contact.avatar }}
        </div>

        <div class="flex-1 min-w-0">
          <div class="flex justify-between items-baseline mb-0.5">
            <span :class="['font-medium truncate text-sm', store.selectedWxid === contact.id ? 'text-slate-800' : 'text-slate-600']">
              {{ contactStore.getDisplayName(contact.id) }}
            </span>
            <span class="text-[10px] text-slate-400 shrink-0">{{ contact.latestDate }}</span>
          </div>
          <div class="flex justify-between items-center text-xs">
            <span class="truncate text-slate-400 pr-2">
              {{ contact.id }} </span>
            <span class="bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded-full text-[10px] font-medium">
              {{ contact.momentCount }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scrollbar-hide::-webkit-scrollbar {
  display: none;
}
.scrollbar-hide {
  -ms-overflow-style: none;
  scrollbar-width: none;
}
</style>
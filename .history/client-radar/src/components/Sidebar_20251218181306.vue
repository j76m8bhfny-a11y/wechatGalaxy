<script setup lang="ts">
import { ref } from 'vue';
import { Search, Settings, User, Star, ShieldAlert, LogOut } from 'lucide-vue-next';

// 模拟数据：通讯录列表
const contacts = ref([
  { id: '1', name: '张总', title: '华兴资本 · 合伙人', avatar: '张', isVip: true, isSpam: false },
  { id: '2', name: '李经理', title: '腾讯云 · 销售总监', avatar: '李', isVip: false, isSpam: false },
  { id: '3', name: '王秘书', title: '未知公司', avatar: '王', isVip: false, isSpam: false },
  { id: '4', name: 'A01 卖茶叶', title: '微商', avatar: '茶', isVip: false, isSpam: true },
  { id: '5', name: '赵总', title: '某国企 · 处长', avatar: '赵', isVip: true, isSpam: false },
]);

const currentFilter = ref('all'); // all | vip | spam
const selectedId = ref('1');      // 当前选中的人

// 简单的过滤逻辑
const filteredContacts = computed(() => {
  if (currentFilter.value === 'vip') return contacts.value.filter(c => c.isVip);
  if (currentFilter.value === 'spam') return contacts.value.filter(c => c.isSpam);
  return contacts.value;
});

import { computed } from 'vue';
</script>

<template>
  <div class="flex flex-col h-full bg-white border-r border-slate-200 w-[260px] select-none">
    
    <div class="p-4 border-b border-slate-100 space-y-3">
      <div class="relative">
        <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="搜索姓名、公司..." 
          class="w-full pl-9 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-md text-sm focus:outline-none focus:ring-1 focus:ring-blue-500 focus:bg-white transition-all placeholder:text-slate-400"
        />
      </div>

      <div class="flex p-1 bg-slate-100 rounded-md">
        <button 
          @click="currentFilter = 'all'"
          :class="['flex-1 py-1 text-xs font-medium rounded-sm transition-all', currentFilter === 'all' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700']"
        >
          全部
        </button>
        <button 
          @click="currentFilter = 'vip'"
          :class="['flex-1 py-1 text-xs font-medium rounded-sm transition-all', currentFilter === 'vip' ? 'bg-white text-amber-600 shadow-sm' : 'text-slate-500 hover:text-slate-700']"
        >
          VIP
        </button>
        <button 
          @click="currentFilter = 'spam'"
          :class="['flex-1 py-1 text-xs font-medium rounded-sm transition-all', currentFilter === 'spam' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700']"
        >
          垃圾
        </button>
      </div>
    </div>

    <div class="flex-1 overflow-y-auto scrollbar-thin">
      <div 
        v-for="contact in filteredContacts" 
        :key="contact.id"
        @click="selectedId = contact.id"
        :class="['flex items-center px-4 py-3 cursor-pointer border-l-4 transition-colors', 
          selectedId === contact.id ? 'bg-blue-50 border-blue-600' : 'border-transparent hover:bg-slate-50']"
      >
        <div class="h-10 w-10 rounded bg-slate-200 flex items-center justify-center text-slate-500 font-bold text-sm shrink-0">
          {{ contact.avatar }}
        </div>
        
        <div class="ml-3 overflow-hidden">
          <div class="flex items-center justify-between">
            <span class="text-sm font-bold text-slate-800 truncate">{{ contact.name }}</span>
            <Star v-if="contact.isVip" class="h-3 w-3 text-amber-500 fill-amber-500" />
            <ShieldAlert v-else-if="contact.isSpam" class="h-3 w-3 text-rose-400" />
          </div>
          <div class="text-xs text-slate-500 truncate mt-0.5">{{ contact.title }}</div>
        </div>
      </div>
    </div>

    <div class="p-3 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
      <div class="flex items-center space-x-3">
        <div class="h-8 w-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-xs">
          我
        </div>
        <div class="text-xs text-slate-600 font-medium">当前账号</div>
      </div>
      <button class="p-1.5 hover:bg-slate-200 rounded text-slate-500">
        <Settings class="h-4 w-4" />
      </button>
    </div>
  </div>
</template>

<style scoped>
/* 自定义极细滚动条，更像 Windows 原生 */
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 4px;
}
</style>
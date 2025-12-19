<script setup lang="ts">
import { ref, computed } from 'vue';
import { Search, Settings, Star, ShieldAlert } from 'lucide-vue-next';

// 模拟数据：通讯录列表
const contacts = ref([
  { id: '1', name: '张总', title: '华兴资本 · 合伙人', avatar: '张', isVip: true, isSpam: false },
  { id: '2', name: '李经理', title: '腾讯云 · 销售总监', avatar: '李', isVip: false, isSpam: false },
  { id: '3', name: '王秘书', title: '未知公司', avatar: '王', isVip: false, isSpam: false },
  { id: '4', name: 'A01 卖茶叶', title: '微商', avatar: '茶', isVip: false, isSpam: true },
  { id: '5', name: '赵总', title: '某国企 · 处长', avatar: '赵', isVip: true, isSpam: false },
]);

const currentFilter = ref('all'); 
const selectedId = ref('1');

const filteredContacts = computed(() => {
  if (currentFilter.value === 'vip') return contacts.value.filter(c => c.isVip);
  if (currentFilter.value === 'spam') return contacts.value.filter(c => c.isSpam);
  return contacts.value;
});
</script>

<template>
  <div class="flex flex-col h-full bg-white border-r border-slate-200 w-full select-none text-sm">
    
    <div class="p-3 border-b border-slate-100 space-y-2">
      <div class="relative">
        <Search class="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-slate-400" />
        <input 
          type="text" 
          placeholder="搜索..." 
          class="w-full pl-8 pr-3 py-1.5 bg-slate-50 border border-slate-200 rounded text-xs focus:outline-none focus:ring-1 focus:ring-blue-500 transition-all placeholder:text-slate-400"
        />
      </div>

      <div class="flex p-0.5 bg-slate-100 rounded">
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
        :class="['flex items-center px-3 py-2.5 cursor-pointer border-l-[3px] transition-colors', 
          selectedId === contact.id ? 'bg-blue-50 border-blue-600' : 'border-transparent hover:bg-slate-50']"
      >
        <div class="h-9 w-9 rounded bg-slate-200 flex items-center justify-center text-slate-500 font-bold text-xs shrink-0">
          {{ contact.avatar }}
        </div>
        
        <div class="ml-2.5 overflow-hidden flex-1">
          <div class="flex items-center justify-between">
            <span class="text-sm font-bold text-slate-700 truncate">{{ contact.name }}</span>
            <Star v-if="contact.isVip" class="h-3 w-3 text-amber-500 fill-amber-500" />
            <ShieldAlert v-else-if="contact.isSpam" class="h-3 w-3 text-rose-400" />
          </div>
          <div class="text-[10px] text-slate-400 truncate mt-0.5">{{ contact.title }}</div>
        </div>
      </div>
    </div>

    <div class="p-2 border-t border-slate-200 bg-slate-50 flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <div class="h-6 w-6 rounded-full bg-blue-600 flex items-center justify-center text-white text-[10px]">
          我
        </div>
        <div class="text-xs text-slate-600 font-medium">当前账号</div>
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
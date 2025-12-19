<script setup lang="ts">
import { ref } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';
import { Search, Database, Loader2 } from 'lucide-vue-next'; // 引入图标

const store = useMomentsStore();
const contactStore = useContactsStore();

// 🟢 这里填你解密后的 MicroMsg.db 的绝对路径
// 注意：Windows路径要转义，例如 "C:\\Users\\xxx\\MicroMsg.db"
const dbPathInput = ref(''); 

const handleImport = async () => {
  if(!dbPathInput.value) return;
  await contactStore.importFromDb(dbPathInput.value);
};

const selectContact = (wxid: string) => {
  store.selectedWxid = wxid;
  store.filterWxid = '';
};
</script>

<template>
  <div class="flex flex-col h-full bg-slate-50 border-r border-slate-200">
    
    <div class="p-3 border-b border-slate-200 bg-white space-y-2">
      
      <div class="relative">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input 
          type="text" 
          placeholder="搜索联系人..." 
          class="w-full pl-9 pr-4 py-2 bg-slate-100 border-none rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
        />
      </div>

      <div class="flex space-x-1">
        <input 
          v-model="dbPathInput"
          type="text" 
          placeholder="输入 MicroMsg.db 路径..." 
          class="flex-1 px-2 py-1.5 bg-slate-100 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none"
        />
        <button 
          @click="handleImport"
          :disabled="contactStore.isLoading"
          class="px-2 py-1.5 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-blue-300 transition-colors flex items-center justify-center min-w-[30px]"
          title="从数据库加载通讯录"
        >
          <Loader2 v-if="contactStore.isLoading" class="h-3 w-3 animate-spin" />
          <Database v-else class="h-3 w-3" />
        </button>
      </div>
      <div v-if="contactStore.errorMsg" class="text-[10px] text-red-500 px-1">
        {{ contactStore.errorMsg }}
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
              {{ contact.id }}
            </span>
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
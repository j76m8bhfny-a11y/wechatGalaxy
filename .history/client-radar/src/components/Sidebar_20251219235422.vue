<script setup lang="ts">
import { ref, computed } from 'vue'; // [新增] 引入 computed
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';
import { Search, Database, Loader2 } from 'lucide-vue-next';
import { invoke } from '@tauri-apps/api/core'; // 引入 Tauri 调用

const store = useMomentsStore();
const contactStore = useContactsStore();

// 状态定义
const dbPathInput = ref(''); // 数据库路径输入框
const isScanning = ref(false); // 扫描 Loading 状态
const searchQuery = ref(''); // [新增] 搜索关键词状态

// [新增] 计算属性：根据搜索词过滤联系人
const filteredContacts = computed(() => {
  const allContacts = store.contacts;
  const query = searchQuery.value.trim().toLowerCase();

  if (!query) {
    return allContacts;
  }

  return allContacts.filter(contact => {
    // 获取显示名称（优先备注，其次昵称，最后wxid）
    const displayName = contactStore.getDisplayName(contact.id).toLowerCase();
    const wxid = contact.id.toLowerCase();
    
    // 只要名字或ID包含搜索词即可
    return displayName.includes(query) || wxid.includes(query);
  });
});

// 🟢 功能1：一键自动扫描 (调用 Rust -> Python Sidecar)
const autoScan = async () => {
  isScanning.value = true;
  contactStore.errorMsg = '';
  
  try {
    console.log("启动自动扫描...");
    const resStr = await invoke<string>('auto_decrypt_wechat');
    const res = JSON.parse(resStr);
    
    if (res.status === 'success') {
      dbPathInput.value = res.micro_db_path; // 显示路径
      
      // 1. 加载通讯录 (Rust 读取 MicroMsg.db)
      await contactStore.importFromDb(res.micro_db_path);
      
      // 2. 🔥 加载朋友圈 (直接使用 Python 返回的 feeds)
      if (res.feeds && res.feeds.length > 0) {
        store.loadFeeds(res.feeds); // 👈 调用新方法
      } else {
        console.log("Python 未返回 Feeds 数据，可能是空库或解析失败");
      }
      
    } else {
      contactStore.errorMsg = res.message || '未知错误';
    }
    
  } catch (e) {
    console.error(e);
    contactStore.errorMsg = "扫描异常: " + String(e);
  } finally {
    isScanning.value = false;
  }
};

// 🔵 功能2：手动导入 (作为备用方案)
const handleImport = async () => {
  if(!dbPathInput.value) return;
  await contactStore.importFromDb(dbPathInput.value);
};

// 选中联系人逻辑
const selectContact = (wxid: string) => {
  store.selectedWxid = wxid;
  // 切换联系人时，同时也清空筛选状态，避免逻辑混乱
  store.filterWxid = '';
};
</script>

<template>
  <div class="flex flex-col h-full bg-slate-50 border-r border-slate-200">
    
    <div class="p-3 border-b border-slate-200 bg-white space-y-2">
      
      <div class="relative">
        <Search class="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
        <input 
          v-model="searchQuery"
          type="text" 
          placeholder="搜索联系人..." 
          class="w-full pl-9 pr-4 py-2 bg-slate-100 border-none rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none transition-all"
        />
      </div>

      <div class="flex space-x-1">
        <input 
          v-model="dbPathInput"
          type="text" 
          placeholder="MicroMsg.db 路径..." 
          class="flex-1 px-2 py-1.5 bg-slate-100 border border-slate-200 rounded text-xs focus:ring-1 focus:ring-blue-500 outline-none truncate text-slate-600"
          :title="dbPathInput" 
        />
        
        <button 
          @click="autoScan"
          :disabled="isScanning || contactStore.isLoading"
          class="px-3 py-1.5 bg-green-600 text-white rounded hover:bg-green-700 disabled:bg-slate-300 transition-colors flex items-center justify-center font-medium text-xs whitespace-nowrap shadow-sm"
          title="一键自动扫描并解密微信"
        >
          <Loader2 v-if="isScanning" class="h-3 w-3 animate-spin mr-1" />
          <span v-else>🚀 扫描</span>
        </button>

        <button 
          @click="handleImport"
          :disabled="contactStore.isLoading"
          class="px-2 py-1.5 bg-blue-50 text-blue-600 border border-blue-100 rounded hover:bg-blue-100 disabled:bg-slate-50 transition-colors"
          title="手动读取指定路径"
        >
          <Database class="h-3 w-3" />
        </button>
      </div>

      <div v-if="contactStore.errorMsg" class="text-[10px] text-red-500 px-1 leading-tight break-all">
        ⚠️ {{ contactStore.errorMsg }}
      </div>

    </div>

    <div class="flex-1 overflow-y-auto scrollbar-hide">
      <div 
        v-for="contact in filteredContacts" 
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
      
      <div v-if="filteredContacts.length === 0" class="text-center text-slate-400 py-10 text-xs">
        未找到相关联系人
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
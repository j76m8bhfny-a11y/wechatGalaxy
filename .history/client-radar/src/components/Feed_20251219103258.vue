<script setup lang="ts">
import { useMomentsStore } from '../stores/moments';
import { MoreHorizontal, FilterX } from 'lucide-vue-next';

const store = useMomentsStore();

const formatDate = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  });
};

const getGridClass = (count: number) => {
  if (count === 1) return 'grid-cols-1 w-2/3';
  if (count === 4) return 'grid-cols-2 w-2/3';
  return 'grid-cols-3';
};

// 清除筛选的函数
const clearFilter = () => {
  store.filterWxid = '';
};
</script>

<template>
  <div class="flex flex-col h-full bg-white text-sm">
    
    <div class="h-12 border-b border-slate-100 flex items-center justify-between px-4 bg-white shrink-0 z-10">
      <div class="flex items-center space-x-2 overflow-hidden">
        <span class="font-bold text-slate-700 whitespace-nowrap">情报档案</span>
        
        <div v-if="store.filterWxid" class="flex items-center space-x-1 bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full cursor-pointer hover:bg-orange-100 transition-colors" @click="clearFilter">
           <span class="text-xs truncate max-w-[80px]">与 {{ store.filterWxid.substring(0,6) }}..</span>
           <FilterX class="h-3 w-3" />
        </div>
        <span v-else-if="store.selectedWxid" class="text-xs text-slate-400 px-2 py-0.5 bg-slate-100 rounded-full truncate max-w-[100px]">
           {{ store.selectedWxid }}
        </span>
      </div>
      <button class="p-1.5 hover:bg-slate-50 rounded text-slate-400">
        <MoreHorizontal class="h-4 w-4" />
      </button>
    </div>

    <div class="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
      
      <div v-if="!store.selectedWxid" class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
        <div class="text-4xl">📂</div>
        <p>请在左侧选择一位联系人</p>
      </div>

      <div v-else-if="store.filteredMoments.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400 space-y-2">
        <div class="text-4xl">🔍</div>
        <p>暂无相关互动记录</p>
        <button @click="clearFilter" class="text-blue-500 text-xs hover:underline">查看全部动态</button>
      </div>

      <div 
        v-else
        v-for="moment in store.filteredMoments" 
        :key="moment.id"
        class="bg-white rounded border border-slate-200 shadow-sm p-3 hover:shadow-md transition-shadow cursor-default"
      >
        <div class="flex justify-between items-start mb-2">
            <div class="flex items-center space-x-2">
              <span class="font-bold text-slate-800 text-xs truncate max-w-[120px]">
                {{ moment.author_wxid }}
              </span>
              <span class="text-[10px] text-slate-400">
                {{ formatDate(moment.timestamp) }}
              </span>
            </div>
        </div>
        
        <p v-if="moment.content.text" class="text-xs text-slate-700 leading-relaxed mb-2.5 whitespace-pre-wrap">
          {{ moment.content.text }}
        </p>
        
        <div 
          v-if="moment.content.media && moment.content.media.length > 0"
          :class="['grid gap-1 mb-3', getGridClass(moment.content.media.length)]"
        >
          <div 
            v-for="(media, idx) in moment.content.media" 
            :key="idx"
            class="aspect-square bg-slate-100 rounded-sm overflow-hidden border border-slate-100"
          >
             <img 
               :src="media.thumb || media.url" 
               class="w-full h-full object-cover hover:scale-110 transition-transform duration-300"
               loading="lazy"
             />
          </div>
        </div>

        <div class="flex items-center justify-between pt-2 border-t border-slate-50">
            <div class="flex space-x-3 text-[10px] text-slate-400">
              <span 
                :class="['flex items-center transition-colors', 
                  moment.interactions.likes.some(u => u.wxid === store.filterWxid) ? 'text-orange-500 font-bold' : 'hover:text-blue-600']"
              >
                <span class="mr-1">👍</span> {{ moment.interactions.likes.length }}
              </span>
              <span 
                :class="['flex items-center transition-colors', 
                  moment.interactions.comments.some(u => u.wxid === store.filterWxid) ? 'text-orange-500 font-bold' : 'hover:text-blue-600']"
              >
                <span class="mr-1">💬</span> {{ moment.interactions.comments.length }}
              </span>
            </div>
        </div>
      </div>
      
      <div v-if="store.filteredMoments.length > 0" class="text-center text-[10px] text-slate-300 py-4">
        —— 筛选出 {{ store.filteredMoments.length }} 条相关动态 ——
      </div>

    </div>
  </div>
</template>

<style scoped>
.scrollbar-thin::-webkit-scrollbar {
  width: 4px;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: #f1f5f9;
  border-radius: 4px;
}
.scrollbar-thin:hover::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
}
</style>
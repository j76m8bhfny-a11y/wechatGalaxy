<script setup lang="ts">
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts'; // 👈 1. 引入
import { MoreHorizontal, FilterX, Heart } from 'lucide-vue-next';

const store = useMomentsStore();
const contactStore = useContactsStore(); // 👈 2. 启用

// 日期格式化
const formatDate = (timestamp: number) => {
  return new Date(timestamp * 1000).toLocaleString('zh-CN', {
    month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  });
};

// 图片九宫格样式
const getGridClass = (count: number) => {
  if (count === 1) return 'grid-cols-1 w-2/3';
  if (count === 4) return 'grid-cols-2 w-2/3';
  return 'grid-cols-3';
};

// 清除筛选
const clearFilter = () => {
  store.filterWxid = '';
};

// ❌ 删除了临时的 formatName 函数，改用 store
</script>

<template>
  <div class="flex flex-col h-full bg-white text-sm">
    
    <div class="h-12 border-b border-slate-100 flex items-center justify-between px-4 bg-white shrink-0 z-10">
      <div class="flex items-center space-x-2 overflow-hidden">
        <span class="font-bold text-slate-700 whitespace-nowrap">情报档案</span>
        
        <div v-if="store.filterWxid" class="flex items-center space-x-1 bg-orange-50 text-orange-600 px-2 py-0.5 rounded-full cursor-pointer hover:bg-orange-100 transition-colors" @click="clearFilter">
           <span class="text-xs truncate max-w-[120px]">与 {{ contactStore.getDisplayName(store.filterWxid) }} 的互动</span>
           <FilterX class="h-3 w-3" />
        </div>
        <span v-else-if="store.selectedWxid" class="text-xs text-slate-400 px-2 py-0.5 bg-slate-100 rounded-full truncate max-w-[150px]">
           {{ contactStore.getDisplayName(store.selectedWxid) }}
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
              <span class="font-bold text-slate-800 text-xs truncate max-w-[150px]">
                {{ contactStore.getDisplayName(moment.author_wxid) }}
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
              <span :class="['flex items-center', moment.interactions.likes.length > 0 ? 'text-slate-600' : '']">
                <Heart class="w-3 h-3 mr-1" /> {{ moment.interactions.likes.length }}
              </span>
              <span :class="['flex items-center', moment.interactions.comments.length > 0 ? 'text-slate-600' : '']">
                <span class="mr-1">💬</span> {{ moment.interactions.comments.length }}
              </span>
            </div>
        </div>

        <div 
          v-if="(moment.interactions.likes && moment.interactions.likes.length > 0) || (moment.interactions.comments && moment.interactions.comments.length > 0)" 
          class="mt-2 bg-slate-50 p-2 rounded-[4px] relative"
        >
           <div class="absolute -top-1 left-3 w-2 h-2 bg-slate-50 rotate-45 transform"></div>

           <div 
             v-if="moment.interactions.likes && moment.interactions.likes.length > 0"
             class="flex flex-wrap items-center text-[11px] leading-snug mb-1.5 pb-1.5 border-b border-slate-200 last:border-0 last:mb-0 last:pb-0"
           >
             <Heart class="w-3 h-3 text-slate-400 mr-1.5 shrink-0" />
             <span v-for="(like, idx) in moment.interactions.likes" :key="idx" class="mr-1">
                <span 
                  :class="['cursor-pointer hover:underline font-medium', 
                    like.wxid === store.filterWxid ? 'text-orange-600 bg-orange-100 rounded px-0.5' : 'text-blue-600']"
                  @click.stop="store.filterWxid = like.wxid"
                  :title="like.wxid"
                >
                  {{ contactStore.getDisplayName(like.wxid) }}
                </span>
                <span v-if="idx < moment.interactions.likes.length - 1" class="text-slate-400">,</span>
             </span>
           </div>

           <div 
             v-if="moment.interactions.comments && moment.interactions.comments.length > 0" 
             class="space-y-1"
           >
             <div 
               v-for="(comment, cIdx) in moment.interactions.comments" 
               :key="cIdx"
               class="text-[11px] leading-snug flex items-start"
             >
               <span 
                 :class="['font-medium cursor-pointer hover:underline shrink-0 mr-1', 
                   comment.wxid === store.filterWxid ? 'text-orange-600' : 'text-blue-600']"
                 @click.stop="store.filterWxid = comment.wxid"
                 :title="comment.wxid"
               >
                 {{ contactStore.getDisplayName(comment.wxid) }}:
               </span>
               <span :class="['break-all', comment.wxid === store.filterWxid ? 'text-slate-900 font-medium' : 'text-slate-600']">
                 {{ comment.content || '' }}
               </span>
             </div>
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
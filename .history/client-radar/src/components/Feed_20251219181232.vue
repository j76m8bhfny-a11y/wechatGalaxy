<script setup lang="ts">
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';
//import { computed } from 'vue';
import { MessageSquare, Heart, Share2, MoreHorizontal } from 'lucide-vue-next';

const store = useMomentsStore();
const contactStore = useContactsStore();

// 核心逻辑：获取显示名称
// 优先策略：
// 1. 如果是互动列表(点赞/评论)传来的 snapshotName (数据库里的历史昵称)，直接用。
// 2. 如果没有，去通讯录 Store 里查现在的备注或昵称。
// 3. 如果还没查到，显示 wxid 或 "未知用户"。
const getDisplayName = (wxid: string, snapshotName?: string) => {
  if (snapshotName && snapshotName.length > 0) {
    return snapshotName;
  }
  return contactStore.getDisplayName(wxid) || '未知用户';
};

// 格式化媒体网格布局
const getGridClass = (count: number) => {
  if (count === 1) return 'grid-cols-1 max-w-[60%]'; // 单张图限制宽度
  if (count === 2) return 'grid-cols-2 max-w-[300px]';
  if (count === 4) return 'grid-cols-2 max-w-[300px]'; // 4张图也是田字格
  return 'grid-cols-3'; // 其他情况九宫格
};
</script>

<template>
  <div class="h-full bg-slate-50 overflow-y-auto p-4 sm:p-6 lg:p-8 custom-scrollbar">
    <div class="max-w-3xl mx-auto space-y-6">
      
      <div 
        v-for="moment in store.filteredMoments" 
        :key="moment.id"
        class="bg-white rounded-xl shadow-sm border border-slate-100 p-5 transition-shadow hover:shadow-md"
      >
        <div class="flex items-start mb-3">
          <div class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold mr-3 shrink-0 text-lg">
            {{ moment.avatar }}
          </div>
          
          <div class="flex-1 min-w-0">
            <div class="flex justify-between items-start">
              <div>
                <h3 class="font-bold text-slate-800 text-sm md:text-base cursor-pointer hover:text-blue-600">
                  {{ getDisplayName(moment.author_wxid) }}
                </h3>
                <p class="text-xs text-slate-400 mt-0.5 font-mono">{{ moment.date }}</p>
              </div>
              <button class="text-slate-300 hover:text-slate-500">
                <MoreHorizontal class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        <div class="mb-3 text-slate-700 text-sm md:text-base whitespace-pre-wrap leading-relaxed select-text">
          {{ moment.content.text }}
        </div>

        <div 
          v-if="moment.content.media && moment.content.media.length > 0" 
          :class="['grid gap-1.5 mb-4', getGridClass(moment.content.media.length)]"
        >
          <div 
            v-for="(item, idx) in moment.content.media" 
            :key="idx" 
            class="aspect-square bg-slate-100 rounded-lg overflow-hidden relative group border border-slate-200"
          >
            <img 
              v-if="item.type === 'image'"
              :src="item.src" 
              class="w-full h-full object-cover transition-transform group-hover:scale-105 cursor-zoom-in"
              loading="lazy"
              referrerpolicy="no-referrer"
              alt="Moment Image"
            />
            
            <video 
              v-else
              :src="item.src" 
              class="w-full h-full object-cover"
              controls 
              preload="metadata"
              referrerpolicy="no-referrer"
            ></video>
          </div>
        </div>

        <div class="flex items-center justify-between pt-3 border-t border-slate-50">
          <div class="flex space-x-6">
            <button class="flex items-center space-x-1.5 text-slate-500 hover:text-pink-500 transition-colors group">
              <Heart class="h-4 w-4 group-hover:fill-current" />
              <span class="text-xs font-medium">{{ moment.stats.likes_count || '赞' }}</span>
            </button>
            
            <button class="flex items-center space-x-1.5 text-slate-500 hover:text-blue-500 transition-colors">
              <MessageSquare class="h-4 w-4" />
              <span class="text-xs font-medium">{{ moment.stats.comments_count || '评论' }}</span>
            </button>
            
            <button class="flex items-center space-x-1.5 text-slate-500 hover:text-green-500 transition-colors">
              <Share2 class="h-4 w-4" />
            </button>
          </div>
        </div>

        <div v-if="moment.interactions && moment.interactions.likes.length > 0" class="mt-3 bg-slate-50 rounded-lg p-3 text-xs text-slate-600 flex items-start">
           <Heart class="h-3 w-3 mt-1 mr-2 text-slate-400 shrink-0" />
           <div class="flex flex-wrap gap-1 leading-5">
             <span v-for="(like, index) in moment.interactions.likes" :key="like.wxid" class="group">
               <span class="text-blue-700 font-semibold cursor-pointer hover:underline">
                 {{ getDisplayName(like.wxid, like.name) }}
               </span>
               <span v-if="index < moment.interactions.likes.length - 1">, </span>
             </span>
           </div>
        </div>

        <div v-if="moment.interactions && moment.interactions.comments.length > 0" class="mt-1 bg-slate-50 rounded-lg p-3 text-xs space-y-1.5">
           <div v-for="(cmt, idx) in moment.interactions.comments" :key="idx" class="flex flex-wrap items-baseline leading-relaxed">
              
              <span class="text-blue-700 font-semibold shrink-0 cursor-pointer hover:underline">
                {{ getDisplayName(cmt.wxid, cmt.name) }}
              </span>

              <span v-if="cmt.reply_to_wxid" class="text-slate-400 mx-1">
                回复
              </span>
              <span v-if="cmt.reply_to_wxid" class="text-blue-700 font-semibold cursor-pointer hover:underline">
                {{ getDisplayName(cmt.reply_to_wxid) }}
              </span>

              <span class="text-slate-400 font-bold mx-0.5">:</span>
              <span class="text-slate-700 select-text">{{ cmt.content }}</span>
           </div>
        </div>

      </div>

      <div v-if="store.moments.length === 0" class="flex flex-col items-center justify-center py-20 text-slate-400">
        <div class="bg-slate-100 p-4 rounded-full mb-4">
          <MessageSquare class="h-8 w-8 text-slate-300" />
        </div>
        <p class="text-sm font-medium">暂无数据</p>
        <p class="text-xs mt-1 text-slate-300">请点击左上角的“扫描”按钮获取朋友圈</p>
      </div>

    </div>
  </div>
</template>

<style scoped>
/* 隐藏默认滚动条但保留滚动功能 (可选优化) */
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
</style>
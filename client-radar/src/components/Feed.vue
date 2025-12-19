<script setup lang="ts">
//import { ref } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';

const store = useMomentsStore();
const contactStore = useContactsStore();

// 处理图片加载错误，防止裂图
const handleImageError = (e: Event) => {
  const target = e.target as HTMLImageElement;
  target.style.display = 'none'; // 加载失败直接隐藏
};

// 格式化时间戳
const formatTime = (timestamp: number) => {
  if (!timestamp) return '';
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
};

/*
// 判断是否是视频文件
const isVideo = (url: string) => {
  return url.toLowerCase().endsWith('.mp4');
};
*/
</script>


<template>
  <div class="h-full overflow-y-auto p-4 space-y-6 bg-slate-50 scrollbar-thin">
    
    <div v-if="store.filteredMoments.length === 0" class="flex flex-col items-center justify-center h-full text-slate-400">
      <div class="text-4xl mb-2">📭</div>
      <p>暂无相关动态</p>
    </div>

    <div 
      v-for="moment in store.filteredMoments" 
      :key="moment.id" 
      class="bg-white p-5 rounded-xl shadow-sm border border-slate-100 transition-all hover:shadow-md"
    >
      <div class="flex items-start space-x-3 mb-3">
        <div class="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center text-blue-600 font-bold shrink-0">
          {{ contactStore.getDisplayName(moment.author_wxid).charAt(0) }}
        </div>
        
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between">
            <h3 class="font-bold text-slate-800 text-base truncate">
              {{ contactStore.getDisplayName(moment.author_wxid) }}
            </h3>
            </div>
          <p class="text-xs text-slate-400 mt-0.5">{{ formatTime(moment.timestamp) }}</p>
        </div>
      </div>

      <div class="mb-3">
        <p class="text-slate-700 text-sm leading-relaxed whitespace-pre-wrap break-words">
          {{ moment.content.text }}
        </p>
      </div>

      <div v-if="moment.content.media && moment.content.media.length > 0" class="mb-4">
        <div class="grid gap-1" 
             :class="{
               'grid-cols-1': moment.content.media.length === 1,
               'grid-cols-2': moment.content.media.length === 2 || moment.content.media.length === 4,
               'grid-cols-3': moment.content.media.length >= 3 && moment.content.media.length !== 4
             }">
          <div v-for="(media, idx) in moment.content.media" :key="idx" class="relative group aspect-square bg-slate-100 overflow-hidden rounded-md cursor-pointer">
            
            <video 
              v-if="media.type === 'video'" 
              :src="media.src" 
              class="w-full h-full object-cover"
              controls 
              preload="metadata"
            ></video>

            <img 
              v-else 
              :src="media.src" 
              class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
              loading="lazy"
              referrerpolicy="no-referrer"
              @error="handleImageError"
            />
          </div>
        </div>
      </div>

      <div class="bg-slate-50/50 rounded-lg p-3 text-xs text-slate-600 space-y-2">
        
        <div v-if="moment.interactions.likes.length > 0" class="flex items-start space-x-2">
          <div class="mt-0.5 text-slate-400 shrink-0">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
            </svg>
          </div>
          <div class="flex flex-wrap gap-1 leading-5">
            <span v-for="(like, index) in moment.interactions.likes" :key="index">
              <span 
                class="cursor-pointer hover:underline"
                :class="like.wxid === store.filterWxid ? 'text-orange-600 font-extrabold bg-orange-100 px-1 rounded' : 'text-blue-600 font-medium'"
              >
                {{ like.name || contactStore.getDisplayName(like.wxid) || '未知用户' }}
              </span>
              <span v-if="index < moment.interactions.likes.length - 1" class="text-slate-300">,</span>
            </span>
          </div>
        </div>

        <div v-if="moment.interactions.likes.length > 0 && moment.interactions.comments.length > 0" class="border-t border-slate-200/60 my-1"></div>

        <div v-if="moment.interactions.comments.length > 0" class="space-y-1">
          <div v-for="(comment, cIndex) in moment.interactions.comments" :key="cIndex" class="flex items-start space-x-2 group">
             <div class="mt-0.5 text-slate-400 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
               <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
                </svg>
             </div>
             <div class="break-words flex-1">
               <span 
                 class="cursor-pointer hover:underline"
                 :class="comment.wxid === store.filterWxid ? 'text-orange-600 font-extrabold bg-orange-100 px-1 rounded' : 'text-blue-600 font-medium'"
               >
                 {{ comment.name || contactStore.getDisplayName(comment.wxid) }}
               </span>
               
               <span v-if="comment.reply_to_wxid" class="text-slate-400 mx-1 text-[10px]">回复</span>
               <span v-if="comment.reply_to_wxid" class="text-blue-600 font-medium text-xs">
                 {{ contactStore.getDisplayName(comment.reply_to_wxid) }}
               </span>
               
               <span class="text-slate-800 mx-0.5">:</span>
               <span class="text-slate-600">{{ comment.content }}</span>
             </div>
          </div>
        </div>

      </div>
    </div>
  </div>
</template>

<style scoped>
/* 隐藏滚动条但保留功能 (Webkit) */
.scrollbar-thin::-webkit-scrollbar {
  width: 6px;
}
.scrollbar-thin::-webkit-scrollbar-track {
  background: transparent;
}
.scrollbar-thin::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
</style>
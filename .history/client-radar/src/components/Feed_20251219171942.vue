<script setup lang="ts">
import { useMomentsStore, type Moment } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';
import { computed } from 'vue';
import { MessageSquare, Heart, Share2, MoreHorizontal } from 'lucide-vue-next';

const store = useMomentsStore();
const contactStore = useContactsStore();

// 获取真实姓名
const getAuthorName = (wxid: string) => {
  return contactStore.getDisplayName(wxid) || '未知用户';
};

// 格式化媒体网格
const getGridClass = (count: number) => {
  if (count === 1) return 'grid-cols-1';
  if (count === 2) return 'grid-cols-2';
  if (count === 3) return 'grid-cols-3';
  if (count === 4) return 'grid-cols-2 max-w-[300px]';
  return 'grid-cols-3';
};
</script>

<template>
  <div class="h-full bg-slate-50 overflow-y-auto p-4 sm:p-6 lg:p-8">
    <div class="max-w-3xl mx-auto space-y-6">
      
      <div 
        v-for="moment in store.filteredMoments" 
        :key="moment.id"
        class="bg-white rounded-xl shadow-sm border border-slate-100 p-5 transition-shadow hover:shadow-md"
      >
        <div class="flex items-start mb-3">
          <div class="w-10 h-10 rounded-lg bg-blue-100 text-blue-600 flex items-center justify-center font-bold mr-3 shrink-0">
            {{ moment.avatar }}
          </div>
          <div class="flex-1 min-w-0">
            <div class="flex justify-between items-start">
              <div>
                <h3 class="font-bold text-slate-800 text-sm md:text-base">
                  {{ getAuthorName(moment.author_wxid) }}
                </h3>
                <p class="text-xs text-slate-400 mt-0.5">{{ moment.date }}</p>
              </div>
              <button class="text-slate-300 hover:text-slate-500">
                <MoreHorizontal class="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>

        <div class="mb-3 text-slate-700 text-sm md:text-base whitespace-pre-wrap leading-relaxed">
          {{ moment.content.text }}
        </div>

        <div 
          v-if="moment.content.media && moment.content.media.length > 0" 
          :class="['grid gap-1.5 mb-4', getGridClass(moment.content.media.length)]"
        >
          <div 
            v-for="(item, idx) in moment.content.media" 
            :key="idx" 
            class="aspect-square bg-slate-100 rounded-lg overflow-hidden relative group"
          >
            <img 
              v-if="item.type === 'image'"
              :src="item.src" 
              class="w-full h-full object-cover transition-transform group-hover:scale-105"
              loading="lazy"
              alt="Moment Image"
            />
            <div v-else class="w-full h-full flex items-center justify-center bg-black/10">
              <span class="text-xs text-slate-500">视频</span>
            </div>
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

        <div v-if="moment.interactions && moment.interactions.likes.length > 0" class="mt-3 bg-slate-50 rounded p-2 text-xs text-slate-600 flex items-start">
           <Heart class="h-3 w-3 mt-0.5 mr-2 text-slate-400 shrink-0" />
           <div class="flex flex-wrap gap-1">
             <span v-for="like in moment.interactions.likes" :key="like.wxid" class="text-blue-600 font-medium cursor-pointer hover:underline">
               {{ getAuthorName(like.wxid) }}
             </span>
           </div>
        </div>

        <div v-if="moment.interactions && moment.interactions.comments.length > 0" class="mt-1 bg-slate-50 rounded p-2 text-xs space-y-1">
           <div v-for="(cmt, idx) in moment.interactions.comments" :key="idx" class="flex">
              <span class="text-blue-600 font-medium shrink-0 cursor-pointer hover:underline">
                {{ getAuthorName(cmt.wxid) }}:
              </span>
              <span class="text-slate-700 ml-1">{{ cmt.content }}</span>
           </div>
        </div>

      </div>

      <div v-if="store.moments.length === 0" class="text-center py-20 text-slate-400">
        <div class="mb-2">📭</div>
        <p>暂无数据，请点击左上角的“扫描”按钮</p>
      </div>

    </div>
  </div>
</template>
<script setup lang="ts">
import { useMomentsStore } from '../stores/moments';
import { Share2 } from 'lucide-vue-next';

const store = useMomentsStore();
</script>

<template>
  <div class="w-full h-full flex flex-col items-center justify-center bg-[#F0F2F5] select-none">
    
    <div v-if="!store.selectedWxid" class="text-center text-slate-400">
      <div class="mb-4 inline-block p-4 bg-white rounded-full shadow-sm">
        <Share2 class="w-10 h-10 text-blue-500 opacity-50" />
      </div>
      <p class="text-lg font-medium">关系透镜准备就绪</p>
      <p class="text-xs mt-1 opacity-75">请在左侧选择一位联系人</p>
    </div>

    <div v-else class="text-center">
      <div class="mb-6 relative inline-block">
        <div class="w-20 h-20 bg-blue-600 rounded-full flex items-center justify-center text-white text-xl font-bold shadow-lg shadow-blue-300">
          {{ store.selectedWxid.substring(0, 1) }}
        </div>
        <div class="absolute -inset-4 border-2 border-blue-200 rounded-full animate-pulse"></div>
      </div>
      
      <h2 class="text-2xl font-bold text-slate-700 mb-2">{{ store.selectedWxid }}</h2>
      <p class="text-slate-500 mb-8">数据连接正常，暂未加载图谱引擎</p>

      <div class="grid grid-cols-2 gap-4 text-left max-w-xs mx-auto">
        <div class="bg-white p-3 rounded border border-slate-200 shadow-sm">
          <div class="text-xs text-slate-400">朋友圈总数</div>
          <div class="text-lg font-bold text-blue-600">{{ store.currentMoments.length }} 条</div>
        </div>
        <div class="bg-white p-3 rounded border border-slate-200 shadow-sm">
          <div class="text-xs text-slate-400">互动次数</div>
          <div class="text-lg font-bold text-purple-600">
             {{ store.currentMoments.reduce((acc, m) => acc + m.interactions.likes.length + m.interactions.comments.length, 0) }} 次
          </div>
        </div>
      </div>
    </div>

  </div>
</template>
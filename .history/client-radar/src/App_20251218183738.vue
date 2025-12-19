<script setup lang="ts">
import { ref } from 'vue';
import Sidebar from "./components/Sidebar.vue";
import Feed from "./components/Feed.vue"; // 👈 新增引入
import { Share2 } from "lucide-vue-next";

// === 1. 状态管理：左右两栏的宽度 ===
const leftWidth = ref(240);
const rightWidth = ref(320);

// 定义最小和最大宽度
const MIN_LEFT = 200;
const MAX_LEFT = 400;
const MIN_RIGHT = 280;
const MAX_RIGHT = 600; // 右侧最大宽度稍微放宽一点，方便看图

// === 2. 核心拖拽逻辑 (保持不变) ===
const isDragging = ref(false);

const startResize = (direction: 'left' | 'right', startEvent: MouseEvent) => {
  startEvent.preventDefault();
  isDragging.value = true;
  
  const startX = startEvent.clientX;
  const startWidth = direction === 'left' ? leftWidth.value : rightWidth.value;

  const onMouseMove = (moveEvent: MouseEvent) => {
    const deltaX = moveEvent.clientX - startX;
    
    if (direction === 'left') {
      const newWidth = startWidth + deltaX;
      if (newWidth >= MIN_LEFT && newWidth <= MAX_LEFT) {
        leftWidth.value = newWidth;
      }
    } else {
      const newWidth = startWidth - deltaX;
      if (newWidth >= MIN_RIGHT && newWidth <= MAX_RIGHT) {
        rightWidth.value = newWidth;
      }
    }
  };

  const onMouseUp = () => {
    isDragging.value = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    document.body.style.cursor = '';
  };

  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
  document.body.style.cursor = 'col-resize';
};
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-[#F3F3F3] text-slate-800 font-sans text-sm">
    
    <div :style="{ width: leftWidth + 'px' }" class="shrink-0 flex flex-col h-full relative">
      <Sidebar />
    </div>

    <div 
      class="w-1 hover:w-1.5 h-full cursor-col-resize z-50 flex justify-center items-center group -ml-0.5 hover:bg-blue-500/10 transition-colors"
      @mousedown="(e) => startResize('left', e)"
    >
      <div class="w-[1px] h-full bg-slate-200 group-hover:bg-blue-400 transition-colors"></div>
    </div>

    <main class="flex-1 flex flex-col relative overflow-hidden bg-[#F0F2F5]">
      <div class="absolute inset-0 flex items-center justify-center select-none">
        <div class="text-center p-8">
          <div class="inline-block p-4 rounded-full bg-white shadow-sm text-blue-600 mb-4 animate-pulse">
            <Share2 class="h-10 w-10" />
          </div>
          <h2 class="text-xl font-bold text-slate-700">关系透镜</h2>
          <p class="text-slate-500 mt-2">宽度自适应演示</p>
        </div>
      </div>
    </main>

    <div 
      class="w-1 hover:w-1.5 h-full cursor-col-resize z-50 flex justify-center items-center group -mr-0.5 hover:bg-blue-500/10 transition-colors"
      @mousedown="(e) => startResize('right', e)"
    >
      <div class="w-[1px] h-full bg-slate-200 group-hover:bg-blue-400 transition-colors"></div>
    </div>

    <aside 
      :style="{ width: rightWidth + 'px' }"
      class="bg-white border-l border-slate-200 flex flex-col shrink-0 z-10 shadow-xl shadow-slate-200/50"
    >
      <Feed />
    </aside>

  </div>
</template>

<style>
body {
  margin: 0;
  font-family: 'Microsoft YaHei UI', 'Segoe UI', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>
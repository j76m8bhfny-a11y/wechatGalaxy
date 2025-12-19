<script setup lang="ts">
import { ref, onUnmounted } from 'vue';
import Sidebar from "./components/Sidebar.vue";
import { MoreHorizontal, Share2 } from "lucide-vue-next";

// === 1. 状态管理：左右两栏的宽度 ===
const leftWidth = ref(240); // 左侧默认宽度
const rightWidth = ref(320); // 右侧默认宽度

// 定义最小和最大宽度，防止拖崩坏
const MIN_LEFT = 200;
const MAX_LEFT = 400;
const MIN_RIGHT = 280;
const MAX_RIGHT = 500;

// === 2. 核心拖拽逻辑 ===
const isDragging = ref(false); // 是否正在拖拽中（用于控制全局光标）

// 通用的拖拽处理函数
const startResize = (direction: 'left' | 'right', startEvent: MouseEvent) => {
  // 阻止默认文本选中行为
  startEvent.preventDefault();
  isDragging.value = true;
  
  // 记录初始位置和初始宽度
  const startX = startEvent.clientX;
  const startWidth = direction === 'left' ? leftWidth.value : rightWidth.value;

  // 鼠标移动事件
  const onMouseMove = (moveEvent: MouseEvent) => {
    const deltaX = moveEvent.clientX - startX;
    
    if (direction === 'left') {
      // 左侧逻辑：往右拖增加宽度
      const newWidth = startWidth + deltaX;
      // 限制范围
      if (newWidth >= MIN_LEFT && newWidth <= MAX_LEFT) {
        leftWidth.value = newWidth;
      }
    } else {
      // 右侧逻辑：往左拖是增加宽度（因为是从右边算的），也就是 deltaX 为负数时宽度增加
      // 实际上右侧栏在 Flex 布局中，改变宽度就是直接改变 width 样式
      // 注意：这里我们是改变 div 的宽度，往左拖动鼠标，clientX 变小，deltaX 为负。
      // 为了让宽度变大，应该是 startWidth - deltaX
      const newWidth = startWidth - deltaX;
      if (newWidth >= MIN_RIGHT && newWidth <= MAX_RIGHT) {
        rightWidth.value = newWidth;
      }
    }
  };

  // 鼠标抬起事件（结束拖拽）
  const onMouseUp = () => {
    isDragging.value = false;
    document.removeEventListener('mousemove', onMouseMove);
    document.removeEventListener('mouseup', onMouseUp);
    // 恢复 body 的光标
    document.body.style.cursor = '';
  };

  // 绑定全局事件（防止鼠标滑太快出界）
  document.addEventListener('mousemove', onMouseMove);
  document.addEventListener('mouseup', onMouseUp);
  // 强制设置全局光标为拖拽样式
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
      
      <div class="h-12 border-b border-slate-100 flex items-center justify-between px-4 bg-white shrink-0 select-none">
        <span class="font-bold text-slate-700">情报档案</span>
        <button class="p-1.5 hover:bg-slate-50 rounded text-slate-400">
          <MoreHorizontal class="h-4 w-4" />
        </button>
      </div>

      <div class="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        <div class="bg-white rounded border border-slate-200 shadow-sm p-3 hover:shadow-md transition-shadow cursor-default group">
          <div class="flex justify-between items-start mb-2">
             <div class="flex items-center space-x-2">
               <span class="font-bold text-slate-800">张总</span>
               <span class="text-[10px] text-slate-400">10分钟前</span>
             </div>
             <span class="bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-[3px] text-[10px] font-medium">商务宴请</span>
          </div>
          <p class="text-xs text-slate-600 leading-relaxed mb-2.5">
            这里的宽度现在可以随意调整了。
          </p>
        </div>
      </div>
    </aside>

  </div>
</template>

<style>
/* 防止拖拽时选中文字，提升体验 */
body {
  margin: 0;
  font-family: 'Microsoft YaHei UI', 'Segoe UI', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

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
<script setup lang="ts">
import Sidebar from "./components/Sidebar.vue";
import { MoreHorizontal, Share2 } from "lucide-vue-next";
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-[#F3F3F3] text-slate-800 font-sans text-sm">
    
    <Sidebar class="shrink-0" />

    <main class="flex-1 flex flex-col relative overflow-hidden bg-[#F0F2F5]">
      
      <div class="absolute inset-0 flex items-center justify-center">
        <div class="text-center p-8">
          <div class="inline-block p-4 rounded-full bg-white shadow-sm text-blue-600 mb-4 animate-pulse">
            <Share2 class="h-10 w-10" />
          </div>
          <h2 class="text-xl font-bold text-slate-700">关系透镜准备就绪</h2>
          <p class="text-slate-500 mt-2">点击左侧列表，此处将展开 <span class="font-bold text-blue-600">[张总]</span> 的人脉星系</p>
          <p class="text-xs text-slate-400 mt-4">Graph Engine Standing By...</p>
        </div>
      </div>
    </main>

    <aside class="w-[320px] bg-white border-l border-slate-200 flex flex-col shrink-0 z-10 shadow-xl shadow-slate-200/50">
      
      <div class="h-12 border-b border-slate-100 flex items-center justify-between px-4 bg-white shrink-0">
        <span class="font-bold text-slate-700">情报档案</span>
        <div class="flex space-x-1">
           <button class="p-1.5 hover:bg-slate-50 rounded text-slate-400">
             <MoreHorizontal class="h-4 w-4" />
           </button>
        </div>
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
            今天和华南区的合作伙伴在深圳湾壹号聚餐，感谢大家的支持。今年的目标是两个亿！
          </p>
          
          <div class="grid grid-cols-3 gap-1 mb-3">
             <div class="aspect-square bg-slate-100 rounded-sm"></div>
             <div class="aspect-square bg-slate-100 rounded-sm"></div>
             <div class="aspect-square bg-slate-100 rounded-sm"></div>
          </div>

          <div class="flex items-center justify-between pt-2 border-t border-slate-50">
             <div class="flex space-x-3 text-[10px] text-slate-400">
                <span class="flex items-center hover:text-blue-600 cursor-pointer transition-colors">
                  <span class="mr-1">👍</span> 24
                </span>
                <span class="flex items-center hover:text-blue-600 cursor-pointer transition-colors">
                  <span class="mr-1">💬</span> 5
                </span>
             </div>
             <button class="text-[10px] text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity font-medium hover:underline">
               AI 生成评论
             </button>
          </div>
        </div>

      </div>
    </aside>

  </div>
</template>

<style>
body {
  margin: 0;
  font-family: 'Microsoft YaHei UI', 'Segoe UI', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* 右侧栏也可以用细滚动条 */
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
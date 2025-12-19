<script setup lang="ts">
import Sidebar from "./components/Sidebar.vue";
import { MoreHorizontal, Share2, MessageSquare } from "lucide-vue-next";
</script>

<template>
  <div class="flex h-screen w-screen overflow-hidden bg-[#F3F3F3] text-slate-800 font-sans">
    
    <Sidebar class="shrink-0" />

    <main class="flex-1 flex flex-col relative overflow-hidden">
      <div class="absolute inset-0 flex items-center justify-center bg-[#F3F3F3]">
        <div class="text-center">
          <div class="inline-block p-4 rounded-full bg-blue-100 text-blue-600 mb-4 animate-pulse">
            <Share2 class="h-8 w-8" />
          </div>
          <h2 class="text-lg font-bold text-slate-700">关系透镜准备就绪</h2>
          <p class="text-sm text-slate-500 mt-2">点击左侧列表，此处将展开 [张总] 的人脉星系</p>
        </div>
      </div>
    </main>

    <aside class="w-[400px] bg-white border-l border-slate-200 flex flex-col shrink-0">
      
      <div class="h-14 border-b border-slate-100 flex items-center justify-between px-6 bg-white">
        <span class="font-bold text-base">情报档案</span>
        <div class="flex space-x-2">
           <button class="p-2 hover:bg-slate-50 rounded-md text-slate-400">
             <MoreHorizontal class="h-5 w-5" />
           </button>
        </div>
      </div>

      <div class="flex-1 overflow-y-auto p-6 space-y-6">
        
        <div class="bg-white rounded-lg border border-slate-200 shadow-sm p-4 hover:shadow-md transition-shadow cursor-default">
          <div class="flex justify-between items-start mb-3">
             <div class="flex items-center space-x-2">
               <span class="font-bold text-slate-800">张总</span>
               <span class="text-xs text-slate-400">10分钟前</span>
             </div>
             <span class="bg-blue-50 text-blue-600 px-2 py-0.5 rounded text-xs font-medium">商务宴请</span>
          </div>
          
          <p class="text-sm text-slate-600 leading-relaxed mb-3">
            今天和华南区的合作伙伴在深圳湾壹号聚餐，感谢大家的支持。今年的目标是两个亿！
          </p>
          
          <div class="grid grid-cols-3 gap-1 mb-4">
             <div class="aspect-square bg-slate-100 rounded-md"></div>
             <div class="aspect-square bg-slate-100 rounded-md"></div>
             <div class="aspect-square bg-slate-100 rounded-md"></div>
          </div>

          <div class="flex items-center justify-between pt-3 border-t border-slate-50">
             <div class="flex space-x-4 text-xs text-slate-500">
                <span class="flex items-center hover:text-blue-600 cursor-pointer">
                  <span class="mr-1">👍</span> 24
                </span>
                <span class="flex items-center hover:text-blue-600 cursor-pointer">
                  <span class="mr-1">💬</span> 5
                </span>
             </div>
             <button class="text-xs text-blue-600 font-medium hover:underline">
               AI 生成评论
             </button>
          </div>
        </div>

      </div>
    </aside>

  </div>
</template>

<style>
/* 全局样式：设置字体，保证 Windows 下显示清晰 */
body {
  margin: 0;
  font-family: 'Microsoft YaHei UI', 'Segoe UI', system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}
</style>
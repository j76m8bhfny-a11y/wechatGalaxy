<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore, type Moment } from '../stores/moments';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const store = useMomentsStore();

// --- 核心算法：构建全网拓扑 + BFS 搜索 ---
const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  if (!centerId) {
    return { title: { text: '请选择核心人物', left: 'center', top: 'center', textStyle: { color: '#aaa' } } };
  }

  // 1. 构建全网邻接表 (Adjacency List)
  const globalGraph = new Map<string, Set<string>>();
  
  const addEdge = (u: string, v: string) => {
    if (u === v) return;
    if (!globalGraph.has(u)) globalGraph.set(u, new Set());
    if (!globalGraph.has(v)) globalGraph.set(v, new Set());
    globalGraph.get(u)!.add(v);
    globalGraph.get(v)!.add(u);
  };

  // 遍历所有数据建立严格关系
  // 规则：作者-点赞者，作者-评论者。不包含点赞者之间。
  const moments = store.moments || [];
  moments.forEach((m: Moment) => {
    const author = m.author_wxid;
    if (m.interactions?.likes) {
      m.interactions.likes.forEach(user => {
        if (user.wxid) addEdge(author, user.wxid);
      });
    }
    if (m.interactions?.comments) {
      m.interactions.comments.forEach(comment => {
        if (comment.wxid) addEdge(author, comment.wxid);
      });
    }
  });

  // 2. BFS (广度优先搜索) 延伸 6 级
  const MAX_LEVEL = 6;
  const MAX_NODES = 150; // 稍微放宽一点节点限制
  
  const visited = new Map<string, number>(); // 记录节点 -> 层级
  const queue: { id: string, level: number }[] = [];
  
  // 初始化
  queue.push({ id: centerId, level: 0 });
  visited.set(centerId, 0);

  const validNodeIds = new Set<string>();

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;
    if (validNodeIds.size >= MAX_NODES) break;
    validNodeIds.add(id);

    if (level < MAX_LEVEL) {
      const neighbors = globalGraph.get(id);
      if (neighbors) {
        neighbors.forEach(neighborId => {
          if (!visited.has(neighborId)) {
            visited.set(neighborId, level + 1);
            queue.push({ id: neighborId, level: level + 1 });
          }
        });
      }
    }
  }

  // 3. 生成 ECharts 数据 (应用新的颜色和大小规则)
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    
    // --- 新的大小规则 (差异更明显) ---
    let size = 15; // 默认 Level 3+
    if (level === 0) size = 65;      // 你 (最大)
    else if (level === 1) size = 45; // 好友 (中等)
    else if (level === 2) size = 28; // 朋友的朋友 (较小)
    
    resultNodes.push({
      id: id,
      name: id,
      symbolSize: size,
      value: `Level ${level}`,
      category: level, // 这里对应下面定义的 color 数组索引
      label: { 
        show: level <= 1,
        fontSize: level === 0 ? 12 : 10,
        fontWeight: level === 0 ? 'bold' : 'normal',
        color: level === 0 ? '#fff' : '#333' // 核心人物文字白色
      },
      // 注意：这里不再需要 itemStyle.color，改用全局调色板
    });
  });

  // 生成连线
  const linkSet = new Set<string>();
  validNodeIds.forEach(source => {
    const neighbors = globalGraph.get(source);
    if (neighbors) {
      neighbors.forEach(target => {
        if (validNodeIds.has(target)) {
          const key = source < target ? `${source}-${target}` : `${target}-${source}`;
          if (!linkSet.has(key)) {
            linkSet.add(key);
            resultLinks.push({
              source, target,
              lineStyle: { width: 1, opacity: 0.4, curveness: 0.1, color: '#ccc' }
            });
          }
        }
      });
    }
  });

  return {
    // --- 关键修改：自定义全局调色板 ---
    // ECharts 会按顺序把这些颜色分配给 category 0, 1, 2, 3...
    color: [
      '#1e40af', // Level 0: 深蓝 (商务旗舰蓝)
      '#3b82f6', // Level 1: 中蓝 (标准蓝)
      '#93c5fd', // Level 2: 浅蓝 (清透蓝)
      '#94a3b8', // Level 3: 灰色 (高级灰)
      '#94a3b8', // Level 4: 灰色
      '#94a3b8', // Level 5: 灰色
      '#94a3b8'  // Level 6: 灰色
    ],
    tooltip: { 
      trigger: 'item',
      formatter: (params: any) => {
         if (params.dataType === 'node') return `<b>${params.name}</b><br/>关系层级: ${params.value}`;
      }
    },
    // 图例 (可选，不想显示就注释掉 show: true)
    legend: {
      show: true,
      bottom: 5,
      data: ['核心 (You)', '1级好友', '2级人脉', '3级+ 路人'],
      textStyle: { color: '#666', fontSize: 10 }
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: resultNodes,
        links: resultLinks,
        // 定义分类名称，用于图例显示
        categories: [
          { name: '核心 (You)' },
          { name: '1级好友' },
          { name: '2级人脉' },
          { name: '3级+ 路人' },
          { name: '3级+ 路人' },
          { name: '3级+ 路人' },
          { name: '3级+ 路人' }
        ],
        roam: true,
        draggable: true,
        force: {
          repulsion: 200,
          gravity: 0.08,
          edgeLength: [40, 100],
          layoutAnimation: true
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 3, color: '#f59e0b' }
        }
      }
    ]
  };
});
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5] flex flex-col overflow-hidden">
    <div v-if="store.selectedWxid" class="absolute top-3 left-3 z-10 pointer-events-none select-none">
      <div class="bg-white/90 backdrop-blur px-3 py-2 rounded-lg border border-slate-200 shadow-sm">
        <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">RELATION LEVELS</div>
        <div class="text-sm font-bold text-slate-800 truncate max-w-[150px]">{{ store.selectedWxid }}</div>
        <div class="mt-1 flex flex-wrap gap-1 text-[10px]">
          <span class="px-1.5 py-0.5 bg-blue-800 text-white rounded-[2px]">L0 核心</span>
          <span class="px-1.5 py-0.5 bg-blue-500 text-white rounded-[2px]">L1 好友</span>
          <span class="px-1.5 py-0.5 bg-blue-300 text-slate-700 rounded-[2px]">L2 人脉</span>
          <span class="px-1.5 py-0.5 bg-slate-400 text-white rounded-[2px]">L3+</span>
        </div>
      </div>
    </div>

    <v-chart class="chart-canvas" :option="chartOption" autoresize />
  </div>
</template>

<style scoped>
.chart-canvas {
  width: 100%;
  height: 100%;
}
</style>
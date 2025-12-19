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

  // 1. 构建全网邻接表 (Adjacency List) & 权重表 (Edge Weights)
  const globalGraph = new Map<string, Set<string>>();
  const edgeWeights = new Map<string, number>(); // 新增：记录每条边的互动次数
  
  const addEdge = (u: string, v: string) => {
    if (u === v) return;
    
    // 1.1 建立图连接 (用于 BFS 寻路)
    if (!globalGraph.has(u)) globalGraph.set(u, new Set());
    if (!globalGraph.has(v)) globalGraph.set(v, new Set());
    globalGraph.get(u)!.add(v);
    globalGraph.get(v)!.add(u);

    // 1.2 记录互动权重 (用于画线的粗细)
    // 保证 key 的唯一性 (a-b 和 b-a 是同一条线)
    const key = u < v ? `${u}-${v}` : `${v}-${u}`;
    edgeWeights.set(key, (edgeWeights.get(key) || 0) + 1);
  };

  // 遍历数据
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
  const MAX_NODES = 150; 
  
  const visited = new Map<string, number>(); 
  const queue: { id: string, level: number }[] = [];
  
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

  // 3. 生成 ECharts 数据
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  // 生成节点
  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    
    // 大小规则
    let size = 15;
    if (level === 0) size = 65;      
    else if (level === 1) size = 45; 
    else if (level === 2) size = 28; 
    
    resultNodes.push({
      id: id,
      name: id,
      symbolSize: size,
      value: `Level ${level}`,
      category: level, 
      label: { 
        show: level <= 1,
        fontSize: level === 0 ? 12 : 10,
        fontWeight: level === 0 ? 'bold' : 'normal',
        color: level === 0 ? '#fff' : '#333' 
      }
    });
  });

  // 生成连线 (恢复权重逻辑！)
  const linkSet = new Set<string>();
  validNodeIds.forEach(source => {
    const neighbors = globalGraph.get(source);
    if (neighbors) {
      neighbors.forEach(target => {
        if (validNodeIds.has(target)) {
          const key = source < target ? `${source}-${target}` : `${target}-${source}`;
          
          if (!linkSet.has(key)) {
            linkSet.add(key);
            
            // 获取权重
            const weight = edgeWeights.get(key) || 1;
            
            // --- 视觉映射公式 ---
            // 宽度: 最细 1px (偶然互动)，最粗 6px (频繁互动)
            const lineWidth = Math.min(1 + (weight - 1) * 0.5, 6);
            
            // 颜色: 互动越多，颜色越深 (opacity 越高)
            // 基础颜色是 slate-400 (#94a3b8)
            const opacity = Math.min(0.3 + (weight * 0.1), 1);

            resultLinks.push({
              source, target,
              lineStyle: { 
                width: lineWidth, 
                opacity: opacity, 
                curveness: 0.1, 
                color: '#64748b' // 使用深一点的灰色作为基底
              },
              // 鼠标移上去显示的提示
              value: weight
            });
          }
        }
      });
    }
  });

  return {
    // 商务蓝渐变色板
    color: ['#1e40af', '#3b82f6', '#93c5fd', '#94a3b8', '#94a3b8', '#94a3b8', '#94a3b8'],
    
    tooltip: { 
      trigger: 'item',
      formatter: (params: any) => {
         if (params.dataType === 'node') return `<b>${params.name}</b><br/>关系层级: ${params.value}`;
         if (params.dataType === 'edge') return `<b>互动强度</b><br/>共计 ${params.value} 次`;
      }
    },
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
          lineStyle: { width: 4, color: '#f59e0b', opacity: 1 }
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
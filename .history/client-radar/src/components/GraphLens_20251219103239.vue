<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore, type Moment } from '../stores/moments';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const store = useMomentsStore();

// --- 临时工具：名称美化器 ---
const formatName = (wxid: string, isCenter: boolean) => {
  if (wxid.length > 10) {
    return isCenter ? wxid : `user_${wxid.substring(wxid.length - 4)}`;
  }
  return wxid;
};

// --- 核心算法 ---
const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  if (!centerId) {
    return { title: { text: '请选择核心人物', left: 'center', top: 'center', textStyle: { color: '#aaa' } } };
  }

  // 构建图谱
  const globalGraph = new Map<string, Set<string>>();
  const edgeWeights = new Map<string, number>();
  
  const addEdge = (u: string, v: string) => {
    if (u === v) return;
    if (!globalGraph.has(u)) globalGraph.set(u, new Set());
    if (!globalGraph.has(v)) globalGraph.set(v, new Set());
    globalGraph.get(u)!.add(v);
    globalGraph.get(v)!.add(u);

    const key = u < v ? `${u}-${v}` : `${v}-${u}`;
    edgeWeights.set(key, (edgeWeights.get(key) || 0) + 1);
  };

  const moments = store.moments || [];
  moments.forEach((m: Moment) => {
    const author = m.author_wxid;
    if (m.interactions?.likes) {
      m.interactions.likes.forEach(user => { if (user.wxid) addEdge(author, user.wxid); });
    }
    if (m.interactions?.comments) {
      m.interactions.comments.forEach(comment => { if (comment.wxid) addEdge(author, comment.wxid); });
    }
  });

  // BFS
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

  // 生成 ECharts 数据
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    const isCenter = level === 0;
    
    // 🆕 高亮逻辑：如果当前 store.filterWxid 选中了某人，给他加个特殊边框
    const isSelected = store.filterWxid === id;

    let size = 15;
    if (level === 0) size = 65;      
    else if (level === 1) size = 45; 
    else if (level === 2) size = 28; 
    
    resultNodes.push({
      id: id,
      name: formatName(id, isCenter),
      originalId: id,
      symbolSize: size,
      value: `Level ${level}`,
      category: level,
      label: { 
        show: level <= 1 || isSelected, // 选中时强制显示名字
        fontSize: isCenter ? 12 : 10,
        fontWeight: isCenter ? 'bold' : 'normal',
        color: isCenter ? '#fff' : '#333'
      },
      itemStyle: {
        // 选中时变成橙色，否则按层级走
        color: isSelected ? '#f97316' : null,
        shadowBlur: isSelected ? 10 : 0,
        shadowColor: '#f97316'
      }
    });
  });

  const linkSet = new Set<string>();
  validNodeIds.forEach(source => {
    const neighbors = globalGraph.get(source);
    if (neighbors) {
      neighbors.forEach(target => {
        if (validNodeIds.has(target)) {
          const key = source < target ? `${source}-${target}` : `${target}-${source}`;
          if (!linkSet.has(key)) {
            linkSet.add(key);
            const weight = edgeWeights.get(key) || 1;
            const lineWidth = Math.min(1 + (weight - 1) * 0.5, 6);
            const opacity = Math.min(0.3 + (weight * 0.1), 1);
            
            resultLinks.push({
              source, target,
              lineStyle: { width: lineWidth, opacity: opacity, curveness: 0.1, color: '#64748b' },
              value: weight
            });
          }
        }
      });
    }
  });

  return {
    color: ['#1e40af', '#3b82f6', '#93c5fd', '#94a3b8', '#94a3b8', '#94a3b8'],
    tooltip: { trigger: 'item' },
    legend: { show: true, bottom: 5, data: ['核心 (You)', '1级好友', '2级人脉', '3级+ 路人'], textStyle: { color: '#666', fontSize: 10 } },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: resultNodes,
        links: resultLinks,
        categories: [{ name: '核心 (You)' }, { name: '1级好友' }, { name: '2级人脉' }, { name: '3级+ 路人' }, { name: '3级+ 路人' }, { name: '3级+ 路人' }],
        roam: true,
        draggable: true,
        force: { repulsion: 200, gravity: 0.08, edgeLength: [40, 100], layoutAnimation: true },
        emphasis: { focus: 'adjacency', lineStyle: { width: 4, color: '#f59e0b', opacity: 1 } }
      }
    ]
  };
});

// --- 🆕 交互逻辑修改 ---
const handleNodeClick = (params: any) => {
  if (params.dataType === 'node') {
    const clickedWxid = params.data.originalId;
    
    // 如果点的是核心自己，或者是已经选中的人，就取消筛选
    if (clickedWxid === store.selectedWxid || clickedWxid === store.filterWxid) {
      console.log("取消筛选");
      store.filterWxid = '';
    } else {
      console.log("筛选互动:", clickedWxid);
      store.filterWxid = clickedWxid;
    }
  }
};

// 点击空白处取消筛选
const handleBlankClick = () => {
  if (store.filterWxid) {
    store.filterWxid = '';
  }
};
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5] flex flex-col overflow-hidden">
    <div v-if="store.selectedWxid" class="absolute top-3 left-3 z-10 pointer-events-none select-none">
      <div class="bg-white/90 backdrop-blur px-3 py-2 rounded-lg border border-slate-200 shadow-sm">
        <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">FILTER MODE</div>
        <div class="text-sm font-bold text-slate-800 truncate max-w-[150px]">{{ store.selectedWxid }}</div>
        
        <div v-if="store.filterWxid" class="mt-1 flex items-center space-x-1 animate-pulse">
           <span class="text-[10px] text-orange-500 font-bold">🔍 仅显示与 {{ formatName(store.filterWxid, false) }} 的互动</span>
        </div>
        <div v-else class="mt-1 text-[10px] text-slate-400">
           显示全部动态
        </div>
      </div>
    </div>

    <v-chart 
      class="chart-canvas" 
      :option="chartOption" 
      autoresize 
      @click="handleNodeClick"
      @zr:click="handleBlankClick"
    />
  </div>
</template>

<style scoped>
.chart-canvas {
  width: 100%;
  height: 100%;
}
</style>
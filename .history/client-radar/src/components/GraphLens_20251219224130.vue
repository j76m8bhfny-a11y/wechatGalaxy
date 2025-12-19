<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts'; // ✅ 找回这个引用
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const store = useMomentsStore();
const contactStore = useContactsStore(); // ✅ 实例化 Store

const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  
  // 空状态图表配置
  if (!centerId) {
    return {
      title: {
        text: '等待指令...\n请在左侧选择目标启动雷达',
        left: 'center',
        top: 'center',
        textStyle: { color: '#94a3b8', fontSize: 16, lineHeight: 24, fontWeight: 'normal' }
      }
    };
  }

  // 1. 构建图谱
  const globalGraph = new Map<string, Set<string>>();
  const edgeWeights = new Map<string, number>();
  
  const addEdge = (u: string, v: string) => {
    if (!u || !v || u === v) return;
    if (!globalGraph.has(u)) globalGraph.set(u, new Set());
    if (!globalGraph.has(v)) globalGraph.set(v, new Set());
    globalGraph.get(u)!.add(v);
    globalGraph.get(v)!.add(u);

    const key = u < v ? `${u}-${v}` : `${v}-${u}`;
    edgeWeights.set(key, (edgeWeights.get(key) || 0) + 1);
  };

  const moments = store.moments || [];
  // 只基于选中的人构建网络
  const targetMoments = moments.filter(m => m.author_wxid === centerId);

  targetMoments.forEach((m) => {
    const author = m.author_wxid;
    // 点赞连线
    if (m.interactions?.likes) {
      m.interactions.likes.forEach(user => { 
        addEdge(author, user.wxid); 
      });
    }
    // 评论连线
    if (m.interactions?.comments) {
      m.interactions.comments.forEach(comment => { 
        addEdge(author, comment.wxid); 
        // 回复连线
        if (comment.reply_to_wxid) {
          addEdge(comment.wxid, comment.reply_to_wxid);
        }
      });
    }
  });

  // 2. BFS 筛选节点
  const MAX_LEVEL = 2;
  const MAX_NODES = 80;
  
  const visited = new Map<string, number>();
  const queue: { id: string, level: number }[] = [];
  const validNodeIds = new Set<string>();

  queue.push({ id: centerId, level: 0 });
  visited.set(centerId, 0);

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

  // 3. 生成节点
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    
    // 节点大小
    let size = 10;
    if (level === 0) size = 60;      
    else if (level === 1) size = 25; 
    else if (level === 2) size = 12; 
    
    // 获取名字 (使用 Store 的智能查找，如果没有则用通讯录)
    let displayName = '';
    if (store.getSmartName) {
        displayName = store.getSmartName(id);
    } else {
        displayName = contactStore.getDisplayName(id);
    }

    resultNodes.push({
      id: id,
      name: displayName, 
      originalId: id,
      symbolSize: size,
      value: `层级: ${level}`,
      category: level,
      label: { 
        show: level <= 1, 
        position: 'right',
        formatter: '{b}',
        fontSize: level === 0 ? 14 : 12,
        fontWeight: level === 0 ? 'bold' : 'normal',
        color: '#334155'
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: level === 0 ? 4 : 1,
        shadowBlur: level === 0 ? 20 : 0,
        shadowColor: 'rgba(0,0,0,0.1)'
      }
    });
  });

  // 4. 生成连线
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
            const lineWidth = Math.min(1 + Math.log(weight), 5);
            
            resultLinks.push({
              source, 
              target,
              lineStyle: { width: lineWidth, curveness: 0.1, color: '#cbd5e1', opacity: 0.6 }
            });
          }
        }
      });
    }
  });

  return {
    // 核心蓝，一级橙，二级灰
    color: ['#3b82f6', '#f97316', '#94a3b8'], 
    tooltip: { trigger: 'item', formatter: '{b}' },
    legend: { 
      show: true, 
      bottom: 20, 
      left: 'center',
      data: [{name: '核心人物'}, {name: '一级密友'}, {name: '边缘关联'}],
      textStyle: { color: '#64748b' },
      itemGap: 20
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: resultNodes,
        links: resultLinks,
        categories: [{ name: '核心人物' }, { name: '一级密友' }, { name: '边缘关联' }],
        roam: true,
        draggable: true,
        force: {
          repulsion: 300,
          gravity: 0.08,
          edgeLength: [60, 180],
          layoutAnimation: true,
          friction: 0.6
        },
        emphasis: {
          focus: 'adjacency',
          scale: true,
          lineStyle: { width: 4, color: '#f59e0b', opacity: 1 }
        }
      }
    ]
  };
});

// 点击事件
const handleNodeClick = (params: any) => {
  if (params.dataType === 'node') {
    const clickedWxid = params.data.originalId; 
    if (clickedWxid !== store.selectedWxid) {
       store.filterWxid = clickedWxid;
    } else {
       store.filterWxid = '';
    }
  }
};

const handleBlankClick = () => {
  store.filterWxid = '';
};
</script>

<template>
  <div class="w-full h-full relative bg-slate-50/50 flex flex-col overflow-hidden">
    
    <div v-if="store.selectedWxid" class="absolute top-6 left-6 z-10 pointer-events-none select-none">
      <div class="bg-white/80 backdrop-blur-md px-5 py-4 rounded-2xl shadow-lg border border-white/60 min-w-[220px]">
        
        <div class="flex items-center space-x-2 mb-3">
          <div class="relative w-3 h-3">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-3 w-3 bg-blue-500"></span>
          </div>
          <div class="text-[10px] text-blue-500 font-bold uppercase tracking-widest">RADAR ACTIVE</div>
        </div>
        
        <div class="mb-3">
            <div class="text-xs text-slate-400 mb-0.5">探测目标</div>
            <div class="text-lg font-bold text-slate-800 truncate max-w-[180px]">
            {{ contactStore.getDisplayName(store.selectedWxid) }}
            </div>
        </div>

        <div class="grid grid-cols-2 gap-4 border-t border-slate-200/60 pt-3">
            <div>
                <div class="text-[10px] text-slate-400">朋友圈样本</div>
                <div class="text-sm font-semibold text-slate-600">{{ store.filteredMoments.length }} 条</div>
            </div>
            <div>
                <div class="text-[10px] text-slate-400">关联节点</div>
                <div class="text-sm font-semibold text-slate-600">{{ (chartOption.series as any)[0].data.length }} 个</div>
            </div>
        </div>

        <div v-if="store.filterWxid" class="mt-3 pt-2 border-t border-orange-100 flex items-center animate-pulse">
           <svg xmlns="http://www.w3.org/2000/svg" class="h-3 w-3 text-orange-500 mr-1.5" viewBox="0 0 20 20" fill="currentColor">
             <path fill-rule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clip-rule="evenodd" />
           </svg>
           <div class="text-xs text-orange-600 font-bold">
             正在追踪: {{ store.getSmartName ? store.getSmartName(store.filterWxid) : contactStore.getDisplayName(store.filterWxid) }}
           </div>
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
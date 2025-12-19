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
  // 注意：不再只看选中的人，而是基于全局数据构建关系网，这样才能发现 A->B 后，B 在自己朋友圈和 C 的关系
  const globalGraph = new Map<string, Set<string>>();
  const edgeWeights = new Map<string, number>();
  
  const addEdge = (u: string, v: string) => {
    if (!u || !v || u === v) return;
    if (!globalGraph.has(u)) globalGraph.set(u, new Set());
    if (!globalGraph.has(v)) globalGraph.set(v, new Set());
    
    // 建立双向索引以便 BFS 遍历
    globalGraph.get(u)!.add(v);
    globalGraph.get(v)!.add(u);

    // 记录边的权重（这里简化处理，始终记录 u-v 形式）
    const key = u < v ? `${u}-${v}` : `${v}-${u}`;
    edgeWeights.set(key, (edgeWeights.get(key) || 0) + 1);
  };

  // 🔥 [关键修改1] 移除 filter，扫描所有已加载的瞬间，寻找潜在的关联链条
  // 原代码: const targetMoments = moments.filter(m => m.author_wxid === centerId);
  const allMoments = store.moments || []; 

  allMoments.forEach((m) => {
    const author = m.author_wxid;
    // 只处理有点赞或评论的数据，减少计算量
    if (!m.interactions) return;

    // 点赞连线 (Author <-> Liker)
    if (m.interactions.likes) {
      m.interactions.likes.forEach(user => { 
        addEdge(author, user.wxid); 
      });
    }
    // 评论连线 (Author <-> Commenter)
    if (m.interactions.comments) {
      m.interactions.comments.forEach(comment => { 
        addEdge(author, comment.wxid); 
        // 回复连线 (Commenter <-> Replier)
        if (comment.reply_to_wxid) {
          addEdge(comment.wxid, comment.reply_to_wxid);
        }
      });
    }
  });

  // 2. BFS 筛选节点
  // 🔥 [关键修改2] 增加层级深度，允许 A->B->C->D (Level 0->1->2->3)
  const MAX_LEVEL = 4; 
  // 为了防止节点过多导致卡顿，稍微限制最大节点数，或者你可以根据性能调大到 100+
  const MAX_NODES = 100;
  
  const visited = new Map<string, number>();
  const queue: { id: string, level: number }[] = [];
  const validNodeIds = new Set<string>();

  queue.push({ id: centerId, level: 0 });
  visited.set(centerId, 0);

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;
    
    // 如果超过节点限制且不是核心层，停止扩散
    if (validNodeIds.size >= MAX_NODES && level > 1) break;
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
    
    // 根据层级调整大小
    let size = 10;
    if (level === 0) size = 60;      
    else if (level === 1) size = 30; 
    else if (level === 2) size = 15;
    else if (level >= 3) size = 8; // 更深层级更小
    
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
        show: level <= 3, // 只有前4级显示名字，避免杂乱
        position: 'right',
        formatter: '{b}',
        fontSize: level === 0 ? 14 : 12,
        color: '#334155'
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: level === 0 ? 4 : 1,
        shadowBlur: level === 0 ? 20 : 0
      }
    });
  });

  // 4. 生成连线
  const linkSet = new Set<string>();
  validNodeIds.forEach(source => {
    const neighbors = globalGraph.get(source);
    if (neighbors) {
      neighbors.forEach(target => {
        // 只有当两个点都在我们筛选出的圈子里时，才画线
        if (validNodeIds.has(target)) {
          // 为了避免重复画线 (A-B 和 B-A)，我们使用唯一Key
          const key = source < target ? `${source}-${target}` : `${target}-${source}`;
          if (!linkSet.has(key)) {
            linkSet.add(key);
            const weight = edgeWeights.get(key) || 1;
            
            resultLinks.push({
              source, 
              target,
              // 🔥 [关键修改3] 增加箭头
              symbol: ['none', 'arrow'],
              symbolSize: [0, 8],
              lineStyle: { 
                width: Math.min(1 + Math.log(weight), 4), 
                curveness: 0.1, 
                color: '#cbd5e1', 
                opacity: 0.6 
              }
            });
          }
        }
      });
    }
  });

  return {
    color: ['#3b82f6', '#f97316', '#94a3b8'], 
    tooltip: { trigger: 'item', formatter: '{b}' },
    legend: { 
      show: true, 
      bottom: 20, 
      data: [{name: '核心人物'}, {name: '一级密友'}, {name: '边缘关联'}]
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
        // 🔥 [关键修改4] 调整力导向参数，让长链条能舒展开
        force: {
          repulsion: 400, // 增大斥力
          gravity: 0.05,  // 减小引力，让节点更松散
          edgeLength: [50, 250], // 允许边更长
          layoutAnimation: true,
          friction: 0.6
        },
        edgeSymbol: ['none', 'arrow'], // 全局箭头配置
        edgeSymbolSize: 6,
        emphasis: {
          focus: 'adjacency',
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
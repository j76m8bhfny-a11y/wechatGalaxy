<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore, type Moment } from '../stores/moments';
import { useContactsStore } from '../stores/contacts'; // 仅用于顶部标题
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const store = useMomentsStore();
const contactStore = useContactsStore();

const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  
  if (!centerId) {
    return {
      title: {
        text: '请在左侧选择一位好友\n开启人脉雷达',
        left: 'center',
        top: 'center',
        textStyle: { color: '#94a3b8', fontSize: 14, lineHeight: 20 }
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
  
  // 🔥🔥🔥 这里的关键改动：我们遍历的是【原始数据】，不依赖任何左侧筛选
  // 只要 filter 后在这个列表里出现过的人，都要进图
  const targetMoments = moments.filter(m => m.author_wxid === centerId);

  targetMoments.forEach((m: Moment) => {
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

  // 2. BFS 筛选
  const MAX_LEVEL = 2; // 聚焦核心圈
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

  // 3. 生成节点 (使用 store.getSmartName)
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    
    let size = 10;
    if (level === 0) size = 50;      
    else if (level === 1) size = 25; 
    else if (level === 2) size = 10; 
    
    // 🔥 使用 Store 的超级查名器，确保所有人都有名字 🔥
    let displayName = store.getSmartName(id);

    resultNodes.push({
      id: id,
      name: displayName, 
      originalId: id,
      symbolSize: size,
      value: `层级: ${level}`,
      category: level,
      label: { 
        show: level <= 1, // 只有核心和一级好友显示名字
        position: 'right',
        formatter: '{b}' 
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1
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
            const lineWidth = Math.min(1 + Math.log(weight), 4);
            
            resultLinks.push({
              source, 
              target,
              lineStyle: { width: lineWidth, curveness: 0.2, color: '#cbd5e1' }
            });
          }
        }
      });
    }
  });

  return {
    color: ['#3b82f6', '#f59e0b', '#94a3b8'], // 核心蓝，一级橙，二级灰
    tooltip: { trigger: 'item', formatter: '{b}' },
    legend: { show: true, bottom: 5, data: [{name: '核心人物'}, {name: '一级密友'}, {name: '边缘关联'}] },
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
          repulsion: 200,
          gravity: 0.1,
          edgeLength: [50, 120],
          layoutAnimation: true
        },
        emphasis: {
          focus: 'adjacency',
          lineStyle: { width: 4, color: '#ef4444', opacity: 1 }
        }
      }
    ]
  };
});

// 点击节点筛选右侧
const handleNodeClick = (params: any) => {
  if (params.dataType === 'node') {
    const clickedWxid = params.data.originalId; 
    // 如果点的不是核心，就筛选他
    if (clickedWxid !== store.selectedWxid) {
       store.filterWxid = clickedWxid;
    } else {
       store.filterWxid = ''; // 点核心取消筛选
    }
  }
};

const handleBlankClick = () => {
  store.filterWxid = '';
};
</script>

<template>
  <div class="w-full h-full relative bg-slate-50 flex flex-col overflow-hidden">
    <div v-if="store.selectedWxid" class="absolute top-4 left-4 z-10 pointer-events-none select-none">
      <div class="bg-white/90 backdrop-blur px-4 py-2 rounded-xl border border-slate-200 shadow-sm">
        <div class="text-[10px] text-blue-500 font-bold uppercase tracking-wider mb-0.5">RELATIONSHIP MAP</div>
        <div class="text-base font-bold text-slate-800">
          {{ store.getSmartName(store.selectedWxid) }}
        </div>
        <div class="flex items-center space-x-2 mt-1" v-if="store.filterWxid">
           <span class="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
           <span class="text-xs text-orange-600 font-bold">聚焦: {{ store.getSmartName(store.filterWxid) }}</span>
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
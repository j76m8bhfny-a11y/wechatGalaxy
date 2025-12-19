<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore, type Moment } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const store = useMomentsStore();
const contactStore = useContactsStore();

// --- 核心算法 ---
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

  // 1. 建立一个“全量名字查询表” (快照名优先)
  // 这是修复问题的关键！我们把 Store 里计算好的包含了“陌生人快照名”的列表转成 Map
  const nameMap = new Map<string, string>();
  store.contacts.forEach(c => {
    if (c.name && c.name !== c.id && c.name !== '未知用户') {
      nameMap.set(c.id, c.name);
    }
  });

  // 2. 构建图谱
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

  // 3. 挖掘关系
  const moments = store.moments || [];
  moments.forEach((m: Moment) => {
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
        // 关键：回复关系连线 (A-B-D)
        if (comment.reply_to_wxid) {
          addEdge(comment.wxid, comment.reply_to_wxid);
        }
      });
    }
  });

  // 4. BFS 筛选核心圈
  const MAX_LEVEL = 3;
  const MAX_NODES = 120;
  
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

  // 5. 生成节点数据
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    
    // 节点大小
    let size = 10;
    if (level === 0) size = 50;      
    else if (level === 1) size = 30; 
    else if (level === 2) size = 15; 
    
    // 🔥🔥🔥 关键修复：获取名字的优先级 🔥🔥🔥
    // 1. 先查 nameMap (这里有从评论区抓取的快照名)
    // 2. 再查 contactStore (通讯录备注)
    // 3. 最后用 ID 兜底
    let displayName = nameMap.get(id);
    if (!displayName) {
       displayName = contactStore.getDisplayName(id);
    }
    if (!displayName || displayName === '未知用户') {
       displayName = id; // 实在没有名字，显示 wxid
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
        formatter: '{b}' 
      },
      itemStyle: {
        borderColor: '#fff',
        borderWidth: 1
      }
    });
  });

  // 6. 生成连线数据
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
    color: ['#3b82f6', '#0ea5e9', '#94a3b8', '#cbd5e1'],
    tooltip: { trigger: 'item', formatter: '{b}' },
    legend: { show: true, bottom: 10, data: [{name: '核心人物'}, {name: '一级密友'}, {name: '二级人脉'}, {name: '边缘关联'}] },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: resultNodes,
        links: resultLinks,
        categories: [{ name: '核心人物' }, { name: '一级密友' }, { name: '二级人脉' }, { name: '边缘关联' }],
        roam: true,
        draggable: true,
        force: {
          repulsion: 250,
          gravity: 0.1,
          edgeLength: [50, 150],
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
  <div class="w-full h-full relative bg-slate-50 flex flex-col overflow-hidden">
    <div v-if="store.selectedWxid" class="absolute top-4 left-4 z-10 pointer-events-none select-none">
      <div class="bg-white/90 backdrop-blur px-4 py-3 rounded-xl border border-slate-200 shadow-sm">
        <div class="text-[10px] text-blue-500 font-bold uppercase tracking-wider mb-1">NETWORK RADAR</div>
        <div class="text-base font-bold text-slate-800">
          {{ contactStore.getDisplayName(store.selectedWxid) }}
        </div>
        <div class="text-xs text-slate-400 mt-1">
          检测到 {{ (chartOption.series as any)[0].data.length }} 个关联节点
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
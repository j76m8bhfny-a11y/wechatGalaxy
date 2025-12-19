<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
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

const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  if (!centerId) {
    return { title: { text: '请选择一位核心人物', left: 'center', top: 'center', textStyle: { color: '#aaa' } } };
  }

  // --- 1. 构建全网关系矩阵 (Adjacency Matrix) ---
  // 我们不仅仅看“我”和“别人”，还要看“别人”和“别人”是否在同一条朋友圈共现
  const linksMap = new Map<string, number>(); // 记录 "id1-id2" -> 权重
  const nodeWeights = new Map<string, number>(); // 记录每个人的总活跃度
  
  const addLink = (id1: string, id2: string) => {
    if (id1 === id2) return;
    // 保证 key 的顺序一致，避免 a-b 和 b-a 重复
    const key = id1 < id2 ? `${id1}|${id2}` : `${id2}|${id1}`;
    linksMap.set(key, (linksMap.get(key) || 0) + 1);
  };

  const moments = store.currentMoments || [];
  
  moments.forEach(m => {
    if (!m.interactions) return;
    // 提取这条朋友圈下所有的参与者（包括点赞和评论）
    const participants = new Set<string>();
    // 把主角自己也加进去，这样主角和所有人都有连线
    participants.add(centerId); 
    
    [...(m.interactions.likes || []), ...(m.interactions.comments || [])].forEach(user => {
      if (user && user.wxid) {
        participants.add(user.wxid);
        // 增加个人权重
        nodeWeights.set(user.wxid, (nodeWeights.get(user.wxid) || 0) + 1);
      }
    });

    // 关键步骤：两两连线 (全连接)
    // 如果张三、李四、王五都在这条朋友圈互动，说明他们是一个圈子的
    const list = Array.from(participants);
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        addLink(list[i], list[j]);
      }
    }
  });

  // --- 2. 筛选节点与连线 ---
  const nodes: any[] = [];
  const links: any[] = [];
  
  // 找出所有涉及的人
  const allNodes = new Set<string>();
  linksMap.forEach((weight, key) => {
    const [source, target] = key.split('|');
    allNodes.add(source);
    allNodes.add(target);
  });

  // 为了性能，只保留和中心人物有直接或间接关系的前 60 人 (基于活跃度)
  const sortedNodes = Array.from(allNodes)
    .sort((a, b) => (nodeWeights.get(b) || 0) - (nodeWeights.get(a) || 0))
    .slice(0, 60); // 限制节点数，防止图表炸裂
  
  const validNodesSet = new Set(sortedNodes);

  // 生成 ECharts Nodes
  sortedNodes.forEach(wxid => {
    const isCenter = wxid === centerId;
    const weight = nodeWeights.get(wxid) || 1;
    // 节点大小
    const size = isCenter ? 60 : 15 + Math.min(weight * 2, 30);
    
    nodes.push({
      id: wxid,
      name: wxid,
      symbolSize: size,
      value: weight,
      category: isCenter ? 0 : 1, // 0:核心, 1:关联
      itemStyle: { 
        color: isCenter ? '#2563eb' : null // 核心蓝，其他人自动配色
      },
      label: { 
        show: size > 20, 
        fontSize: 10,
        formatter: (p: any) => p.name.length > 4 ? p.name.substring(0,4)+'..' : p.name
      },
      draggable: true
    });
  });

  // 生成 ECharts Links
  linksMap.forEach((weight, key) => {
    const [source, target] = key.split('|');
    // 只保留都在前60名名单里的连线
    if (validNodesSet.has(source) && validNodesSet.has(target)) {
      links.push({
        source,
        target,
        lineStyle: {
          width: Math.min(weight, 5), // 共现次数越多，线越粗
          opacity: 0.6,
          curveness: 0.2 // 稍微弯曲一点，更有网络感
        }
      });
    }
  });

  return {
    tooltip: { trigger: 'item' },
    legend: { show: false },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: nodes,
        links: links,
        categories: [{ name: '核心' }, { name: '关联' }],
        roam: true,
        label: { position: 'right' },
        force: {
          repulsion: 200, // 斥力
          gravity: 0.05,  // 引力小一点，让图散开
          edgeLength: [30, 100], // 连线长度
          layoutAnimation: true
        },
        emphasis: {
          focus: 'adjacency', // 鼠标移上去，只高亮相关联的一串人
          lineStyle: { width: 5, color: '#f59e0b' } // 高亮变成橙色
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
        <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">NETWORK MESH</div>
        <div class="text-sm font-bold text-slate-800">{{ store.selectedWxid }}</div>
        <div class="mt-1 flex items-center space-x-2 text-[10px] text-slate-500">
          <span class="inline-block w-2 h-2 rounded-full bg-blue-500"></span>
          <span>共现分析模式</span>
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
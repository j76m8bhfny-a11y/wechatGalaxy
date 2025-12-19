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

// 1. 注册 ECharts 组件
use([
  CanvasRenderer,
  GraphChart,
  TitleComponent,
  TooltipComponent,
  LegendComponent
]);

const store = useMomentsStore();

// 2. 核心数据转换：Store -> ECharts Option
const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  
  // 空状态
  if (!centerId) {
    return {
      title: {
        text: '请在左侧选择一位客户',
        left: 'center',
        top: 'center',
        textStyle: { color: '#94a3b8', fontSize: 14 }
      }
    };
  }

  // --- 组装数据 ---
  const nodes: any[] = [];
  const links: any[] = [];

  // A. 添加中心节点 (主角)
  nodes.push({
    id: centerId,
    name: centerId,
    symbolSize: 50, // 主角大一点
    itemStyle: { color: '#2563eb' }, // 商务蓝
    label: { show: true, fontWeight: 'bold', fontSize: 12 },
    category: 0
  });

  // B. 统计互动数据
  const interactionMap = new Map<string, number>();
  // 防护：防止 currentMoments 为空
  const moments = store.currentMoments || [];
  
  moments.forEach(m => {
    // 防护：防止 interactions 结构不完整
    if (!m.interactions) return;
    const allInteractions = [...(m.interactions.likes || []), ...(m.interactions.comments || [])];
    
    allInteractions.forEach(user => {
      if (user && user.wxid && user.wxid !== centerId) {
        const count = interactionMap.get(user.wxid) || 0;
        interactionMap.set(user.wxid, count + 1);
      }
    });
  });

  // C. 生成卫星节点 (前 30 名)
  const topList = Array.from(interactionMap.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 30);

  topList.forEach(([wxid, count]) => {
    // 节点大小 (20~40)
    const size = 20 + Math.min(count * 2, 20);
    
    nodes.push({
      id: wxid,
      name: wxid,
      symbolSize: size,
      value: count, // 鼠标悬停显示互动数
      itemStyle: { color: '#64748b' }, // 灰色
      label: { show: size > 25, fontSize: 10, color: '#64748b' } // 大节点才显示名字
    });

    links.push({
      source: centerId,
      target: wxid,
      lineStyle: {
        width: Math.min(count, 5), // 线宽
        color: '#cbd5e1'
      }
    });
  });

  // --- ECharts 配置 ---
  return {
    // 提示框
    tooltip: {
      trigger: 'item',
      formatter: (params: any) => {
        if (params.dataType === 'node') {
          return `${params.name}<br/>互动次数: ${params.value || '核心'}`;
        }
      }
    },
    // 核心图表配置
    series: [
      {
        type: 'graph',
        layout: 'force', // 物理引擎布局
        data: nodes,
        links: links,
        roam: true, // 允许缩放和平移
        draggable: true, // 节点可拖拽
        label: { position: 'bottom' },
        force: {
          repulsion: 300, // 斥力：让节点散开
          edgeLength: [50, 120], // 连线长度范围
          gravity: 0.1 // 引力：防止飞太远
        },
        // 高亮交互
        emphasis: {
          focus: 'adjacency', // 只高亮相关联的
          lineStyle: { width: 4, color: '#3b82f6' }
        }
      }
    ]
  };
});
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5] flex flex-col overflow-hidden">
    <div v-if="store.selectedWxid" class="absolute top-3 left-3 z-10 bg-white/80 backdrop-blur p-2 rounded border border-slate-200 shadow-sm pointer-events-none">
      <div class="text-[10px] text-slate-400 uppercase tracking-wider">Analysis Target</div>
      <div class="text-sm font-bold text-slate-700">{{ store.selectedWxid }}</div>
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
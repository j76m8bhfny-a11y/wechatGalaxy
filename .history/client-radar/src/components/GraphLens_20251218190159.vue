<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { VNetworkGraph, defineConfigs } from "v-network-graph";

// 1. 引入数据仓库
const store = useMomentsStore();

// 2. 核心算法：将朋友圈互动数据 -> 转化为图谱 Nodes 和 Edges
const graphData = computed(() => {
  const centerId = store.selectedWxid;
  
  // 如果没选人，或者这个人没发过朋友圈，返回空
  if (!centerId) return { nodes: {}, edges: {} };

  const nodes: Record<string, { name: string, color: string, size: number, isCenter: boolean }> = {};
  const edges: Record<string, { source: string, target: string, width: number }> = {};

  // Step 1: 创建中心节点 (主角)
  nodes[centerId] = { 
    name: centerId, 
    color: '#2563eb', // 商务蓝
    size: 40,         // 主角最大
    isCenter: true
  };

  // Step 2: 统计互动频率
  const interactionMap = new Map<string, number>(); 
  
  store.currentMoments.forEach(m => {
    // 统计点赞
    m.interactions.likes.forEach(user => {
      const count = interactionMap.get(user.wxid) || 0;
      interactionMap.set(user.wxid, count + 1);
    });
    // 统计评论
    m.interactions.comments.forEach(user => {
      const count = interactionMap.get(user.wxid) || 0;
      interactionMap.set(user.wxid, count + 1);
    });
  });

  // Step 3: 生成卫星节点 (取前 20 名，防止太乱)
  const topInteractors = Array.from(interactionMap.entries())
    .filter(([wxid]) => wxid !== centerId) // 排除自己点赞自己
    .sort((a, b) => b[1] - a[1]) // 按互动次数降序
    .slice(0, 20);

  topInteractors.forEach(([wxid, count]) => {
    // 节点大小：基础 16 + 互动加成 (最大 30)
    const nodeSize = 16 + Math.min(count * 2, 14);
    
    nodes[wxid] = {
      name: wxid,
      color: '#94a3b8', // Slate-400 (高级灰)
      size: nodeSize,
      isCenter: false
    };

    // 连线
    const edgeId = `${centerId}-${wxid}`;
    edges[edgeId] = {
      source: centerId,
      target: wxid,
      width: Math.min(count, 6) // 线宽：最多 6px
    };
  });

  return { nodes, edges };
});

// 3. 视觉配置
const configs = defineConfigs({
  view: {
    layoutHandler: new VNetworkGraph.ForceLayout({
      positionFixedByDrag: false, // 允许拖拽节点
      positionFixedByClickWithAltKey: true,
      createSimulation: (d3, nodes, edges) => {
        const forceLink = d3.forceLink(edges).id((d: any) => d.id);
        return d3
          .forceSimulation(nodes)
          .force("edge", forceLink.distance(100)) // 连线长度
          .force("charge", d3.forceManyBody().strength(-300)) // 节点排斥力 (防止重叠)
          .force("center", d3.forceCenter());
      }
    }),
  },
  node: {
    selectable: true,
    normal: {
      type: "circle",
      radius: node => node.size / 2, // 使用数据里算好的大小
      color: node => node.color,
    },
    hover: {
      color: "#3b82f6", // 鼠标悬停变亮
    },
    label: {
      visible: true,
      text: node => node.name.length > 6 ? node.name.substring(0, 4) + '..' : node.name,
      fontSize: 11,
      color: "#475569",
      margin: 4,
    },
  },
  edge: {
    normal: {
      width: edge => edge.width, // 使用数据里算好的粗细
      color: "#e2e8f0", // 浅灰连线
    },
    hover: {
      color: "#3b82f6",
    }
  },
});
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5] flex flex-col overflow-hidden">
    
    <div v-if="!store.selectedWxid" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="text-center text-slate-400">
        <p class="text-lg font-medium">👈 请在左侧选择一位客户</p>
        <p class="text-xs mt-1 opacity-75">关系引擎待命中...</p>
      </div>
    </div>

    <div v-else-if="Object.keys(graphData.nodes).length <= 1" class="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
      <div class="text-center text-slate-400 bg-white/50 p-4 rounded-lg backdrop-blur-sm">
        <p class="font-bold text-slate-600">{{ store.selectedWxid }}</p>
        <p class="text-xs mt-1">这位朋友似乎很低调，暂无互动记录</p>
      </div>
    </div>

    <div v-if="Object.keys(graphData.nodes).length > 1" class="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur border border-slate-200 p-2 rounded shadow-sm text-xs text-slate-600 pointer-events-none select-none">
      <div class="font-bold text-blue-600 mb-1">关系透镜</div>
      <div>核心: {{ store.selectedWxid }}</div>
      <div>关联: {{ Object.keys(graphData.nodes).length - 1 }} 人</div>
    </div>

    <v-network-graph
      v-if="store.selectedWxid"
      class="graph-canvas"
      :nodes="graphData.nodes"
      :edges="graphData.edges"
      :configs="configs"
    />
  </div>
</template>

<style scoped>
/* 保持这个救命的样式不动！ */
.graph-canvas {
  width: 100%;
  height: 100%;
  /* 强制白色背景变透明，融入父容器的灰色背景 */
  background-color: transparent; 
}
</style>
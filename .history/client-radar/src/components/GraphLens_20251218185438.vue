<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { VNetworkGraph, defineConfigs } from "v-network-graph";

// ❌ 【关键修改】不要引入那个报错的 css 文件了，我们在下面手动写样式
// import "v-network-graph/style.css"; 

const store = useMomentsStore();

// === 1. 数据转换核心算法 ===
const graphData = computed(() => {
  const centerId = store.selectedWxid;
  // 调试点：如果没有选中人，返回空
  if (!centerId) return { nodes: {}, edges: {} };

  const nodes: Record<string, { name: string, color: string, size: number }> = {};
  const edges: Record<string, { source: string, target: string, width: number, label: string }> = {};

  // 1.1 添加中心节点
  nodes[centerId] = { 
    name: centerId, 
    color: '#2563eb', 
    size: 50 
  };

  // 1.2 遍历朋友圈
  const interactionMap = new Map<string, number>(); 
  
  store.currentMoments.forEach(m => {
    // 统计点赞
    if (m.interactions && m.interactions.likes) {
      m.interactions.likes.forEach(like => {
        const count = interactionMap.get(like.wxid) || 0;
        interactionMap.set(like.wxid, count + 1);
      });
    }
    // 统计评论
    if (m.interactions && m.interactions.comments) {
      m.interactions.comments.forEach(comment => {
        const count = interactionMap.get(comment.wxid) || 0;
        interactionMap.set(comment.wxid, count + 1);
      });
    }
  });

  // 1.3 生成卫星节点
  const topInteractors = Array.from(interactionMap.entries())
    .filter(([wxid]) => wxid !== centerId)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 30); // 只取前30个互动最频繁的

  topInteractors.forEach(([wxid, count]) => {
    nodes[wxid] = {
      name: wxid,
      color: '#94a3b8', 
      size: 20 + Math.min(count * 2, 20)
    };
    const edgeId = `${centerId}-${wxid}`;
    edges[edgeId] = {
      source: centerId,
      target: wxid,
      width: Math.min(count, 8),
      label: count.toString()
    };
  });
  
  return { nodes, edges };
});

const configs = defineConfigs({
  view: {
    layoutHandler: new VNetworkGraph.ForceLayout({
      positionFixedByDrag: false,
    }),
  },
  node: {
    selectable: true,
    normal: {
      type: "circle",
      radius: node => node.size / 2,
      color: node => node.color,
    },
    label: {
      visible: true,
      text: node => node.name.substring(0, 4),
      fontSize: 11,
    },
  },
  edge: {
    normal: {
      width: edge => edge.width,
      color: "#cbd5e1",
    },
  },
});
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5] flex flex-col">
    
    <div v-if="store.selectedWxid" class="absolute top-2 left-2 z-50 bg-black/70 text-white p-2 text-xs rounded pointer-events-none">
      <p>Debug: {{ store.selectedWxid }}</p>
      <p>Nodes: {{ Object.keys(graphData.nodes).length }}</p>
    </div>

    <v-network-graph
      class="graph-canvas"
      :nodes="graphData.nodes"
      :edges="graphData.edges"
      :configs="configs"
    />
  </div>
</template>

<style scoped>
/* 1. 容器样式 */
.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 400px;
  background-color: white;
  border: 1px solid #e2e8f0; /* 加上边框，方便看区域 */
}

/* 2. 强制覆盖 v-network-graph 内部样式 (解决白屏的关键) */
:deep(.v-network-graph) {
  width: 100%;
  height: 100%;
  position: relative;
}

:deep(svg) {
  width: 100%;
  height: 100%;
  display: block;
}
</style>
<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { VNetworkGraph, defineConfigs } from "v-network-graph";
// 尝试这里：如果 lib 也不行，试试 dist。如果都白屏，我们下面手动补 CSS。
import "v-network-graph/lib/style.css"; 

const store = useMomentsStore();

// === 1. 数据转换核心算法 ===
const graphData = computed(() => {
  const centerId = store.selectedWxid;
  // 调试点 1：如果没有选中人，返回空
  if (!centerId) return { nodes: {}, edges: {} };

  const nodes: Record<string, { name: string, color: string, size: number }> = {};
  const edges: Record<string, { source: string, target: string, width: number, label: string }> = {};

  // 1.1 添加中心节点（蓝色大球）
  nodes[centerId] = { 
    name: centerId, 
    color: '#2563eb', 
    size: 50 // 加大一点
  };

  // 1.2 遍历朋友圈
  const interactionMap = new Map<string, number>(); 
  
  // 调试点 2：确认是否有朋友圈数据
  console.log(`[GraphDebug] 当前选中: ${centerId}, 朋友圈数量: ${store.currentMoments.length}`);

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
    .slice(0, 30);

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

  console.log(`[GraphDebug] 生成节点: ${Object.keys(nodes).length}, 连线: ${Object.keys(edges).length}`);
  
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
      text: node => node.name.substring(0, 4), // 缩短名字防重叠
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
    
    <div class="absolute top-2 left-2 z-50 bg-black/70 text-white p-2 text-xs rounded pointer-events-none">
      <p>选中: {{ store.selectedWxid || '无' }}</p>
      <p>节点数: {{ Object.keys(graphData.nodes).length }}</p>
      <p>连线数: {{ Object.keys(graphData.edges).length }}</p>
      <p>朋友圈数: {{ store.currentMoments.length }}</p>
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
/* 强制给高度，防止高度坍塌 */
.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 400px; /* 最小高度保底 */
  border: 2px solid red; /* 调试用：看到红框说明组件加载了 */
  background-color: white;
}
</style>
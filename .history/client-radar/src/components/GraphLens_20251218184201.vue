<script setup lang="ts">
import { computed } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { VNetworkGraph, defineConfigs } from "v-network-graph";
import "v-network-graph/style.css";

const store = useMomentsStore();

// === 1. 数据转换核心算法 ===
// 将当前选中的人和他的互动数据，转化为图谱所需的 Nodes 和 Edges
const graphData = computed(() => {
  const centerId = store.selectedWxid;
  if (!centerId) return { nodes: {}, edges: {} };

  const nodes: Record<string, { name: string, color: string, size: number }> = {};
  const edges: Record<string, { source: string, target: string, width: number, label: string }> = {};

  // 1.1 添加中心节点（当前选中的主角）
  nodes[centerId] = { 
    name: centerId, // 暂时显示 wxid
    color: '#2563eb', // 蓝色
    size: 40 
  };

  // 1.2 遍历朋友圈，寻找卫星节点
  const interactionMap = new Map<string, number>(); // 记录互动次数

  store.currentMoments.forEach(m => {
    // 统计点赞
    m.interactions.likes.forEach(like => {
      const count = interactionMap.get(like.wxid) || 0;
      interactionMap.set(like.wxid, count + 1);
    });
    // 统计评论
    m.interactions.comments.forEach(comment => {
      const count = interactionMap.get(comment.wxid) || 0;
      interactionMap.set(comment.wxid, count + 1);
    });
  });

  // 1.3 生成卫星节点和连线
  // 过滤掉自己给自己的点赞，且只显示互动次数前 20 名（防止图太乱）
  const topInteractors = Array.from(interactionMap.entries())
    .filter(([wxid]) => wxid !== centerId)
    .sort((a, b) => b[1] - a[1]) // 按互动次数降序
    .slice(0, 20);

  topInteractors.forEach(([wxid, count]) => {
    // 添加节点
    nodes[wxid] = {
      name: wxid,
      color: '#94a3b8', // 灰色
      size: 20 + Math.min(count * 2, 20) // 互动越多，节点越大
    };

    // 添加连线
    const edgeId = `${centerId}-${wxid}`;
    edges[edgeId] = {
      source: centerId,
      target: wxid,
      width: Math.min(count, 8), // 互动越多，线越粗
      label: count.toString()
    };
  });

  return { nodes, edges };
});

// === 2. 图谱样式配置 ===
const configs = defineConfigs({
  view: {
    layoutHandler: new VNetworkGraph.ForceLayout({
      positionFixedByDrag: false,
      positionFixedByClickWithAltKey: true,
    }),
  },
  node: {
    selectable: true,
    normal: {
      type: "circle",
      radius: node => node.size / 2, // 根据数据里的 size 动态调整大小
      color: node => node.color,
    },
    label: {
      visible: true,
      text: node => node.name.length > 10 ? node.name.substring(0, 6) + '...' : node.name,
      fontSize: 11,
    },
  },
  edge: {
    normal: {
      width: edge => edge.width, // 根据互动次数动态调整粗细
      color: "#cbd5e1",
    },
    label: {
      fontSize: 10,
      color: "#94a3b8"
    }
  },
});

// 点击事件（预留给 Phase 4）
const eventHandlers = {
  "node:click": ({ node }) => {
    console.log("点击了节点:", node);
    // 这里未来会做：点击卫星节点，右侧只显示和他有关的朋友圈
  },
};
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5]">
    <div v-if="!store.selectedWxid" class="absolute inset-0 flex items-center justify-center text-slate-400 select-none pointer-events-none">
      <div class="text-center">
        <p class="text-lg">👈 请在左侧选择一位客户</p>
        <p class="text-xs mt-2">AI 关系引擎待命中...</p>
      </div>
    </div>

    <v-network-graph
      v-else
      class="w-full h-full"
      :nodes="graphData.nodes"
      :edges="graphData.edges"
      :configs="configs"
      :event-handlers="eventHandlers"
    />
  </div>
</template>

<style scoped>
/* 让画布占据 100% */
.v-network-graph {
  width: 100%;
  height: 100%;
}
</style>
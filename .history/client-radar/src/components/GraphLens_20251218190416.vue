<script setup lang="ts">
import { ref, computed, watchEffect } from 'vue';
import { useMomentsStore } from '../stores/moments';
import { VNetworkGraph, defineConfigs } from "v-network-graph";

const store = useMomentsStore();
const errorMsg = ref('');

// 2. 核心算法 (加装防弹玻璃版)
const graphData = computed(() => {
  try {
    const centerId = store.selectedWxid;
    if (!centerId) return { nodes: {}, edges: {} };

    // === 防护 1: 确保此时有朋友圈数据 ===
    if (!store.currentMoments || store.currentMoments.length === 0) {
      return { nodes: {}, edges: {} };
    }

    const nodes: Record<string, any> = {};
    const edges: Record<string, any> = {};

    // Step 1: 创建中心节点
    nodes[centerId] = { 
      name: centerId, 
      color: '#2563eb', 
      size: 40,
      isCenter: true
    };

    // Step 2: 统计互动频率 (极度防御模式)
    const interactionMap = new Map<string, number>(); 
    
    store.currentMoments.forEach((m, index) => {
      // === 防护 2: 某些数据可能没有 interactions 字段 ===
      if (!m || !m.interactions) return;

      // 安全读取点赞 (如果 likes 是 undefined，就用空数组 [])
      const likes = m.interactions.likes || [];
      likes.forEach(user => {
        if (!user || !user.wxid) return; // === 防护 3: 确保人名存在 ===
        const count = interactionMap.get(user.wxid) || 0;
        interactionMap.set(user.wxid, count + 1);
      });

      // 安全读取评论
      const comments = m.interactions.comments || [];
      comments.forEach(user => {
        if (!user || !user.wxid) return;
        const count = interactionMap.get(user.wxid) || 0;
        interactionMap.set(user.wxid, count + 1);
      });
    });

    // Step 3: 生成卫星节点
    const topInteractors = Array.from(interactionMap.entries())
      .filter(([wxid]) => wxid !== centerId)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 20);

    topInteractors.forEach(([wxid, count]) => {
      const nodeSize = 16 + Math.min(count * 2, 14);
      nodes[wxid] = {
        name: wxid,
        color: '#94a3b8', 
        size: nodeSize,
        isCenter: false
      };
      const edgeId = `${centerId}-${wxid}`;
      edges[edgeId] = {
        source: centerId,
        target: wxid,
        width: Math.min(count, 6)
      };
    });

    return { nodes, edges };

  } catch (err: any) {
    console.error("图谱计算崩溃:", err);
    errorMsg.value = err.message;
    return { nodes: {}, edges: {} };
  }
});

// 3. 视觉配置
const configs = defineConfigs({
  view: {
    layoutHandler: new VNetworkGraph.ForceLayout({
      positionFixedByDrag: false,
      createSimulation: (d3, nodes, edges) => {
        const forceLink = d3.forceLink(edges).id((d: any) => d.id);
        return d3
          .forceSimulation(nodes)
          .force("edge", forceLink.distance(100))
          .force("charge", d3.forceManyBody().strength(-300))
          .force("center", d3.forceCenter());
      }
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
      text: node => node.name.length > 6 ? node.name.substring(0, 4) + '..' : node.name,
      fontSize: 11,
      color: "#475569",
    },
  },
  edge: {
    normal: {
      width: edge => edge.width,
      color: "#e2e8f0",
    },
  },
});
</script>

<template>
  <div class="w-full h-full relative bg-[#F0F2F5] flex flex-col">
    
    <div v-if="errorMsg" class="absolute top-0 left-0 right-0 bg-red-100 text-red-600 p-2 text-xs z-50">
      图谱引擎错误: {{ errorMsg }}
    </div>

    <div v-if="!store.selectedWxid" class="absolute inset-0 flex items-center justify-center pointer-events-none">
      <div class="text-center text-slate-400">
        <p class="text-lg font-medium">👈 请在左侧选择一位客户</p>
      </div>
    </div>

    <v-network-graph
      v-if="store.selectedWxid && !errorMsg"
      class="graph-canvas"
      :nodes="graphData.nodes"
      :edges="graphData.edges"
      :configs="configs"
    />

    <div v-if="store.selectedWxid" class="absolute bottom-2 right-2 text-[10px] text-slate-300 pointer-events-none">
       Nodes: {{ Object.keys(graphData.nodes).length }}
    </div>
  </div>
</template>

<style scoped>
/* 强制给高度，防止高度坍塌 */
.graph-canvas {
  width: 100%;
  height: 100%;
  background-color: transparent; 
}
</style>
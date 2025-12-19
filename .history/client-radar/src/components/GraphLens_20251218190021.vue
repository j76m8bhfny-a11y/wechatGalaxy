<script setup lang="ts">
import { ref } from 'vue';
import { VNetworkGraph } from "v-network-graph";

// 1. 模拟最简单的数据
const nodes = ref({
  node1: { name: "张总", color: "#2563eb" }, // 蓝色
  node2: { name: "王秘", color: "#94a3b8" }, // 灰色
  node3: { name: "李总", color: "#94a3b8" }, // 灰色
});

const edges = ref({
  edge1: { source: "node1", target: "node2" },
  edge2: { source: "node1", target: "node3" },
});

// 2. 最基础的配置 (让它能动就行)
const configs = ref({
  node: {
    normal: {
      radius: 16,
      color: (node: any) => node.color,
    },
    label: { visible: true },
  },
});
</script>

<template>
  <div class="w-full h-full bg-white relative flex flex-col">
    <div class="p-2 bg-slate-100 text-xs text-slate-500 border-b border-slate-200">
      图谱引擎测试模式
    </div>

    <div class="flex-1 relative border border-blue-100 m-4 rounded bg-slate-50">
      <v-network-graph
        class="graph-canvas"
        :nodes="nodes"
        :edges="edges"
        :configs="configs"
      />
    </div>
  </div>
</template>

<style scoped>
/* 🔑 关键：手动给高度，防止白屏 */
.graph-canvas {
  width: 100%;
  height: 100%;
  min-height: 400px; /* 保底高度 */
}
</style>
<script setup lang="ts">
import { computed, ref } from 'vue';
import { useMomentsStore, type Moment } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';
import { use } from 'echarts/core';
import { CanvasRenderer } from 'echarts/renderers';
import { GraphChart } from 'echarts/charts';
import { TitleComponent, TooltipComponent, LegendComponent } from 'echarts/components';
import VChart from 'vue-echarts';

// 注册 ECharts 组件
use([CanvasRenderer, GraphChart, TitleComponent, TooltipComponent, LegendComponent]);

const store = useMomentsStore();
const contactStore = useContactsStore();

// --- 核心算法 ---
const chartOption = computed(() => {
  const centerId = store.selectedWxid;
  
  // 空状态处理
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

  // 1. 构建图谱 (Global Graph Construction)
  const globalGraph = new Map<string, Set<string>>();
  const edgeWeights = new Map<string, number>(); // 记录互动次数作为权重
  
  // 辅助函数：添加边 (无向图)
  const addEdge = (u: string, v: string) => {
    if (!u || !v || u === v) return; // 排除无效ID和自己跟自己互动
    
    if (!globalGraph.has(u)) globalGraph.set(u, new Set());
    if (!globalGraph.has(v)) globalGraph.set(v, new Set());
    
    globalGraph.get(u)!.add(v);
    globalGraph.get(v)!.add(u);

    // 记录权重 (u-v 和 v-u 是同一条边)
    const key = u < v ? `${u}-${v}` : `${v}-${u}`;
    edgeWeights.set(key, (edgeWeights.get(key) || 0) + 1);
  };

  // 2. 遍历朋友圈，挖掘关系
  const moments = store.moments || [];
  moments.forEach((m: Moment) => {
    const author = m.author_wxid;
    
    // A. 处理点赞：点赞者 <-> 发帖人
    if (m.interactions?.likes) {
      m.interactions.likes.forEach(user => { 
        addEdge(author, user.wxid); 
      });
    }

    // B. 处理评论：评论者 <-> 发帖人
    if (m.interactions?.comments) {
      m.interactions.comments.forEach(comment => { 
        addEdge(author, comment.wxid); 

        // 🔥🔥🔥 关键逻辑升级：回复关系挖掘 (Friend of Friend) 🔥🔥🔥
        // 如果这条评论是回复别人的 (reply_to_wxid 存在)
        // 那么建立：评论者 <-> 被回复者 的直接连线
        // 这就是实现 A-B-D 链条的关键！
        if (comment.reply_to_wxid) {
          addEdge(comment.wxid, comment.reply_to_wxid);
        }
      });
    }
  });

  // 3. BFS 广度优先搜索 (控制显示层级，防止图太大爆炸)
  const MAX_LEVEL = 3; // 最多显示 3 层关系 (你-朋友-朋友的朋友)
  const MAX_NODES = 100; // 限制最大节点数，保证性能
  
  const visited = new Map<string, number>(); // 记录节点层级
  const queue: { id: string, level: number }[] = [];
  const validNodeIds = new Set<string>(); // 最终要显示的节点集合

  // 从选中人开始
  queue.push({ id: centerId, level: 0 });
  visited.set(centerId, 0);

  while (queue.length > 0) {
    const { id, level } = queue.shift()!;
    
    if (validNodeIds.size >= MAX_NODES) break; // 超过数量停止
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

  // 4. 生成 ECharts 数据格式
  const resultNodes: any[] = [];
  const resultLinks: any[] = [];

  validNodeIds.forEach(id => {
    const level = visited.get(id)!;
    const isCenter = level === 0;
    
    // 节点大小随层级递减
    let size = 10;
    if (level === 0) size = 50;      
    else if (level === 1) size = 30; 
    else if (level === 2) size = 15; 
    
    // 获取显示名称 (快照名逻辑可以后续加上，这里先查通讯录)
    let displayName = contactStore.getDisplayName(id);
    if (!displayName || displayName === '未知用户') displayName = id;

    resultNodes.push({
      id: id,
      name: displayName, 
      originalId: id,
      symbolSize: size,
      value: `层级: ${level}`, // 鼠标悬停显示
      category: level, // 用于 Legend 分类
      // 只有核心和一级好友显示名字，防止太乱
      label: { 
        show: level <= 1, 
        position: 'right',
        formatter: '{b}' 
      },
      itemStyle: {
        // 选中人高亮逻辑 (暂留接口)
        borderColor: '#fff',
        borderWidth: 1
      }
    });
  });

  // 5. 生成连线
  const linkSet = new Set<string>();
  
  // 只生成 validNodeIds 内部的连线
  validNodeIds.forEach(source => {
    const neighbors = globalGraph.get(source);
    if (neighbors) {
      neighbors.forEach(target => {
        // 确保连线的另一端也在我们筛选出的图里
        if (validNodeIds.has(target)) {
          // 避免重复添加 (A-B 和 B-A)
          const key = source < target ? `${source}-${target}` : `${target}-${source}`;
          
          if (!linkSet.has(key)) {
            linkSet.add(key);
            const weight = edgeWeights.get(key) || 1;
            
            // 连线样式：互动越频繁，线越粗
            const lineWidth = Math.min(1 + Math.log(weight), 4);
            
            resultLinks.push({
              source, 
              target,
              lineStyle: { 
                width: lineWidth, 
                curveness: 0.2, // 一点点弯曲度更好看
                color: '#cbd5e1' 
              }
            });
          }
        }
      });
    }
  });

  return {
    // 配色方案：蓝 -> 青 -> 灰 -> 浅灰
    color: ['#3b82f6', '#0ea5e9', '#94a3b8', '#cbd5e1'],
    tooltip: { 
      trigger: 'item',
      formatter: '{b} <br/> {c}' // 显示名字和层级
    },
    legend: { 
      show: true, 
      bottom: 10, 
      data: [{name: '核心人物'}, {name: '一级密友'}, {name: '二级人脉'}, {name: '边缘关联'}],
      // 映射 category index 到 legend name
      formatter: (name: string) => name 
    },
    series: [
      {
        type: 'graph',
        layout: 'force',
        data: resultNodes,
        links: resultLinks,
        categories: [
          { name: '核心人物' }, // category 0
          { name: '一级密友' }, // category 1
          { name: '二级人脉' }, // category 2
          { name: '边缘关联' }  // category 3+
        ],
        roam: true, // 允许拖拽画布
        draggable: true, // 允许拖拽节点
        force: {
          repulsion: 200,   // 斥力：节点之间的排斥力
          gravity: 0.1,     // 引力：向中心的拉力
          edgeLength: [50, 150], // 连线长度范围
          layoutAnimation: true
        },
        emphasis: {
          focus: 'adjacency', // 鼠标悬停高亮相邻节点
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

    <v-chart 
      class="chart-canvas" 
      :option="chartOption" 
      autoresize 
    />
  </div>
</template>

<style scoped>
.chart-canvas {
  width: 100%;
  height: 100%;
}
</style>
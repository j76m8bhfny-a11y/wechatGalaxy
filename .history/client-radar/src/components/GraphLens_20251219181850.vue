<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue';
import * as d3 from 'd3';
import { useMomentsStore } from '../stores/moments';
import { useContactsStore } from '../stores/contacts';

const store = useMomentsStore();
const contactStore = useContactsStore();
const svgRef = ref<SVGSVGElement | null>(null);
const containerRef = ref<HTMLDivElement | null>(null);

// 核心数据转换：将 Store 里的 contacts (发帖+互动) 转换为 D3 节点
const graphData = computed(() => {
  const nodes: any[] = [];
  const links: any[] = [];
  const nodeMap = new Map();

  // 1. 生成节点 (利用我们在 Store 里聚合好的全量名单)
  store.contacts.forEach(c => {
    // 过滤：如果是纯路人且互动极少，可以过滤掉，避免图太乱
    // 这里为了让你看到效果，全部展示
    const node = {
      id: c.id,
      name: c.name || c.id,
      group: c.isInteractionOnly ? 2 : 1, // 1=核心发帖者, 2=围观群众
      val: c.momentCount * 5 + c.interactionCount // 节点大小
    };
    nodes.push(node);
    nodeMap.set(c.id, node);
  });

  // 2. 生成连线 (基于朋友圈的互动关系)
  store.moments.forEach(m => {
    const authorId = m.author_wxid;
    if (!nodeMap.has(authorId)) return;

    // A. 建立 点赞人 -> 发帖人 的连线
    m.interactions.likes.forEach(like => {
      if (nodeMap.has(like.wxid) && like.wxid !== authorId) {
        links.push({
          source: like.wxid,
          target: authorId,
          type: 'like'
        });
      }
    });

    // B. 建立 评论人 -> 发帖人 的连线
    m.interactions.comments.forEach(cmt => {
      if (nodeMap.has(cmt.wxid) && cmt.wxid !== authorId) {
        links.push({
          source: cmt.wxid,
          target: authorId,
          type: 'comment'
        });
      }
      
      // C. 建立 回复人 -> 被回复人 的连线 (更深层关系)
      if (cmt.reply_to_wxid && nodeMap.has(cmt.reply_to_wxid) && cmt.reply_to_wxid !== cmt.wxid) {
         links.push({
          source: cmt.wxid,
          target: cmt.reply_to_wxid,
          type: 'reply'
        });
      }
    });
  });

  return { nodes, links };
});

// D3 渲染逻辑
const renderGraph = () => {
  if (!svgRef.value || !containerRef.value) return;
  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  // 清空画布
  const svg = d3.select(svgRef.value);
  svg.selectAll("*").remove();

  const { nodes, links } = graphData.value;
  if (nodes.length === 0) return;

  // 模拟力导向图
  const simulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links).id((d: any) => d.id).distance(100))
    .force("charge", d3.forceManyBody().strength(-200))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(30));

  // 绘制连线
  const link = svg.append("g")
    .attr("stroke", "#999")
    .attr("stroke-opacity", 0.6)
    .selectAll("line")
    .data(links)
    .join("line")
    .attr("stroke-width", (d: any) => d.type === 'like' ? 1 : 2) // 评论线粗一点
    .attr("stroke", (d: any) => d.type === 'reply' ? '#f59e0b' : '#cbd5e1'); // 回复线用橙色

  // 绘制节点
  const node = svg.append("g")
    .selectAll("g")
    .data(nodes)
    .join("g")
    .call(drag(simulation));

  // 节点圆圈
  node.append("circle")
    .attr("r", (d: any) => Math.sqrt(d.val) + 5)
    .attr("fill", (d: any) => d.group === 1 ? "#3b82f6" : "#10b981") // 蓝=发帖人，绿=互动者
    .attr("stroke", "#fff")
    .attr("stroke-width", 1.5);

  // 节点文字 (只显示比较重要的节点，防止太乱)
  node.append("text")
    .text((d: any) => d.name)
    .attr("x", 8)
    .attr("y", 3)
    .style("font-size", "10px")
    .style("fill", "#334155")
    .style("pointer-events", "none");
    
  // 提示框 Title
  node.append("title")
    .text((d: any) => `${d.name}\nID: ${d.id}`);

  // 动画更新
  simulation.on("tick", () => {
    link
      .attr("x1", (d: any) => d.source.x)
      .attr("y1", (d: any) => d.source.y)
      .attr("x2", (d: any) => d.target.x)
      .attr("y2", (d: any) => d.target.y);

    node
      .attr("transform", (d: any) => `translate(${d.x},${d.y})`);
  });
};

// 拖拽行为
const drag = (simulation: any) => {
  const dragstarted = (event: any, d: any) => {
    if (!event.active) simulation.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  };
  const dragged = (event: any, d: any) => {
    d.fx = event.x;
    d.fy = event.y;
  };
  const dragended = (event: any, d: any) => {
    if (!event.active) simulation.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  };
  return d3.drag()
    .on("start", dragstarted)
    .on("drag", dragged)
    .on("end", dragended);
};

// 监听数据变化重新渲染
watch(() => store.moments, () => {
  renderGraph();
}, { deep: true });

onMounted(() => {
  renderGraph();
  window.addEventListener('resize', renderGraph);
});
</script>

<template>
  <div class="w-full h-full bg-slate-50 relative flex flex-col" ref="containerRef">
    <div class="absolute top-4 left-4 z-10 bg-white/90 backdrop-blur px-3 py-2 rounded-lg shadow-sm border border-slate-200">
      <h3 class="text-sm font-bold text-slate-800">关系星图</h3>
      <div class="flex items-center space-x-3 mt-1 text-xs text-slate-500">
        <div class="flex items-center"><span class="w-2 h-2 rounded-full bg-blue-500 mr-1"></span>发帖者</div>
        <div class="flex items-center"><span class="w-2 h-2 rounded-full bg-emerald-500 mr-1"></span>互动者</div>
      </div>
    </div>

    <svg ref="svgRef" class="w-full h-full cursor-grab active:cursor-grabbing"></svg>
    
    <div v-if="store.moments.length === 0" class="absolute inset-0 flex items-center justify-center text-slate-400">
      <p>暂无数据，请先扫描</p>
    </div>
  </div>
</template>
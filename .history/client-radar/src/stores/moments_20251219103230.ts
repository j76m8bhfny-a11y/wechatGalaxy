import { defineStore } from 'pinia';
import { ref, computed, shallowRef } from 'vue';
import rawData from '../assets/moments_full.json';

// --- 类型定义 ---
export interface Interaction {
  wxid: string;
  time?: string;
  content?: string;
}

export interface Moment {
  id: string;
  author_wxid: string;
  timestamp: number;
  date: string;
  content: {
    text: string;
    media: any[];
  };
  interactions: {
    likes: Interaction[];
    comments: Interaction[];
  };
}

export interface Contact {
  id: string;
  name: string;
  avatar: string;
  momentCount: number;
  latestDate: string;
}

// --- Store ---
export const useMomentsStore = defineStore('moments', () => {
  const moments = shallowRef<Moment[]>(rawData as any as Moment[]);
  
  // 1. 当前选中的核心人物 (Author)
  const selectedWxid = ref<string>('');

  // 2. 🆕 新增：当前选中的互动者 (用于筛选右侧内容)
  // 如果为空，显示所有朋友圈；如果不为空，只显示和他有关的
  const filterWxid = ref<string>('');

  // 3. 计算联系人列表 (侧边栏用)
  const contacts = computed(() => {
    const map = new Map<string, Contact>();
    moments.value.forEach((m) => {
      const wxid = m.author_wxid;
      if (!map.has(wxid)) {
        map.set(wxid, {
          id: wxid,
          name: wxid,
          avatar: wxid.substring(0, 1).toUpperCase(),
          momentCount: 0,
          latestDate: m.date
        });
      }
      const contact = map.get(wxid)!;
      contact.momentCount++;
      if (m.date > contact.latestDate) contact.latestDate = m.date;
    });
    return Array.from(map.values()).sort((a, b) => b.latestDate.localeCompare(a.latestDate));
  });

  // 4. 获取当前核心人物的所有朋友圈
  const currentMoments = computed(() => {
    if (!selectedWxid.value) return [];
    return moments.value.filter((m) => m.author_wxid === selectedWxid.value);
  });

  // 5. 🆕 新增：过滤后的展示列表 (Feed 用)
  const filteredMoments = computed(() => {
    // 如果没有核心人物，返回空
    if (!selectedWxid.value) return [];
    
    // 基础列表：核心人物的所有朋友圈
    const baseList = currentMoments.value;

    // 如果没有设置筛选人，直接返回全部
    if (!filterWxid.value) return baseList;

    // 核心逻辑：只保留 filterWxid 参与互动的条目
    const targetId = filterWxid.value;
    return baseList.filter(m => {
      const hasLike = m.interactions?.likes?.some(u => u.wxid === targetId);
      const hasComment = m.interactions?.comments?.some(u => u.wxid === targetId);
      return hasLike || hasComment;
    });
  });

  return {
    moments,
    contacts,
    selectedWxid,
    filterWxid,      // 导出给组件用
    currentMoments,
    filteredMoments  // 导出给 Feed 用
  };
});
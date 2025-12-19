import { defineStore } from 'pinia';
export const useMomentsStore = defineStore('moments', () => {
import { ref, computed } from 'vue';
// 直接导入 JSON 数据（Vite 会自动解析）
import rawData from '../assets/moments_full.json';

// 定义数据类型接口
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
  name: string; // 暂时存 wxid，后续做映射
  avatar: string; // 暂时用首字母
  momentCount: number;
  latestDate: string;
}

export const useMomentsStore = defineStore('moments', () => {
  // 1. 原始数据
  //const moments = ref<Moment[]>(rawData as Moment[]);
  const moments = shallowRef(rawData);

  // 2. 当前选中的联系人 ID
  const selectedWxid = ref<string>('');

  // 3. 【核心算法】从朋友圈列表反推“联系人列表”
  // 因为 JSON 是按朋友圈存的，我们需要聚合出“发过朋友圈的人”
  const contacts = computed(() => {
    const map = new Map<string, Contact>();

    moments.value.forEach(m => {
      const wxid = m.author_wxid;
      
      if (!map.has(wxid)) {
        map.set(wxid, {
          id: wxid,
          name: wxid, // ⚠️ Phase 1.5 还没做昵称映射，先显示 wxid
          avatar: wxid.substring(0, 1).toUpperCase(),
          momentCount: 0,
          latestDate: m.date
        });
      }
      
      const contact = map.get(wxid)!;
      contact.momentCount++;
      // 更新最近时间
      if (m.date > contact.latestDate) {
        contact.latestDate = m.date;
      }
    });

    // 转为数组并按“最近更新时间”排序
    return Array.from(map.values()).sort((a, b) => 
      b.latestDate.localeCompare(a.latestDate)
    );
  });

  // 4. 获取当前选中人的朋友圈
  const currentMoments = computed(() => {
    if (!selectedWxid.value) return [];
    return moments.value.filter(m => m.author_wxid === selectedWxid.value);
  });

  return {
    moments,
    contacts,
    selectedWxid,
    currentMoments
  };
});
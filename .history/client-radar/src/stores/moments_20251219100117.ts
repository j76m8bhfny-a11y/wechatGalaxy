import { defineStore } from 'pinia';
import { ref, computed, shallowRef } from 'vue'; // ✅ 修复：引入 shallowRef
import rawData from '../assets/moments_full.json';

// --- 类型定义区域 ---
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

// --- Store 定义区域 ---
export const useMomentsStore = defineStore('moments', () => {
  // ✅ 修复：使用 shallowRef 并强制指定类型 <Moment[]>
  // (rawData as any) 是为了防止 TS 抱怨 json 格式不匹配
  const moments = shallowRef<Moment[]>(rawData as any as Moment[]);
  
  // 2. 当前选中的联系人 ID
  const selectedWxid = ref<string>('');

  // 3. 计算联系人列表
  const contacts = computed(() => {
    const map = new Map<string, Contact>();

    // ✅ 修复：因为 moments 有了类型，这里的 m 自动会被识别为 Moment
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
      if (m.date > contact.latestDate) {
        contact.latestDate = m.date;
      }
    });

    return Array.from(map.values()).sort((a, b) => 
      b.latestDate.localeCompare(a.latestDate)
    );
  });

  // 4. 获取当前选中人的朋友圈
  const currentMoments = computed(() => {
    if (!selectedWxid.value) return [];
    return moments.value.filter((m) => m.author_wxid === selectedWxid.value);
  });

  // ✅ 修复：一定要把这些状态 return 出去，否则外部组件读不到
  return {
    moments,
    contacts,
    selectedWxid,
    currentMoments
  };
}); // ✅ 修复：闭合的大括号和圆括号
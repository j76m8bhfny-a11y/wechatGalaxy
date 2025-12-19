import { defineStore } from 'pinia';
import { ref, computed } from 'vue';

// ==========================================
// 1. 新版类型定义 (匹配 Python 返回的结构)
// ==========================================

export interface Interaction {
  wxid: string;
  name?: string; // 🆕 新增这个字段：Python 返回的快照昵称
  time?: number;
  content?: string; // 评论内容
  reply_to?: string;
}

export interface MediaItem {
  type: 'image' | 'video';
  src: string;
  thumb?: string;
}

export interface MomentContent {
  text: string;
  media: MediaItem[];
}

export interface MomentStats {
  likes_count: number;
  comments_count: number;
}

export interface MomentInteractions {
  likes: Interaction[];
  comments: Interaction[];
}

export interface Moment {
  id: string;
  timestamp: number;
  date: string;
  author_wxid: string; // 🆕 以前是 wxid, 现在 Python 返回 author_wxid
  
  // 🆕 结构化内容
  content: MomentContent;
  stats: MomentStats;
  interactions: MomentInteractions;
  
  // 兼容字段 (UI 还需要用到的)
  avatar: string; 
  name: string;   
}

// 左侧列表用的摘要
export interface ContactSummary {
  id: string;
  avatar: string;
  momentCount: number;
  latestDate: string;
}

export const useMomentsStore = defineStore('moments', () => {
  // State
  const moments = ref<Moment[]>([]);
  const selectedWxid = ref<string>('');
  const filterWxid = ref<string>('');

  // 🚀 核心：直接加载 Python 解析好的数据
  const loadFeeds = (rawFeeds: any[]) => {
    console.log(`📦 正在加载 ${rawFeeds.length} 条朋友圈数据...`);
    
    moments.value = rawFeeds.map(feed => {
      // 映射 Python 字段 -> 前端字段
      return {
        id: feed.id,
        timestamp: feed.timestamp,
        date: feed.date || new Date(feed.timestamp * 1000).toLocaleString(),
        author_wxid: feed.author_wxid,
        
        content: feed.content || { text: '', media: [] },
        stats: feed.stats || { likes_count: 0, comments_count: 0 },
        interactions: feed.interactions || { likes: [], comments: [] },
        
        // UI 辅助字段
        avatar: '👤', 
        name: '加载中...', 
      };
    });
    
    console.log("✅ 数据加载完成！");
  };

  // Getters
  const filteredMoments = computed(() => {
    let list = moments.value;
    if (selectedWxid.value) {
      list = list.filter(m => m.author_wxid === selectedWxid.value);
    }
    return list;
  });

  const contacts = computed(() => {
    const map = new Map<string, ContactSummary>();
    moments.value.forEach(m => {
      const uid = m.author_wxid;
      if (!uid) return;
      
      if (!map.has(uid)) {
        map.set(uid, {
          id: uid,
          avatar: m.avatar,
          momentCount: 0,
          latestDate: m.date
        });
      }
      const c = map.get(uid)!;
      c.momentCount++;
      // 简单字符串日期比较可能不准，最好用 timestamp，这里先维持现状
      if (m.timestamp > (new Date(c.latestDate).getTime() / 1000)) {
         c.latestDate = m.date;
      }
    });
    
    // 按活跃时间排序
    return Array.from(map.values()).sort((a, b) => {
      // 如果 date 解析失败可能会 NaN，简单处理
      return (new Date(b.latestDate).getTime() || 0) - (new Date(a.latestDate).getTime() || 0);
    });
  });

  return {
    moments,
    selectedWxid,
    filterWxid,
    loadFeeds, // 👈 以前是 importFromDb，现在改用这个
    filteredMoments,
    contacts
  };
});
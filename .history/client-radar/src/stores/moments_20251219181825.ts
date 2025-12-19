import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useContactsStore } from './contacts'; // 引入通讯录 Store 以便兜底查询

// ==========================================
// 类型定义
// ==========================================

export interface Interaction {
  wxid: string;
  name?: string;          // 快照名字
  time?: number;
  content?: string;
  reply_to_wxid?: string;
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
  author_wxid: string;
  content: MomentContent;
  stats: MomentStats;
  interactions: MomentInteractions;
  avatar: string; 
  name: string;   
}

// 侧边栏/星图用的摘要对象
export interface ContactSummary {
  id: string;
  avatar: string;
  name: string;        // 🆕 新增名字字段，方便星图使用
  momentCount: number; // 发帖数
  interactionCount: number; // 🆕 新增互动数 (点赞+评论)
  latestDate: string;
  isInteractionOnly: boolean; // 🆕 标记是否仅出现在互动中
}

export const useMomentsStore = defineStore('moments', () => {
  const moments = ref<Moment[]>([]);
  const selectedWxid = ref<string>('');
  const filterWxid = ref<string>('');
  
  // 引用外部通讯录 Store，用于名字兜底
  const contactStore = useContactsStore();

  // 🚀 加载数据
  const loadFeeds = (rawFeeds: any[]) => {
    console.log(`📦 加载 ${rawFeeds.length} 条朋友圈...`);
    moments.value = rawFeeds.map(feed => ({
      id: feed.id,
      timestamp: feed.timestamp,
      date: feed.date || new Date(feed.timestamp * 1000).toLocaleString(),
      author_wxid: feed.author_wxid,
      content: feed.content || { text: '', media: [] },
      stats: feed.stats || { likes_count: 0, comments_count: 0 },
      interactions: feed.interactions || { likes: [], comments: [] },
      avatar: '👤', 
      name: '加载中...', 
    }));
  };

  // 🔍 筛选逻辑
  const filteredMoments = computed(() => {
    let list = moments.value;
    if (selectedWxid.value) {
      // 这里的逻辑是：如果选中某人，显示 他发的朋友圈 + 他参与互动的(可选)
      // 目前保持只显示他发的
      list = list.filter(m => m.author_wxid === selectedWxid.value);
    }
    return list;
  });

  // 🌟 核心升级：全量关系提取器
  // 这个 computed 会生成包含“发帖人 + 点赞人 + 评论人”的完整名单
  const contacts = computed(() => {
    const map = new Map<string, ContactSummary>();

    // 辅助函数：处理用户出现
    const handleUser = (wxid: string, dateStr: string, isAuthor: boolean, snapshotName?: string) => {
      if (!wxid) return;

      if (!map.has(wxid)) {
        // 尝试获取名字：快照名字 > 通讯录备注 > 昵称 > WXID
        let realName = snapshotName || '';
        if (!realName) {
           realName = contactStore.getDisplayName(wxid); 
        }
        if (realName === '未知用户' || !realName) {
           realName = wxid; // 实在没人名，就显示 ID，总比空白好
        }

        map.set(wxid, {
          id: wxid,
          avatar: '👤', // 后续可根据 wxid 匹配头像
          name: realName, 
          momentCount: 0,
          interactionCount: 0,
          latestDate: dateStr,
          isInteractionOnly: !isAuthor 
        });
      }

      const c = map.get(wxid)!;
      
      // 更新计数
      if (isAuthor) c.momentCount++;
      else c.interactionCount++;

      // 更新最近时间
      // 简单字符串比较，实际项目可用 timestamp
      if (dateStr > c.latestDate) {
         c.latestDate = dateStr;
      }
      
      // 如果之前认为是仅互动，现在发现他发帖了，更新状态
      if (isAuthor) c.isInteractionOnly = false;
      
      // 如果之前没名字，现在有快照名字了，补上
      if ((c.name === wxid || c.name === '未知用户') && snapshotName) {
        c.name = snapshotName;
      }
    };

    // 1. 遍历每一条朋友圈
    moments.value.forEach(m => {
      // A. 处理发帖人
      handleUser(m.author_wxid, m.date, true);

      // B. 处理点赞人
      m.interactions.likes.forEach(like => {
        handleUser(like.wxid, m.date, false, like.name);
      });

      // C. 处理评论人
      m.interactions.comments.forEach(cmt => {
        handleUser(cmt.wxid, m.date, false, cmt.name);
        // D. 处理被回复的人 (A 回复 B, B 也算参与了)
        if (cmt.reply_to_wxid) {
          handleUser(cmt.reply_to_wxid, m.date, false);
        }
      });
    });

    // 排序：优先显示发帖多的，其次互动多的
    return Array.from(map.values()).sort((a, b) => {
      const scoreA = a.momentCount * 10 + a.interactionCount;
      const scoreB = b.momentCount * 10 + b.interactionCount;
      return scoreB - scoreA;
    });
  });

  return {
    moments,
    selectedWxid,
    filterWxid,
    loadFeeds,
    filteredMoments,
    contacts // 现在这里包含了所有人！
  };
});
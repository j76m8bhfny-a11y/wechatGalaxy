import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { useContactsStore } from './contacts';

export interface Interaction {
  wxid: string;
  name?: string;
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

export interface ContactSummary {
  id: string;
  avatar: string;
  name: string;
  momentCount: number;
  latestDate: string;
}

export const useMomentsStore = defineStore('moments', () => {
  const moments = ref<Moment[]>([]);
  const selectedWxid = ref<string>('');
  const filterWxid = ref<string>('');
  
  const contactStore = useContactsStore();
  
  // 💾 内部缓存：记录所有出现过的 wxid -> name 映射
  // 来源包括：通讯录、朋友圈作者、点赞列表快照、评论列表快照
  const globalUserMap = ref<Map<string, string>>(new Map());

  // 📥 加载数据并构建“全员户口本”
  const loadFeeds = (rawFeeds: any[]) => {
    console.log(`📦 加载 ${rawFeeds.length} 条数据，正在构建全员索引...`);
    const map = new Map<string, string>();

    rawFeeds.forEach(feed => {
      // 1. 记录发帖人 (如果有快照名虽少见，但也记录)
      if (feed.author_wxid) {
        // 这里的名字稍后由 ContactStore 补全，先占位
        if (!map.has(feed.author_wxid)) map.set(feed.author_wxid, '');
      }

      // 2. 记录点赞人 (利用 Python 传回来的 name)
      if (feed.interactions?.likes) {
        feed.interactions.likes.forEach((u: any) => {
          if (u.wxid && u.name) map.set(u.wxid, u.name);
        });
      }

      // 3. 记录评论人
      if (feed.interactions?.comments) {
        feed.interactions.comments.forEach((c: any) => {
          if (c.wxid && c.name) map.set(c.wxid, c.name);
        });
      }
    });
    
    globalUserMap.value = map;

    // 转换数据结构
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

  // 🔍 超级查名器 (核心功能)
  // 任何组件想知道某个 wxid 叫什么，都调这个，别自己瞎查
  const getSmartName = (wxid: string) => {
    if (!wxid) return '未知';
    
    // 1. 优先查通讯录 (备注名最准)
    const contactName = contactStore.getDisplayName(wxid);
    if (contactName && contactName !== '未知用户' && contactName !== wxid) {
      return contactName;
    }

    // 2. 查全员快照 (朋友圈里留下的历史名字)
    const snapshotName = globalUserMap.value.get(wxid);
    if (snapshotName && snapshotName.length > 0) {
      return snapshotName;
    }

    // 3. 实在没有，返回 wxid
    return wxid;
  };

  // 左侧列表：只显示发过朋友圈的人 (保持界面整洁)
  // 如果你想让点赞的人也出现在左侧，可以改这里，但通常没必要
  const contacts = computed(() => {
    const map = new Map<string, ContactSummary>();
    moments.value.forEach(m => {
      const uid = m.author_wxid;
      if (!uid) return;
      
      if (!map.has(uid)) {
        map.set(uid, {
          id: uid,
          avatar: '👤',
          name: getSmartName(uid), // 使用超级查名
          momentCount: 0,
          latestDate: m.date
        });
      }
      const c = map.get(uid)!;
      c.momentCount++;
      if (m.date > c.latestDate) c.latestDate = m.date;
    });
    
    return Array.from(map.values()).sort((a, b) => b.momentCount - a.momentCount);
  });

  const filteredMoments = computed(() => {
    // 🔥 模式一：雷达追踪模式 (点击了图谱中的节点，例如 C)
    if (filterWxid.value) {
      const targetId = filterWxid.value; 

      return moments.value.filter(m => {
        // 1. 【主动出击】：C 去点赞、评论了别人
        // (保持不变：展示 C 在任何地方留下的痕迹)
        const targetIsActive = 
          (m.interactions?.likes && m.interactions.likes.some(u => u.wxid === targetId)) ||
          (m.interactions?.comments && m.interactions.comments.some(c => 
            c.wxid === targetId || c.reply_to_wxid === targetId
          ));
        
        if (targetIsActive) return true;

        // 2. 【被动吸引】：C 发的朋友圈，被别人（B、A或其他链路节点）互动了
        // (修改点：不再强制要求是 rootId(A) 互动，只要有“他人”互动即可)
        if (m.author_wxid === targetId) {
           const hasInteractions = 
             (m.interactions?.likes && m.interactions.likes.some(u => u.wxid !== targetId)) ||
             (m.interactions?.comments && m.interactions.comments.some(c => c.wxid !== targetId));
           
           // 只要有人理他（形成了社交连线），就展示
           // 这样 B 评论 C 的朋友圈就能显示出来了
           // 同时依然过滤掉了 C 发的“无人问津”的自言自语
           if (hasInteractions) return true;
        }

        return false;
      });
    }

    // 🔥 模式二：单人查看模式 (左侧选了 A，中间没点球)
    if (selectedWxid.value) {
      return moments.value.filter(m => m.author_wxid === selectedWxid.value);
    }

    return moments.value;
  });

  return {
    moments,
    selectedWxid,
    filterWxid,
    loadFeeds,
    filteredMoments,
    contacts,
    getSmartName // 👈 暴露出这个新方法
  };
});
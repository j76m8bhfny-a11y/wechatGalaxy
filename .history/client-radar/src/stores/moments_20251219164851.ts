import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { invoke } from '@tauri-apps/api/core';

interface SnsRawItem {
  sns_id: string;
  create_time: number;
  content: string; 
}

export interface Moment {
  id: string;
  wxid: string;
  avatar: string;
  name: string;
  text: string;
  images: string[];
  date: string;
  timestamp: number;
  likes: any[];
  comments: any[];
  isRaw?: boolean; // 标记是否为原始乱码
}

export interface ContactSummary {
  id: string;
  avatar: string;
  momentCount: number;
  latestDate: string;
}

export const useMomentsStore = defineStore('moments', () => {
  const moments = ref<Moment[]>([]);
  const selectedWxid = ref<string>('');
  const filterWxid = ref<string>('');

  // 🛠️ 宽容版解析器
  const parseXmlContent = (rawContent: string) => {
    try {
      // 1. 尝试匹配 XML (不区分大小写)
      const match = rawContent.match(/<TimelineObject[\s\S]*?<\/TimelineObject>/i);
      
      if (!match) {
        // ⚠️ 关键修改：如果匹配失败，不再返回 null，而是返回“原始内容”
        // 这样即使全是乱码，也能显示出来，方便调试
        return { 
          text: '⚠️ [未识别格式] 原始内容预览:\n' + rawContent.substring(0, 500), 
          images: [], 
          username: 'unknown_format',
          isRaw: true
        };
      }

      const cleanXml = match[0];
      const parser = new DOMParser();
      const doc = parser.parseFromString(cleanXml, "text/xml");
      
      const text = doc.querySelector('ContentDesc')?.textContent || '';
      const images: string[] = [];
      doc.querySelectorAll('Media Url').forEach(node => {
        if(node.textContent) images.push(node.textContent);
      });
      const username = doc.querySelector('username')?.textContent || '';

      return { text, images, username, isRaw: false };

    } catch (e) {
      return { 
        text: '❌ [解析崩溃] ' + String(e), 
        images: [], 
        username: 'error',
        isRaw: true
      };
    }
  };

  const importFromDb = async (dbPath: string) => {
    if (!dbPath) return;
    try {
      console.log('📡 读取朋友圈:', dbPath);
      const rawList = await invoke<SnsRawItem[]>('read_moments_from_db', { dbPath });
      console.log(`✅ 后端返回: ${rawList.length} 条数据`);

      const parsedList: Moment[] = [];

      rawList.forEach(item => {
        const result = parseXmlContent(item.content);
        
        // 格式化时间
        const dateObj = new Date(item.create_time * 1000);
        
        parsedList.push({
          id: item.sns_id,
          // 如果解析出了 unknown_format，说明正则没匹配上
          wxid: result.username || 'unknown', 
          avatar: result.isRaw ? '❓' : '👤',
          name: result.isRaw ? '格式未知' : '加载中...', 
          text: result.text, // 这里会显示原始内容
          images: result.images,
          date: dateObj.toLocaleString(),
          timestamp: item.create_time,
          likes: [],   
          comments: [] 
        });
      });

      console.log(`✨ 渲染列表: ${parsedList.length} 条`);
      moments.value = parsedList;

    } catch (e) {
      console.error('❌ 读取失败:', e);
      throw e;
    }
  };

  // ... (Getters 保持不变)
  const filteredMoments = computed(() => {
    let list = moments.value;
    if (selectedWxid.value) {
      list = list.filter(m => m.wxid === selectedWxid.value);
    }
    return list;
  });

  const contacts = computed(() => {
    const map = new Map<string, ContactSummary>();
    moments.value.forEach(m => {
      // 即使是 unknown 用户也统计进去，方便看到数据
      if (!m.wxid) return; 
      
      if (!map.has(m.wxid)) {
        map.set(m.wxid, {
          id: m.wxid,
          avatar: m.avatar,
          momentCount: 0,
          latestDate: m.date
        });
      }
      const c = map.get(m.wxid)!;
      c.momentCount++;
      if (m.timestamp > (new Date(c.latestDate).getTime() / 1000)) {
         c.latestDate = m.date;
      }
    });
    return Array.from(map.values()).sort((a, b) => {
      return new Date(b.latestDate).getTime() - new Date(a.latestDate).getTime();
    });
  });

  return {
    moments,
    selectedWxid,
    filterWxid,
    importFromDb,
    filteredMoments,
    contacts
  };
});
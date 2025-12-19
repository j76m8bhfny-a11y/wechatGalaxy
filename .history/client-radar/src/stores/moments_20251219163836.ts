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

  // 🛠️ 增强版 XML 清洗器
  const parseXmlContent = (rawContent: string) => {
    try {
      // 1. 正则提取：不管前面有多少乱码，只抓取 <TimelineObject ... > 到 </TimelineObject> 之间的内容
      // [\s\S]*? 表示跨行匹配非贪婪模式
      const match = rawContent.match(/<TimelineObject[\s\S]*?<\/TimelineObject>/);
      
      if (!match) {
        // 如果没匹配到，可能是纯文本或者格式极其特殊，返回原始内容的前100字方便调试
        // return { text: '[非XML格式数据] ' + rawContent.substring(0, 50), images: [], username: '' };
        return null; // 没匹配到就直接丢弃，不显示报错，保证界面整洁
      }

      const cleanXml = match[0];
      const parser = new DOMParser();
      const doc = parser.parseFromString(cleanXml, "text/xml");
      
      // 2. 提取文字
      const text = doc.querySelector('ContentDesc')?.textContent || '';
      
      // 3. 提取图片
      const images: string[] = [];
      const medias = doc.querySelectorAll('Media Url');
      medias.forEach(node => {
        const url = node.textContent || '';
        if (url) images.push(url);
      });

      // 4. 提取发帖人
      const username = doc.querySelector('username')?.textContent || '';

      return { text, images, username };
    } catch (e) {
      console.warn("解析跳过:", e);
      return null;
    }
  };

  const importFromDb = async (dbPath: string) => {
    if (!dbPath) return;
    try {
      console.log('📡 读取朋友圈:', dbPath);
      const rawList = await invoke<SnsRawItem[]>('read_moments_from_db', { dbPath });
      console.log(`✅ 原始记录: ${rawList.length} 条 (含乱码)`);

      const parsedList: Moment[] = [];

      rawList.forEach(item => {
        // 解析清洗
        const result = parseXmlContent(item.content);
        
        // 只有解析成功的才加入列表
        if (result) {
          const { text, images, username } = result;
          const dateObj = new Date(item.create_time * 1000);

          parsedList.push({
            id: item.sns_id,
            wxid: username || 'unknown', 
            avatar: '👤',
            name: '加载中...', 
            text: text,
            images: images,
            date: dateObj.toLocaleString(),
            timestamp: item.create_time,
            likes: [],   
            comments: [] 
          });
        }
      });

      console.log(`✨ 有效朋友圈: ${parsedList.length} 条`);
      moments.value = parsedList;

    } catch (e) {
      console.error('❌ 读取失败:', e);
      throw e;
    }
  };

  // Getters
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
      if (!m.wxid || m.wxid === 'unknown') return;
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
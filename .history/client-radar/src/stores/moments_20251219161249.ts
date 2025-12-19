import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { invoke } from '@tauri-apps/api/core';

// ==========================================
// 1. 类型定义
// ==========================================

// Rust 返回的原始数据接口
interface SnsRawItem {
  sns_id: string;
  create_time: number;
  content: string; // 原始 XML 字符串
}

// 前端展示用的朋友圈接口
export interface Moment {
  id: string;
  wxid: string;    // 发帖人 ID
  avatar: string;  // 头像 (暂时用占位符)
  name: string;    // 名字 (通过 contactsStore 获取)
  text: string;    // 正文
  images: string[];// 图片链接列表
  date: string;    // 可读时间字符串
  timestamp: number;
  likes: any[];    // 点赞 (暂未解析)
  comments: any[]; // 评论 (暂未解析)
}

// 左侧列表用的精简接口
export interface ContactSummary {
  id: string;
  avatar: string;
  momentCount: number;
  latestDate: string;
}

export const useMomentsStore = defineStore('moments', () => {
  // ==========================================
  // State (状态)
  // ==========================================
  const moments = ref<Moment[]>([]);       // 存储所有解析后的朋友圈
  const selectedWxid = ref<string>('');    // 当前选中的联系人ID (用于过滤)
  const filterWxid = ref<string>('');      // 搜索/筛选 ID

  // ==========================================
  // Actions (逻辑方法)
  // ==========================================

  // 🛠️ 内部工具：解析 XML 内容
  const parseXmlContent = (xml: string) => {
    try {
      const parser = new DOMParser();
      const doc = parser.parseFromString(xml, "text/xml");
      
      // 1. 提取文字 (ContentDesc 标签)
      const text = doc.querySelector('ContentDesc')?.textContent || '';
      
      // 2. 提取图片 (MediaList -> Media -> Url)
      const images: string[] = [];
      const medias = doc.querySelectorAll('Media Url');
      medias.forEach(node => {
        const url = node.textContent || '';
        // 微信 XML 里的 Url 有时包含 CDATA 或特殊字符，直接提取即可
        // 注意：后续可能需要处理 Referrer 防盗链问题
        if (url) images.push(url);
      });

      // 3. 提取发帖人 (username 标签)
      // XML 里的 <username> 通常是发帖人的 wxid
      const username = doc.querySelector('username')?.textContent || '';

      return { text, images, username };
    } catch (e) {
      console.warn("XML 解析异常:", e);
      return { text: '[内容解析错误]', images: [], username: '' };
    }
  };

  // 🚀 核心：从数据库加载数据
  const importFromDb = async (dbPath: string) => {
    if (!dbPath) return;
    
    try {
      console.log('📡 正在从数据库读取朋友圈:', dbPath);
      
      // 1. 调用 Rust 后端命令
      const rawList = await invoke<SnsRawItem[]>('read_moments_from_db', { dbPath });
      console.log(`✅ 获取到 ${rawList.length} 条原始数据，开始解析...`);

      // 2. 遍历解析 XML
      const parsedList: Moment[] = rawList.map(item => {
        const { text, images, username } = parseXmlContent(item.content);
        
        // 格式化时间
        const dateObj = new Date(item.create_time * 1000);
        const dateStr = dateObj.toLocaleString();

        return {
          id: item.sns_id,
          // 如果 XML 里没找到 username，暂记为 unknown (通常 XML 里都有)
          wxid: username || 'unknown_user', 
          avatar: '👤', // 暂时使用通用头像，具体头像由 UI 层去匹配 ContactStore
          name: '加载中...', 
          text: text,
          images: images,
          date: dateStr,
          timestamp: item.create_time,
          likes: [],   
          comments: [] 
        };
      });

      // 3. 更新状态
      moments.value = parsedList;
      console.log('🎉 朋友圈数据解析完成，已更新 UI');

    } catch (e) {
      console.error('❌ 读取朋友圈失败:', e);
      // 可以选择抛出错误让 Sidebar 显示红色警告
      throw e; 
    }
  };

  // ==========================================
  // Getters (计算属性)
  // ==========================================

  // 🔍 筛选逻辑：根据 Sidebar 选中的人过滤 Feed
  const filteredMoments = computed(() => {
    let list = moments.value;

    // 如果左侧选中了某人，只显示他的朋友圈
    if (selectedWxid.value) {
      list = list.filter(m => m.wxid === selectedWxid.value);
    }
    
    return list;
  });

  // 👥 动态生成左侧联系人列表
  // 逻辑：遍历所有朋友圈，统计谁发了多少条，生成列表供 Sidebar 渲染
  const contacts = computed(() => {
    const map = new Map<string, ContactSummary>();
    
    moments.value.forEach(m => {
      // 过滤掉无效用户
      if (!m.wxid || m.wxid === 'unknown_user') return;

      if (!map.has(m.wxid)) {
        map.set(m.wxid, {
          id: m.wxid,
          avatar: m.avatar, // 使用 Moment 里的头像 (占位符)
          momentCount: 0,
          latestDate: m.date
        });
      }

      const c = map.get(m.wxid)!;
      c.momentCount++;
      
      // 更新该用户的“最近活跃时间”
      if (m.timestamp > (new Date(c.latestDate).getTime() / 1000)) {
         c.latestDate = m.date;
      }
    });

    // 转换为数组，并按“最近活跃时间”倒序排列
    return Array.from(map.values()).sort((a, b) => {
      return new Date(b.latestDate).getTime() - new Date(a.latestDate).getTime();
    });
  });

  return {
    // State
    moments,
    selectedWxid,
    filterWxid,
    
    // Actions
    importFromDb,
    
    // Getters
    filteredMoments,
    contacts
  };
});
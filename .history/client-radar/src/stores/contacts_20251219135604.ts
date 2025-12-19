import { defineStore } from 'pinia';
import { ref } from 'vue';
import { invoke } from '@tauri-apps/api/core'; // Tauri v2 调用核心

// 默认还是先加载个空的或静态的，以防数据库没连上
import mockData from '../assets/contacts_map.json';

interface DbContact {
  username: string;
  remark: string;
  nickname: string;
}

export const useContactsStore = defineStore('contacts', () => {
  // 1. 联系人映射表
  const contactMap = ref<Record<string, string>>({ ...mockData });
  const isLoading = ref(false);
  const errorMsg = ref('');

  // 2. 核心：从数据库导入
  const importFromDb = async (dbPath: string) => {
    if (!dbPath) return;
    
    isLoading.value = true;
    errorMsg.value = '';
    
    try {
      console.log('正在读取数据库:', dbPath);
      // 调用 Rust 后端
      const res = await invoke<DbContact[]>('read_contacts_from_db', { dbPath });
      console.log(`成功读取 ${res.length} 个联系人`);

      // 转换数据格式：优先用 Remark，其次用 NickName
      const newMap: Record<string, string> = {};
      res.forEach(c => {
        if (c.remark) {
          newMap[c.username] = c.remark;
        } else if (c.nickname) {
          newMap[c.username] = c.nickname;
        }
      });

      // 合并到现有 Map (或者直接覆盖 contactMap.value = newMap)
      Object.assign(contactMap.value, newMap);
      
    } catch (e) {
      console.error('数据库读取失败:', e);
      errorMsg.value = String(e);
    } finally {
      isLoading.value = false;
    }
  };

  // 3. 获取显示名称
  const getDisplayName = (wxid: string): string => {
    if (!wxid) return '未知用户';
    if (contactMap.value[wxid]) return contactMap.value[wxid];
    if (wxid.length > 10) return `user_${wxid.substring(wxid.length - 4)}`;
    return wxid;
  };

  return {
    contactMap,
    isLoading,
    errorMsg,
    getDisplayName,
    importFromDb
  };
});
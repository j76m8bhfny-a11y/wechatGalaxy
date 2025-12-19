import { defineStore } from 'pinia';
import { ref } from 'vue';
// 引入刚才创建的静态字典 (未来这里会变成从数据库读取)
import mockData from '../assets/contacts_map.json';

export const useContactsStore = defineStore('contacts', () => {
  // 1. 联系人映射表 Record<wxid, name>
  const contactMap = ref<Record<string, string>>(mockData);

  // 2. 核心方法：获取显示名称
  // 逻辑：有备注显示备注，没备注显示处理过的 wxid
  const getDisplayName = (wxid: string): string => {
    if (!wxid) return '未知用户';
    
    // 命中字典，直接返回真名
    if (contactMap.value[wxid]) {
      return contactMap.value[wxid];
    }

    // 没命中，美化一下 wxid (比如 wxid_123456 -> user_3456)
    if (wxid.length > 10) {
      return `user_${wxid.substring(wxid.length - 4)}`;
    }
    
    return wxid;
  };

  // 3. 未来扩展：修改备注 (Phase 3 后期功能)
  const updateContactName = (wxid: string, newName: string) => {
    contactMap.value[wxid] = newName;
  };

  return {
    contactMap,
    getDisplayName,
    updateContactName
  };
});
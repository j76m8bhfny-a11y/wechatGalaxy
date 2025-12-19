import os
import json
import traceback
import xmltodict
from datetime import datetime

# 引用核心模块
try:
    from wxManager.decrypt.get_wx_info import read_info
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
    import wxManager.db_v3.sns as sns_module 
    from wxManager.db_v3.sns import Sns
except ImportError:
    print("❌ 请确保在项目根目录下运行，且依赖已安装。")
    exit(1)

def parse_sns_xml(xml_str):
    """
    简单的 XML 清洗函数：提取文字和图片链接
    """
    if not xml_str:
        return {"text": "", "images": []}
    
    try:
        # 将 XML 转为字典
        data = xmltodict.parse(xml_str)
        timeline = data.get('TimelineObject', {})
        
        # 1. 提取文字内容
        text = timeline.get('contentDesc', '')
        
        # 2. 提取媒体列表 (图片/视频)
        media_list = []
        content_obj = timeline.get('ContentObject', {})
        if content_obj and 'MediaList' in content_obj:
            medias = content_obj['MediaList'].get('Media', [])
            # xmltodict 在只有一个子节点时返回 dict，多个时返回 list，需要兼容
            if isinstance(medias, dict):
                medias = [medias]
                
            for m in medias:
                # 尝试获取 URL，优先取高清图(Url)，没有则取缩略图(Thumb)
                url = m.get('Url', {}).get('#text', '')
                thumb = m.get('Thumb', {}).get('#text', '')
                type_code = m.get('Type', '0') # 2=图片, 6=视频
                
                if url or thumb:
                    media_list.append({
                        "type": "video" if type_code == '6' else "image",
                        "url": url if url else thumb,
                        "thumb": thumb
                    })
                    
        return {"text": text, "media": media_list}
        
    except Exception as e:
        # 解析失败这行可能不是标准朋友圈，忽略错误
        return {"text": "解析错误或非标准格式", "images": []}

def main():
    print("🚀 正在启动数据导出服务...")

    # --- 1. 获取密钥 ---
    version_path = os.path.join("wxManager", "decrypt", "version_list.json")
    with open(version_path, "r", encoding="utf-8") as f:
        version_dict = json.load(f)
    
    wx_infos = read_info(version_dict)
    if not wx_infos:
        print("❌ 请先登录 PC 微信！")
        return
    
    user_info = wx_infos[0]
    key = user_info['key']
    wx_dir = user_info['wx_dir']
    
    print(f"👤 当前用户: {user_info['name']}")

    # --- 2. 解密 Sns.db ---
    output_dir = os.path.abspath("./data_export") # 数据存放在 data_export 文件夹
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 自动查找 Sns.db 路径
    possible_paths = [
        os.path.join(wx_dir, "Sns.db"),
        os.path.join(wx_dir, "Msg", "Sns.db"),
    ]
    src_db = next((p for p in possible_paths if os.path.exists(p)), None)
    
    if not src_db:
        print("❌ 未找到 Sns.db，请确保电脑上有缓存朋友圈。")
        return

    dst_db = os.path.join(output_dir, "Sns.db")
    decrypt_db_file_v3(key, src_db, dst_db)

    # --- 3. 读取并转换数据 ---
    print("📥 正在读取并清洗数据...")
    
    # 注入路径 Hack
    sns_module.db_path = dst_db 
    
    sns = Sns()
    if not sns.open_flag:
        sns.init_database(output_dir)

    feeds = sns.get_feeds()
    
    if not feeds:
        print("⚠️ 数据库为空。")
        return

    # --- 4. 生成 JSON ---
    export_data = []
    for item in feeds:
        # item 结构: [FeedId, CreateTime, StrTime, Type, UserName, Status, StringId, Content]
        feed_id = item[0]
        timestamp = item[1]
        str_time = item[2]
        raw_xml = item[7]
        
        # 解析 XML 内容
        parsed_content = parse_sns_xml(raw_xml)
        
        # 组装给前端用的对象
        json_item = {
            "id": feed_id,
            "date": str_time,
            "timestamp": timestamp,
            "sender": item[4], # wxid
            "content": parsed_content['text'],
            "media": parsed_content['media']
        }
        export_data.append(json_item)

    # 保存文件
    json_path = os.path.join(output_dir, "moments.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_data, f, ensure_ascii=False, indent=2)

    print(f"✅ 导出成功！")
    print(f"📄 数据文件: {json_path}")
    print(f"📊 共导出 {len(export_data)} 条朋友圈")

if __name__ == "__main__":
    main()
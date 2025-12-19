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
    print("❌ 依赖缺失：请确保 wxManager 文件夹在当前目录下，且已安装 requirements.txt")
    exit(1)

def parse_sns_xml(xml_str):
    """
    解析朋友圈 XML，提取正文和媒体（图片/视频）
    """
    if not xml_str:
        return {"text": "", "media": []}
    
    try:
        data = xmltodict.parse(xml_str)
        timeline = data.get('TimelineObject', {})
        
        # 1. 提取文字
        text = timeline.get('contentDesc', '')
        
        # 2. 提取媒体
        media_list = []
        content_obj = timeline.get('ContentObject', {})
        if content_obj and 'MediaList' in content_obj:
            medias = content_obj['MediaList'].get('Media', [])
            if isinstance(medias, dict):
                medias = [medias]
                
            for m in medias:
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
    except:
        return {"text": "XML解析异常", "media": []}

def process_interactions(sns_driver, feed_id):
    """
    【新增】专门处理每条朋友圈的互动数据（点赞 & 评论）
    """
    comments_data = sns_driver.get_comment(feed_id)
    
    likes_list = []
    comments_list = []
    
    # 遍历该条朋友圈的所有互动记录
    for c in comments_data:
        # c 的结构对应 sns.py 中的 SQL 查询结果：
        # [FeedId, CommentId, CreateTime, StrTime, CommentType, Content, FromUserName, ReplyUserName, ReplyId]
        
        c_time = c[3]
        c_type = c[4] # 1=点赞, 2=评论, 3=其他
        c_content = c[5]
        sender_wxid = c[6]
        reply_to_wxid = c[7]
        
        if c_type == 1:
            # === 处理点赞 ===
            likes_list.append({
                "wxid": sender_wxid,
                "time": c_time
            })
        elif c_type == 2:
            # === 处理评论 ===
            comments_list.append({
                "wxid": sender_wxid,
                "content": c_content,
                "time": c_time,
                "reply_to": reply_to_wxid # 如果是回复别人的评论，这里会有值
            })
            
    return likes_list, comments_list

def main():
    print("🚀 [Phase 1] 启动全量数据采集...")

    # --- 1. 获取密钥 ---
    version_path = os.path.join("wxManager", "decrypt", "version_list.json")
    if not os.path.exists(version_path):
        print("❌ 找不到 version_list.json")
        return

    with open(version_path, "r", encoding="utf-8") as f:
        version_dict = json.load(f)
    
    print("🔑 读取微信信息...")
    wx_infos = read_info(version_dict)
    if not wx_infos:
        print("❌ 未检测到微信运行，请登录。")
        return
    
    user_info = wx_infos[0]
    key = user_info.get('key')
    wx_dir = user_info.get('wx_dir')
    
    if not key or key == 'None':
        print("❌ 密钥获取失败。")
        return
        
    print(f"👤 目标用户: {user_info.get('name')}")

    # --- 2. 解密数据库 ---
    output_dir = os.path.abspath("./client_radar_data") # 数据目录改个名，更正规
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 寻找 Sns.db
    possible_paths = [
        os.path.join(wx_dir, "Sns.db"),
        os.path.join(wx_dir, "Msg", "Sns.db"),
    ]
    src_db = next((p for p in possible_paths if os.path.exists(p)), None)
    
    if not src_db:
        print("❌ 本地未找到 Sns.db，请确保已浏览过朋友圈。")
        return

    dst_db = os.path.join(output_dir, "Sns.db")
    print(f"🔓 正在解密数据库: {src_db} -> {dst_db}")
    
    success, msg = decrypt_db_file_v3(key, src_db, dst_db)
    if not success:
        print(f"❌ 解密失败: {msg}")
        return

    # --- 3. 提取数据 ---
    print("📥 正在提取朋友圈及互动数据...")
    
    # 注入路径到模块
    sns_module.db_path = dst_db 
    
    sns = Sns()
    if not sns.open_flag:
        sns.init_database(output_dir)

    feeds = sns.get_feeds()
    
    if not feeds:
        print("⚠️ 数据库为空。建议在电脑上多刷一刷朋友圈再运行。")
        return

    export_list = []
    
    # 使用 tqdm 显示进度条（如果没装 tqdm 就简单 print）
    try:
        from tqdm import tqdm
        iterator = tqdm(feeds, desc="解析中", unit="条")
    except ImportError:
        iterator = feeds
        print(f"共发现 {len(feeds)} 条数据，开始解析...")

    for item in iterator:
        # item: [FeedId, CreateTime, StrTime, Type, UserName, Status, StringId, Content]
        feed_id = item[0]
        feed_xml = item[7]
        
        # 1. 解析内容
        content_data = parse_sns_xml(feed_xml)
        
        # 2. 【关键】获取互动数据（点赞和评论）
        # 需要传入 feed_id (可能是 int 或 stringId，sns.py 里通常用 stringId 查询)
        # item[6] 是 StringId (如 "138402..."), item[0] 是 FeedId (int)
        # 根据 sns.py 的 get_comment 实现: where FeedId=? 
        # 通常这里要传 FeedId (item[0])。如果不行再试 StringId。
        likes, comments = process_interactions(sns, feed_id)
        
        # 3. 组装数据
        feed_obj = {
            "id": str(item[6]), # 使用 StringId 作为唯一标识更通用
            "timestamp": item[1],
            "date": item[2],
            "author_wxid": item[4], # 发帖人的 wxid
            "content": {
                "text": content_data['text'],
                "media": content_data['media']
            },
            "stats": {
                "likes_count": len(likes),
                "comments_count": len(comments)
            },
            "interactions": {
                "likes": likes,       # 包含点赞人的 wxid
                "comments": comments  # 包含评论人的 wxid 和内容
            }
        }
        export_list.append(feed_obj)

    # --- 4. 保存 ---
    json_path = os.path.join(output_dir, "moments_full.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(export_list, f, ensure_ascii=False, indent=2)

    print(f"\n✅ 第一阶段完成！")
    print(f"📊 成功采集: {len(export_list)} 条朋友圈")
    print(f"📁 数据已保存: {json_path}")
    print("💡 提示：目前的 author_wxid 和 interactions 里的 wxid 都是微信号ID（如 wxid_xxxx）。")
    print("   后续阶段我们可以利用 Contact 表把它们替换成真实的‘微信昵称’。")

    sns.close()

if __name__ == "__main__":
    main()
import os
import sys
import json
import xmltodict
import sqlite3

# 1. 环境初始化
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # 引入解密模块
    from wxManager.decrypt import get_wx_info
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
    
    # 🔥 引入 wxManager 的 SNS 核心模块 🔥
    import wxManager.db_v3.sns as sns_module 
    from wxManager.db_v3.sns import Sns
    
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"依赖缺失: {str(e)}"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": f"初始化异常: {str(e)}"}))
    sys.exit(1)

# 2. XML 解析 (用于处理正文里的图片/视频/文字)
# wxManager 返回的只是 XML 字符串，我们需要转成前端能用的 JSON
def parse_sns_xml(xml_str):
    if not xml_str: return {"text": "", "media": []}
    try:
        # 清洗非法字符
        clean_xml = "".join([c for c in xml_str if c == '\t' or c == '\n' or c == '\r' or c >= ' '])
        
        # 截取 TimelineObject
        start = clean_xml.find("<TimelineObject")
        if start != -1: clean_xml = clean_xml[start:]
            
        data = xmltodict.parse(clean_xml)
        timeline = data.get('TimelineObject', {})
        
        text = timeline.get('ContentDesc', '') or timeline.get('contentDesc', '')
        media_list = []
        content_obj = timeline.get('ContentObject', {}) or timeline.get('contentObject', {})
        
        if content_obj and 'MediaList' in content_obj:
            media_wrapper = content_obj['MediaList'].get('Media', [])
            if isinstance(media_wrapper, dict): medias = [media_wrapper]
            else: medias = media_wrapper
            
            for m in medias:
                url_obj = m.get('Url', '')
                url = url_obj.get('#text', '') if isinstance(url_obj, dict) else url_obj
                thumb = m.get('Thumb', {}).get('#text', '') if isinstance(m.get('Thumb'), dict) else m.get('Thumb', '')
                
                type_code = m.get('Type', '0')
                src = url if url else thumb
                
                if src:
                    media_list.append({"type": "video" if type_code == '6' else "image", "src": src})
                    
        return {"text": text, "media": media_list}
    except:
        # 解析失败降级
        return {"text": "", "media": []}

# 3. 核心逻辑
def main():
    try:
        # --- A. 获取微信 Key ---
        json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
        with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
        
        wx_infos = get_wx_info.read_info(version_list)
        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未登录微信"}))
            return

        user_info = wx_infos[0]
        key = user_info.get('key')
        wxid = user_info.get('wxid')
        wx_dir = user_info.get('wx_dir')
        
        # --- B. 准备输出目录 ---
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".client-radar", "decrypted", wxid)
        if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
        
        target_micro = os.path.join(output_dir, "MicroMsg.db")
        target_sns = os.path.join(output_dir, "Sns.db")
        
        # --- C. 解密通讯录 (MicroMsg.db) ---
        db_base_path = os.path.join(wx_dir, "Msg") 
        src_micro = os.path.join(os.path.dirname(db_base_path), "MicroMsg.db")
        if not os.path.exists(src_micro): 
            src_micro = os.path.join(wx_dir, "MicroMsg.db")
            
        if os.path.exists(src_micro):
            decrypt_db_file_v3(key, src_micro, target_micro)
        
        # --- D. 解密朋友圈 (Sns.db) ---
        possible_sns_paths = [
            os.path.join(db_base_path, "Sns.db"),
            os.path.join(os.path.dirname(db_base_path), "Sns", "Sns.db")
        ]
        
        sns_decrypted = False
        for src in possible_sns_paths:
            if os.path.exists(src):
                success, msg = decrypt_db_file_v3(key, src, target_sns)
                if success: sns_decrypted = True; break
        
        # --- E. 🔥 使用 wxManager 解析数据 🔥 ---
        feeds_data = []
        if sns_decrypted:
            # 1. 注入解密后的数据库路径
            # 这是最关键的一步！告诉 wxManager 去读我们刚解密好的文件
            sns_module.db_path = target_sns
            
            # 2. 初始化 Sns 对象
            sns_driver = Sns()
            
            # 3. 获取所有朋友圈 (get_feeds 内部会处理 Protobuf)
            # 假设返回结构: [FeedId, CreateTime, StrTime, Type, UserName, Status, StringId, Content]
            raw_feeds = sns_driver.get_feeds()
            
            # 限制数量，防止前端爆炸 (取最新的 500 条)
            # 注意: get_feeds 返回的通常是按时间倒序的，直接切片即可
            if raw_feeds and len(raw_feeds) > 500:
                raw_feeds = raw_feeds[:500]
                
            for item in raw_feeds:
                try:
                    feed_id = item[0]  # Int64 ID
                    string_id = str(item[6]) # String ID (通常更安全)
                    timestamp = item[1]
                    username = item[4]
                    xml_content = item[7]
                    
                    # A. 解析正文
                    parsed_content = parse_sns_xml(xml_content)
                    
                    # B. 解析互动 (调用 wxManager 的 get_comment)
                    # get_comment 会自动处理 Buffer 解析
                    raw_comments = sns_driver.get_comment(feed_id)
                    
                    likes = []
                    comments = []
                    
                    for c in raw_comments:
                        # c 的结构: [FeedId, CommentId, CreateTime, StrTime, CommentType, Content, FromUserName, ReplyUserName, ReplyId]
                        c_time = c[3]
                        c_type = c[4] # 1=点赞, 2=评论
                        c_content = c[5]
                        c_user = c[6]
                        c_reply_to = c[7]
                        
                        interaction_item = {
                            "wxid": c_user,
                            "name": "", # wxManager 可能不返回快照名，留给前端查通讯录
                            "content": c_content if c_content else "",
                            "time": c_time,
                            "reply_to_wxid": c_reply_to if c_reply_to else ""
                        }
                        
                        if c_type == 1:
                            likes.append(interaction_item)
                        elif c_type == 2:
                            comments.append(interaction_item)
                    
                    # C. 组装最终对象
                    feeds_data.append({
                        "id": string_id,
                        "timestamp": timestamp,
                        "author_wxid": username,
                        "content": parsed_content,
                        "stats": {
                            "likes_count": len(likes), 
                            "comments_count": len(comments)
                        },
                        "interactions": {
                            "likes": likes, 
                            "comments": comments
                        }
                    })
                except Exception:
                    continue
            
            # 关闭数据库连接
            try: sns_driver.close()
            except: pass

        # --- F. 输出 JSON ---
        result = {
            "status": "success",
            "wxid": wxid,
            "micro_db_path": target_micro,
            "sns_db_path": target_sns,
            "feeds": feeds_data
        }
        print(json.dumps(result))

    except Exception as e:
        # 全局错误捕获
        print(json.dumps({"status": "error", "message": f"Global Error: {str(e)}"}))

if __name__ == "__main__":
    main()
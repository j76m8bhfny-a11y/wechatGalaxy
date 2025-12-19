import os
import sys
import json
import xmltodict
import sqlite3

# 1. 环境初始化
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"依赖缺失: {str(e)}"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": f"初始化异常: {str(e)}"}))
    sys.exit(1)

# 2. XML 解析 (保持不变)
def parse_sns_xml(xml_str):
    if not xml_str: return {"text": "", "media": []}
    try:
        start = xml_str.find("<TimelineObject")
        if start != -1: xml_str = xml_str[start:]
        xml_str = "".join([c for c in xml_str if c == '\t' or c == '\n' or c == '\r' or c >= ' '])
        data = xmltodict.parse(xml_str)
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
                type_code = m.get('Type', '0')
                if url:
                    media_list.append({"type": "video" if type_code == '6' else "image", "src": url})
        return {"text": text, "media": media_list}
    except:
        return {"text": "", "media": []}

# 3. 🔥🔥 核心修复：适配 CommentV20 和 SnsComment 🔥🔥
def get_interactions(cursor, feed_id):
    likes = []
    comments = []
    
    try:
        # A. 探测表名
        table_name = "SnsComment"
        # 检查是否存在 CommentV20 (新版结构)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='CommentV20'")
        if cursor.fetchone():
            table_name = "CommentV20"
            # 新版列名映射: FromUserName -> wxid, 无 NickName
            sql = """
                SELECT FromUserName, Content, CreateTime, CommentType, ReplyUserName 
                FROM CommentV20 
                WHERE FeedId=? 
                ORDER BY CreateTime ASC
            """
            cursor.execute(sql, (feed_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                wxid, content, time, c_type, reply_wxid = row
                
                # 处理二进制内容
                if isinstance(content, bytes): 
                    content = content.decode('utf-8', errors='ignore')
                
                item = {
                    "wxid": wxid,
                    "name": "", # CommentV20 没有昵称列，留空让前端查通讯录
                    "content": content,
                    "time": time,
                    "reply_to_wxid": reply_wxid if reply_wxid else ""
                }
                
                try: c_type = int(c_type)
                except: c_type = 0
                
                if c_type == 1: likes.append(item)
                elif c_type == 2 or c_type == 3: comments.append(item) # 3 sometimes used for replies
                
        else:
            # B. 旧版 SnsComment 结构
            # 旧版列名: UserName -> wxid, 有 NickName
            sql = """
                SELECT UserName, NickName, Content, CreateTime, CommentType, ReplyUserName 
                FROM SnsComment 
                WHERE FeedId=? 
                ORDER BY CreateTime ASC
            """
            cursor.execute(sql, (feed_id,))
            rows = cursor.fetchall()
            
            for row in rows:
                wxid, nickname, content, time, c_type, reply_wxid = row
                
                if isinstance(content, bytes): 
                    content = content.decode('utf-8', errors='ignore')
                
                item = {
                    "wxid": wxid,
                    "name": nickname if nickname else "",
                    "content": content,
                    "time": time,
                    "reply_to_wxid": reply_wxid if reply_wxid else ""
                }
                
                if c_type == 1: likes.append(item)
                elif c_type == 2: comments.append(item)

    except Exception as e:
        # 遇到错误静默处理，避免崩溃，但打印日志方便调试
        # print(f"Interaction Error: {e}")
        pass
        
    return likes, comments

# 4. 主读取逻辑 (适配 FeedsV20)
def read_feeds_from_db(db_path):
    feeds = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 探测朋友圈表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_name = "SnsInfo"
        if "FeedsV20" in tables: table_name = "FeedsV20"
        
        # 探测列名
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        content_col = "Content"
        for col in ["FaultContent", "Buffer", "objectDesc"]:
            if col in columns: content_col = col; break
                
        id_col = "FeedId" if "FeedId" in columns else "SnsId"
        
        # 查询 (限制 300 条)
        cursor.execute(f"SELECT {id_col}, CreateTime, {content_col}, UserName FROM {table_name} WHERE {content_col} IS NOT NULL ORDER BY CreateTime DESC LIMIT 300")
        rows = cursor.fetchall()
        
        for row in rows:
            sns_id, create_time, content_blob, username = row
            content_str = ""
            if isinstance(content_blob, bytes):
                try: content_str = content_blob.decode('utf-8', errors='ignore')
                except: pass
            else: content_str = str(content_blob)
                
            parsed = parse_sns_xml(content_str)
            
            # 获取互动
            likes, comments = get_interactions(cursor, sns_id)
            
            feeds.append({
                "id": str(sns_id),
                "timestamp": create_time,
                "author_wxid": username, 
                "content": parsed,       
                "stats": { "likes_count": len(likes), "comments_count": len(comments) },
                "interactions": { "likes": likes, "comments": comments }
            })
        conn.close()
    except Exception:
        return []
    return feeds

# 5. 主入口
def main():
    try:
        json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
        with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
        
        wx_infos = get_wx_info.read_info(version_list)
        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未登录微信"}))
            return
        user_info = wx_infos[0]
        
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".client-radar", "decrypted", user_info.get('wxid'))
        if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
        
        target_micro = os.path.join(output_dir, "MicroMsg.db")
        target_sns = os.path.join(output_dir, "Sns.db")
        
        # 解密 MicroMsg
        db_base_path = os.path.join(user_info.get('wx_dir'), "Msg") 
        src_micro = os.path.join(os.path.dirname(db_base_path), "MicroMsg.db")
        if not os.path.exists(src_micro): src_micro = os.path.join(user_info.get('wx_dir'), "MicroMsg.db")
        if os.path.exists(src_micro): decrypt_db_file_v3(user_info.get('key'), src_micro, target_micro)
        
        # 解密 Sns
        possible_sns_paths = [os.path.join(db_base_path, "Sns.db"), os.path.join(os.path.dirname(db_base_path), "Sns", "Sns.db")]
        sns_decrypted = False
        for src in possible_sns_paths:
            if os.path.exists(src):
                success, _ = decrypt_db_file_v3(user_info.get('key'), src, target_sns)
                if success: sns_decrypted = True; break
        
        feeds_data = []
        if sns_decrypted: feeds_data = read_feeds_from_db(target_sns)
            
        print(json.dumps({
            "status": "success", 
            "wxid": user_info.get('wxid'),
            "micro_db_path": target_micro, 
            "sns_db_path": target_sns, 
            "feeds": feeds_data
        }))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()
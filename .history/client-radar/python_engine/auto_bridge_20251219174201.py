import os
import sys
import json
import xmltodict
import sqlite3

# 引用核心模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"依赖缺失详细信息: {str(e)}"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": f"其他异常: {str(e)}"}))
    sys.exit(1)

def parse_sns_xml(xml_str):
    """ 解析朋友圈 XML """
    if not xml_str: return {"text": "", "media": []}
    try:
        start = xml_str.find("<TimelineObject")
        if start != -1: xml_str = xml_str[start:]
        
        # 容错处理：过滤掉非法的控制字符，防止 xmltodict 报错
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
                url = m.get('Url', {}).get('#text', '') if isinstance(m.get('Url'), dict) else m.get('Url', '')
                type_code = m.get('Type', '0')
                if url:
                    media_list.append({
                        "type": "video" if type_code == '6' else "image",
                        "src": url
                    })
        return {"text": text, "media": media_list}
    except:
        return {"text": "", "media": []}

def get_interactions(cursor, feed_id):
    """ 读取点赞和评论 """
    likes = []
    comments = []
    try:
        # SnsComment 表结构通常是: FeedId, CommentType, Content, CreateTime, UserName, NickName
        # CommentType: 1=点赞, 2=评论
        # 注意：FeedId 在数据库里可能是长整型，但也可能需要用 StringId 匹配，这里尝试用 FeedId
        cursor.execute(
            "SELECT UserName, NickName, Content, CreateTime, CommentType FROM SnsComment WHERE FeedId=? ORDER BY CreateTime ASC", 
            (feed_id,)
        )
        for row in cursor.fetchall():
            wxid, nickname, content, time, c_type = row
            
            # 处理二进制内容
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            item = {
                "wxid": wxid,
                "content": content,
                "time": time
            }
            
            if c_type == 1:
                likes.append(item)
            elif c_type == 2:
                comments.append(item)
                
    except Exception:
        pass # 表可能不存在或结构不同，忽略错误
        
    return likes, comments

def read_feeds_from_db(db_path):
    feeds = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 确定表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        table_name = "FeedsV20" if "FeedsV20" in tables else "SnsInfo"
        
        # 2. 确定列名
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        content_col = "Content"
        for col in ["FaultContent", "Buffer", "objectDesc"]:
            if col in columns: content_col = col; break
                
        id_col = "FeedId" if "FeedId" in columns else "SnsId"
        
        # 3. 查询朋友圈主体
        cursor.execute(f"SELECT {id_col}, CreateTime, {content_col}, UserName FROM {table_name} WHERE {content_col} IS NOT NULL ORDER BY CreateTime DESC LIMIT 300")
        rows = cursor.fetchall()
        
        # 4. 遍历处理
        for row in rows:
            sns_id, create_time, content_blob, username = row
            
            content_str = ""
            if isinstance(content_blob, bytes):
                try: content_str = content_blob.decode('utf-8', errors='ignore')
                except: pass
            else: content_str = str(content_blob)
                
            parsed = parse_sns_xml(content_str)
            
            # 🔥 获取互动数据 (传入 sns_id)
            likes, comments = get_interactions(cursor, sns_id)
            
            feeds.append({
                "id": str(sns_id),
                "timestamp": create_time,
                "author_wxid": username, 
                "content": parsed,       
                "stats": {
                    "likes_count": len(likes), 
                    "comments_count": len(comments)
                },
                "interactions": {
                    "likes": likes, 
                    "comments": comments
                }
            })
            
        conn.close()
    except Exception:
        return []
    return feeds

def main():
    try:
        # 1. 初始化
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
        
        # 2. 准备目录
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".client-radar", "decrypted", wxid)
        if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
        
        target_micro = os.path.join(output_dir, "MicroMsg.db")
        target_sns = os.path.join(output_dir, "Sns.db")
        
        # 3. 解密 MicroMsg.db (用于匹配人名)
        db_base_path = os.path.join(wx_dir, "Msg") 
        src_micro = os.path.join(os.path.dirname(db_base_path), "MicroMsg.db")
        if not os.path.exists(src_micro): src_micro = os.path.join(wx_dir, "MicroMsg.db")
        if os.path.exists(src_micro): decrypt_db_file_v3(key, src_micro, target_micro)
        
        # 4. 解密 Sns.db (用于内容)
        possible_sns_paths = [os.path.join(db_base_path, "Sns.db"), os.path.join(os.path.dirname(db_base_path), "Sns", "Sns.db")]
        sns_decrypted = False
        for src in possible_sns_paths:
            if os.path.exists(src):
                success, msg = decrypt_db_file_v3(key, src, target_sns)
                if success: sns_decrypted = True; break
        
        # 5. 解析并输出
        feeds_data = []
        if sns_decrypted:
            feeds_data = read_feeds_from_db(target_sns)
            
        print(json.dumps({
            "status": "success",
            "wxid": wxid,
            "micro_db_path": target_micro,
            "sns_db_path": target_sns,
            "feeds": feeds_data
        }))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()
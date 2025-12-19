import os
import sys
import json
import xmltodict
import sqlite3

# ==========================================
# 1. 环境与依赖初始化
# ==========================================
# 确保能找到同级目录下的 wxManager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info
    # 注意：必须指向 decrypt_v3 模块
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
except ImportError as e:
    # 捕获依赖缺失错误，返回 JSON 给 Rust
    print(json.dumps({"status": "error", "message": f"依赖缺失详细信息: {str(e)}"}))
    sys.exit(1)
except Exception as e:
    print(json.dumps({"status": "error", "message": f"初始化异常: {str(e)}"}))
    sys.exit(1)

# ==========================================
# 2. 核心功能函数
# ==========================================

def parse_sns_xml(xml_str):
    """ 
    解析朋友圈 XML 内容 
    提取：正文、图片、视频链接
    """
    if not xml_str: return {"text": "", "media": []}
    try:
        # 1. 简单清洗：移除头部二进制乱码
        start = xml_str.find("<TimelineObject")
        if start != -1: 
            xml_str = xml_str[start:]
        
        # 2. 过滤非法控制字符 (防止 xmltodict 崩溃)
        xml_str = "".join([c for c in xml_str if c == '\t' or c == '\n' or c == '\r' or c >= ' '])

        # 3. 解析 XML
        data = xmltodict.parse(xml_str)
        timeline = data.get('TimelineObject', {})
        
        # 4. 获取文字 (兼容不同大小写)
        text = timeline.get('ContentDesc', '') or timeline.get('contentDesc', '')
        
        # 5. 获取媒体列表
        media_list = []
        content_obj = timeline.get('ContentObject', {}) or timeline.get('contentObject', {})
        
        if content_obj and 'MediaList' in content_obj:
            media_wrapper = content_obj['MediaList'].get('Media', [])
            
            # xmltodict 特性：单条是 dict，多条是 list，需统一处理
            if isinstance(media_wrapper, dict): 
                medias = [media_wrapper]
            else: 
                medias = media_wrapper
                
            for m in medias:
                # 提取 Url (有时候是直接文本，有时候是嵌套对象)
                url_obj = m.get('Url', '')
                url = url_obj.get('#text', '') if isinstance(url_obj, dict) else url_obj
                
                # Type: 2=图片, 6=视频
                type_code = m.get('Type', '0')
                
                if url:
                    media_list.append({
                        "type": "video" if type_code == '6' else "image",
                        "src": url
                    })
                    
        return {"text": text, "media": media_list}
    except Exception:
        # 解析失败时不中断，返回空内容即可
        return {"text": "", "media": []}

def get_interactions(cursor, feed_id):
    """ 
    读取互动的点赞和评论 
    包含：wxid, 名字, 内容, 回复关系
    """
    likes = []
    comments = []
    try:
        # SQL 查询：增加 ReplyUserName (被回复人的 wxid)
        # SnsComment 表结构: FeedId, CommentType, Content, CreateTime, UserName, NickName, ReplyUserName
        cursor.execute(
            """
            SELECT UserName, NickName, Content, CreateTime, CommentType, ReplyUserName 
            FROM SnsComment 
            WHERE FeedId=? 
            ORDER BY CreateTime ASC
            """, 
            (feed_id,)
        )
        
        for row in cursor.fetchall():
            wxid, nickname, content, time, c_type, reply_wxid = row
            
            # 处理二进制内容乱码
            if isinstance(content, bytes):
                content = content.decode('utf-8', errors='ignore')
            
            # 构造互动对象
            item = {
                "wxid": wxid,
                "name": nickname if nickname else "",  # 快照名字
                "content": content,
                "time": time,
                "reply_to_wxid": reply_wxid if reply_wxid else "" # 核心：回复对象ID
            }
            
            # 分类：1=点赞, 2=评论 (还有3,4等其他类型暂时忽略)
            if c_type == 1:
                likes.append(item)
            elif c_type == 2:
                comments.append(item)
                
    except Exception:
        pass # 表不存在或结构不支持时忽略
        
    return likes, comments

def read_feeds_from_db(db_path):
    """ 
    主逻辑：读取朋友圈数据 
    """
    feeds = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 1. 智能探测表名 (FeedsV20 或 SnsInfo)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_name = "SnsInfo"
        if "FeedsV20" in tables: table_name = "FeedsV20"
        
        # 2. 智能探测列名 (Content 还是 FaultContent)
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        content_col = "Content"
        for col in ["FaultContent", "Buffer", "objectDesc"]:
            if col in columns:
                content_col = col
                break
        
        # ID 列名适配
        id_col = "FeedId" if "FeedId" in columns else "SnsId"
        
        # 3. 执行查询 (限制 300 条)
        cursor.execute(f"SELECT {id_col}, CreateTime, {content_col}, UserName FROM {table_name} WHERE {content_col} IS NOT NULL ORDER BY CreateTime DESC LIMIT 300")
        rows = cursor.fetchall()
        
        # 4. 遍历处理每一条
        for row in rows:
            sns_id, create_time, content_blob, username = row
            
            # 转字符串
            content_str = ""
            if isinstance(content_blob, bytes):
                try: content_str = content_blob.decode('utf-8', errors='ignore')
                except: pass
            else: 
                content_str = str(content_blob)
                
            # 解析 XML
            parsed = parse_sns_xml(content_str)
            
            # 获取互动数据 (传入 sns_id)
            likes, comments = get_interactions(cursor, sns_id)
            
            # 组装最终对象
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

# ==========================================
# 3. 程序入口
# ==========================================

def main():
    try:
        # --- A. 获取微信 Key ---
        json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
        with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
        
        wx_infos = get_wx_info.read_info(version_list)
        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未登录微信或无法获取信息"}))
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
        # 必须解密这个，否则左侧列表为空
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
        
        # --- E. 解析数据 ---
        feeds_data = []
        if sns_decrypted:
            feeds_data = read_feeds_from_db(target_sns)
            
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
        # 全局捕获，防止 crash
        print(json.dumps({"status": "error", "message": f"全局异常: {str(e)}"}))

if __name__ == "__main__":
    main()
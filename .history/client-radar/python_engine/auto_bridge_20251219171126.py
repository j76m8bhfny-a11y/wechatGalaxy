import os
import sys
import json
import xmltodict
import sqlite3

# 引用核心模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info, decrypt_db_file_v3
except ImportError:
    # 如果找不到模块，打印 JSON 格式错误，方便 Rust 捕获
    print(json.dumps({"status": "error", "message": "依赖缺失: wxManager"}))
    sys.exit(1)

def parse_sns_xml(xml_str):
    """ 解析朋友圈 XML (复用你的逻辑) """
    if not xml_str: return {"text": "", "media": []}
    try:
        # 简单清洗：有时候前面有乱码，尝试找 <TimelineObject
        start = xml_str.find("<TimelineObject")
        if start != -1:
            xml_str = xml_str[start:]
            
        data = xmltodict.parse(xml_str)
        timeline = data.get('TimelineObject', {})
        text = timeline.get('contentDesc', '')
        media_list = []
        content_obj = timeline.get('ContentObject', {})
        if content_obj and 'MediaList' in content_obj:
            medias = content_obj['MediaList'].get('Media', [])
            if isinstance(medias, dict): medias = [medias]
            for m in medias:
                url = m.get('Url', {}).get('#text', '')
                type_code = m.get('Type', '0')
                if url:
                    media_list.append({
                        "type": "video" if type_code == '6' else "image",
                        "src": url
                    })
        return {"text": text, "media": media_list}
    except:
        return {"text": "XML解析失败", "media": []}

def read_feeds_from_db(db_path):
    """ 直接用 Python 读取数据库，不依赖 wxManager 的 sns 模块，避免复杂的依赖 """
    feeds = []
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 智能探测：到底是 FeedsV20 还是 SnsInfo
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        table_name = "SnsInfo"
        if "FeedsV20" in tables: table_name = "FeedsV20"
        
        # 智能探测：内容列叫 Content 还是 FaultContent
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        
        # 常见的列名优先级
        content_col = "Content"
        for col in ["FaultContent", "Buffer", "objectDesc"]:
            if col in columns:
                content_col = col
                break
                
        # 查询数据 (ID, Time, Content)
        # 注意：FeedsV20 的 ID 可能是 FeedId
        id_col = "FeedId" if "FeedId" in columns else "SnsId"
        
        cursor.execute(f"SELECT {id_col}, CreateTime, {content_col} FROM {table_name} WHERE {content_col} IS NOT NULL ORDER BY CreateTime DESC LIMIT 100")
        
        for row in cursor.fetchall():
            sns_id, create_time, content_blob = row
            
            # 处理二进制数据
            content_str = ""
            if isinstance(content_blob, bytes):
                try:
                    content_str = content_blob.decode('utf-8', errors='ignore')
                except: pass
            else:
                content_str = str(content_blob)
                
            parsed = parse_sns_xml(content_str)
            
            feeds.append({
                "id": str(sns_id),
                "timestamp": create_time,
                "text": parsed['text'],
                "images": [m['src'] for m in parsed['media']],
                "raw_preview": content_str[:50] # 调试用
            })
            
        conn.close()
    except Exception as e:
        return []
    return feeds

def main():
    try:
        # 1. 正常流程：解密
        json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
        with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
        
        try:
            wx_infos = get_wx_info.read_info(version_list)
        except Exception:
            print(json.dumps({"status": "error", "message": "无法读取微信信息"}))
            return

        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未登录微信"}))
            return

        user_info = wx_infos[0]
        key = user_info.get('key')
        wxid = user_info.get('wxid')
        wx_dir = user_info.get('wx_dir')
        
        # 2. 准备路径
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".client-radar", "decrypted", wxid)
        if not os.path.exists(output_dir): os.makedirs(output_dir, exist_ok=True)
        
        target_micro = os.path.join(output_dir, "MicroMsg.db")
        target_sns = os.path.join(output_dir, "Sns.db")
        
        # 3. 执行解密 (Sns)
        # 这里简化处理，假设 MicroMsg 已经解密或不重要，重点搞 Sns
        db_base_path = os.path.join(wx_dir, "Msg") 
        possible_sns_paths = [
            os.path.join(db_base_path, "Sns.db"),
            os.path.join(os.path.dirname(db_base_path), "Sns", "Sns.db")
        ]
        
        sns_decrypted = False
        for src in possible_sns_paths:
            if os.path.exists(src):
                success, msg = decrypt_db_file_v3(key, src, target_sns)
                if success: sns_decrypted = True; break
        
        # 4. 🔥【核心改变】Python 直接读取并解析数据
        feeds_data = []
        if sns_decrypted:
            feeds_data = read_feeds_from_db(target_sns)
            
        # 5. 输出最终 JSON 给 Rust
        result = {
            "status": "success",
            "wxid": wxid,
            "micro_db_path": target_micro, # 依然返回路径给 Rust 读通讯录
            "sns_db_path": target_sns,
            "feeds": feeds_data # 🔥 直接把解析好的数据送给前端！
        }
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()
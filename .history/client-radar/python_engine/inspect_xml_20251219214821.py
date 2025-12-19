import sqlite3
import os
import json
import sys

# 1. 自动定位数据库
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info
    json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
    with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
    wx_infos = get_wx_info.read_info(version_list)
    user_info = wx_infos[0]
    
    home_dir = os.path.expanduser("~")
    sns_db_path = os.path.join(home_dir, ".client-radar", "decrypted", user_info.get('wxid'), "Sns.db")
    
    print(f"✅ 正在读取数据库: {sns_db_path}")
    conn = sqlite3.connect(sns_db_path)
    cursor = conn.cursor()

    # 2. 目标 FeedId
    target_id = -3632670000990055880
    print(f"🔍 正在查询朋友圈 ID: {target_id}")

    # 3. 确定表名 (FeedsV20 或 SnsInfo)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    table_name = "FeedsV20" if "FeedsV20" in tables else "SnsInfo"
    print(f"📋 锁定表名: {table_name}")

    # 4. 提取 XML 内容
    # 注意：列名可能是 Content, FaultContent, 或 Buffer
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [r[1] for r in cursor.fetchall()]
    content_col = "Content"
    for c in ["FaultContent", "Buffer"]:
        if c in cols: content_col = c; break
    
    print(f"📋 锁定列名: {content_col}")

    # 5. 执行查询
    cursor.execute(f"SELECT {content_col} FROM {table_name} WHERE FeedId=?", (target_id,))
    row = cursor.fetchone()

    if row:
        raw_bytes = row[0]
        # 尝试解码，忽略错误
        try:
            xml_str = raw_bytes.decode('utf-8', errors='ignore')
            print("\n" + "="*50)
            print("📜 原始 XML 内容 (部分截取)")
            print("="*50)
            print(xml_str[:2000]) # 打印前2000个字符，通常评论在前面
            
            print("\n" + "="*50)
            print("🧐 智能分析结果")
            print("="*50)
            
            if "commentList" in xml_str:
                print("✅ 发现 '<commentList>' 标签！评论确实藏在这里！")
            else:
                print("❌ 未发现 '<commentList>' 标签。")

            if "comment" in xml_str:
                print("✅ 发现 '<comment>' 标签！")
            
            # 尝试搜索常见的评论关键标签
            import re
            comments = re.findall(r'<content>(.*?)</content>', xml_str)
            if comments:
                print(f"✅ 提取到潜在内容 (包含正文和评论): {comments}")
            
        except Exception as e:
            print(f"解码失败: {e}")
    else:
        print("❌ 未找到该 ID 的记录，请检查 ID 是否正确。")

    conn.close()

except Exception as e:
    import traceback
    traceback.print_exc()
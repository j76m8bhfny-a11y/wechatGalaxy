import sqlite3
import os
import json
import sys
import re

# 1. 自动定位数据库
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # 这一步是为了获取正确的数据库路径
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

    # 3. 确定表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    table_name = "FeedsV20" if "FeedsV20" in tables else "SnsInfo"
    print(f"📋 锁定表名: {table_name}")

    # 4. 确定列名
    cursor.execute(f"PRAGMA table_info({table_name})")
    cols = [r[1] for r in cursor.fetchall()]
    content_col = "Content"
    for c in ["FaultContent", "Buffer"]:
        if c in cols: content_col = c; break
    print(f"📋 锁定列名: {content_col}")

    # 5. 执行查询
    # 注意：有时候 ID 需要转字符串查询
    cursor.execute(f"SELECT {content_col} FROM {table_name} WHERE FeedId=?", (target_id,))
    row = cursor.fetchone()

    # 如果数字查不到，试一下字符串
    if not row:
        print("⚠️ 数字 ID 未查到，尝试字符串 ID...")
        cursor.execute(f"SELECT {content_col} FROM {table_name} WHERE FeedId=?", (str(target_id),))
        row = cursor.fetchone()

    if row:
        raw_data = row[0]
        xml_str = ""

        # 🔥 修复点：智能类型判断 🔥
        if isinstance(raw_data, bytes):
            try:
                xml_str = raw_data.decode('utf-8', errors='ignore')
            except:
                xml_str = str(raw_data)
        else:
            xml_str = str(raw_data) # 已经是字符串，直接用

        print("\n" + "="*50)
        print("📜 XML 内容摘要 (前 1000 字符)")
        print("="*50)
        print(xml_str[:1000]) 
        
        print("\n" + "="*50)
        print("🧐 深度分析结果")
        print("="*50)
        
        # 1. 检查 commentList 标签
        if "<commentList>" in xml_str or "&lt;commentList&gt;" in xml_str:
            print("✅ 成功发现 '<commentList>' 标签！")
            print("   (这证明评论确实藏在 XML 里，没有存进数据库表)")
        else:
            print("❌ 未发现 '<commentList>' 标签。")

        # 2. 尝试提取具体的评论内容
        # 简单的正则匹配 <content>...</content>
        comments = re.findall(r'<content>(.*?)</content>', xml_str)
        if comments:
            print(f"\n✅ 提取到 {len(comments)} 条内容 (含正文和评论):")
            for i, c in enumerate(comments):
                if len(c) > 20: c = c[:20] + "..."
                print(f"   {i+1}. {c}")
        else:
            # 可能是转义字符 &lt;content&gt;
            comments_esc = re.findall(r'&lt;content&gt;(.*?)&lt;/content&gt;', xml_str)
            if comments_esc:
                print(f"\n✅ 提取到 (转义格式) 内容:")
                for i, c in enumerate(comments_esc):
                    print(f"   {i+1}. {c}")
            else:
                print("\n⚠️ 未能通过正则提取到 content，请人工检查上方 XML。")

    else:
        print("❌ 依然未找到记录，这可能是 FeedId 在数据库中存储格式的问题。")

    conn.close()

except Exception as e:
    import traceback
    traceback.print_exc()
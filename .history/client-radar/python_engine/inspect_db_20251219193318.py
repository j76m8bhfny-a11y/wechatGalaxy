import sqlite3
import os
import json
import sys

# 1. 初始化路径
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    # 2. 获取数据库路径
    json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
    with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
    from wxManager.decrypt import get_wx_info
    wx_infos = get_wx_info.read_info(version_list)
    user_info = wx_infos[0]
    
    home_dir = os.path.expanduser("~")
    sns_db_path = os.path.join(home_dir, ".client-radar", "decrypted", user_info.get('wxid'), "Sns.db")
    
    print(f"✅ 正在读取数据库: {sns_db_path}")
    conn = sqlite3.connect(sns_db_path)
    cursor = conn.cursor()

    # 3. 目标 FeedId (你提供的那个)
    # 注意：在 SQL 里，大整数有时候需要作为字符串查询，有时候作为数字
    target_id_str = "-3632670000990055880"
    target_id_int = -3632670000990055880

    print(f"\n🔍 正在查询 ID: {target_id_str}")

    # 4. 获取列名结构
    table_name = "CommentV20"
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns_info = cursor.fetchall()
    col_names = [col[1] for col in columns_info]
    print(f"📋 表结构 ({table_name}): {col_names}")

    # 5. 查询所有相关行 (不做任何过滤)
    sql = f"SELECT * FROM {table_name} WHERE FeedId=?"
    
    # 尝试用字符串查
    cursor.execute(sql, (target_id_str,))
    rows_str = cursor.fetchall()
    
    # 尝试用数字查
    cursor.execute(sql, (target_id_int,))
    rows_int = cursor.fetchall()

    rows = rows_str if rows_str else rows_int
    print(f"📊 找到 {len(rows)} 条原始互动记录:\n")

    # 6. 打印每一行详情
    for i, row in enumerate(rows):
        print(f"--- 记录 #{i+1} ---")
        # 把列名和值对应起来打印
        for col_name, val in zip(col_names, row):
            # 如果是类型，重点标记
            prefix = "🔴 " if "Type" in col_name else "   "
            # 如果是内容，截取一下防止刷屏
            val_str = str(val)
            if len(val_str) > 50: val_str = val_str[:50] + "..."
            print(f"{prefix}{col_name}: {val_str}")
        print("")

    conn.close()

except Exception as e:
    import traceback
    traceback.print_exc()
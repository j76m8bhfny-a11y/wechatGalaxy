import sqlite3
import os
import json
import sys

# 1. 自动寻找 Sns.db (借用之前的逻辑)
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info
    # 读取配置
    json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
    with open(json_path, "r", encoding="utf-8") as f: version_list = json.load(f)
    wx_infos = get_wx_info.read_info(version_list)
    user_info = wx_infos[0]
    wxid = user_info.get('wxid')
    
    # 定位已解密的 Sns.db
    home_dir = os.path.expanduser("~")
    sns_db_path = os.path.join(home_dir, ".client-radar", "decrypted", wxid, "Sns.db")
    
    if not os.path.exists(sns_db_path):
        print(f"❌ 找不到解密后的数据库: {sns_db_path}")
        print("请先运行一次 auto_bridge.py 进行解密！")
        sys.exit(1)
        
    print(f"✅ 正在诊断数据库: {sns_db_path}")
    
    conn = sqlite3.connect(sns_db_path)
    cursor = conn.cursor()
    
    print("\n" + "="*50)
    print("🔍 步骤 1: 检查 SnsComment 表是否存在")
    print("="*50)
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='SnsComment'")
    if not cursor.fetchone():
        print("❌ 致命错误: 数据库里竟然没有 'SnsComment' 表！")
        # 可能是表名变了，打印所有表名
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print("所有表名:", [r[0] for r in cursor.fetchall()])
        sys.exit(1)
    else:
        print("✅ SnsComment 表存在。")

    print("\n" + "="*50)
    print("🔍 步骤 2: 检查 SnsComment 表的列名 (Columns)")
    print("="*50)
    
    cursor.execute("PRAGMA table_info(SnsComment)")
    columns = cursor.fetchall()
    col_names = [col[1] for col in columns]
    print(f"列名列表: {col_names}")
    
    if "ReplyUserName" not in col_names:
        print("⚠️ 警告: 表里没有 'ReplyUserName' 列。之前的代码可能因此崩溃了。")
    else:
        print("✅ 包含 'ReplyUserName' 列。")

    print("\n" + "="*50)
    print("🔍 步骤 3: 数据采样对比 (核心步骤)")
    print("="*50)
    
    # 3.1 取一条朋友圈的 ID
    # 先找表名
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [r[0] for r in cursor.fetchall()]
    main_table = "FeedsV20" if "FeedsV20" in tables else "SnsInfo"
    print(f"朋友圈主表是: {main_table}")
    
    # 取 ID 列名
    cursor.execute(f"PRAGMA table_info({main_table})")
    cols = [r[1] for r in cursor.fetchall()]
    id_col = "FeedId" if "FeedId" in cols else "SnsId"
    
    # 查一条数据
    print(f"正在查询 {main_table} 的前 3 条 ID...")
    cursor.execute(f"SELECT {id_col} FROM {main_table} LIMIT 3")
    feed_ids = cursor.fetchall()
    
    for (fid,) in feed_ids:
        print(f"\n--- 检查朋友圈 ID: {fid} (类型: {type(fid)}) ---")
        
        # 3.2 尝试去 SnsComment 里找对应的评论
        # 尝试方式 A: 直接数字匹配
        cursor.execute(f"SELECT count(*) FROM SnsComment WHERE FeedId=?", (fid,))
        count_num = cursor.fetchone()[0]
        
        # 尝试方式 B: 转字符串匹配
        cursor.execute(f"SELECT count(*) FROM SnsComment WHERE FeedId=?", (str(fid),))
        count_str = cursor.fetchone()[0]
        
        print(f"  > 使用 数字 ID 查询，找到 {count_num} 条互动")
        print(f"  > 使用 字符串 ID 查询，找到 {count_str} 条互动")
        
        if count_num > 0 or count_str > 0:
            print("  ✅ 成功关联！说明 ID 匹配是没问题的。")
            # 打印一条具体的评论看看
            cursor.execute(f"SELECT * FROM SnsComment WHERE FeedId=? LIMIT 1", (fid,))
            row = cursor.fetchone()
            print(f"  > 评论数据样本: {row}")
        else:
            print("  ❌ 这条朋友圈没有互动，或者 ID 匹配失败。")

    print("\n" + "="*50)
    print("🔍 步骤 4: 检查是否有任何评论数据")
    print("="*50)
    cursor.execute("SELECT * FROM SnsComment LIMIT 1")
    any_row = cursor.fetchone()
    if any_row:
        print(f"✅ 数据库里确实有评论数据，样本: {any_row}")
    else:
        print("❌ SnsComment 表是空的！(这就是为什么你看不到了)")

    conn.close()

except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"\n❌ 发生错误: {e}")
    input("按回车键退出...")
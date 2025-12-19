import os
import time
import json
from datetime import datetime

# 引用核心模块获取基础路径
try:
    from wxManager.decrypt.get_wx_info import read_info
except ImportError:
    print("❌ 缺少依赖，请确保 wxManager 在当前目录下。")
    exit(1)

def get_file_info(path):
    """获取文件的最后修改时间"""
    if not os.path.exists(path):
        return None
    timestamp = os.path.getmtime(path)
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def main():
    print("🕵️‍♂️ 正在寻找真正活跃的 Sns.db (朋友圈数据库)...")
    
    # 1. 获取当前登录账号的理论路径
    version_path = os.path.join("wxManager", "decrypt", "version_list.json")
    with open(version_path, "r", encoding="utf-8") as f:
        version_dict = json.load(f)
    
    wx_infos = read_info(version_dict)
    if not wx_infos:
        print("❌ 未检测到登录账号，请保持微信运行。")
        return

    current_user = wx_infos[0]
    current_wx_dir = current_user.get('wx_dir', '')
    
    print(f"\n👤 当前登录检测到的路径: {current_wx_dir}")
    
    # 2. 扫描该路径下的 Sns.db
    target_files = [
        os.path.join(current_wx_dir, "Sns.db"),
        os.path.join(current_wx_dir, "Msg", "Sns.db"),
    ]
    
    print("-" * 50)
    print("📂 检查当前账号文件状态:")
    found_active = False
    for f in target_files:
        if os.path.exists(f):
            mtime = get_file_info(f)
            size = os.path.getsize(f) / 1024 / 1024 # MB
            print(f"  📄 文件: {f}")
            print(f"     🕒 最后修改: {mtime} (越接近现在越对)")
            print(f"     📦 大小: {size:.2f} MB")
            found_active = True
        else:
            print(f"  ❌ 不存在: {f}")

    # 3. 如果上面的文件修改时间是很久以前的，说明找错了
    # 我们尝试向上退一级，扫描所有 WeChat Files 下的文件夹
    if "WeChat Files" in current_wx_dir:
        base_dir = os.path.dirname(current_wx_dir)
        print(f"\n🔍 深度扫描 {base_dir} 下的所有账号...")
        
        for name in os.listdir(base_dir):
            user_dir = os.path.join(base_dir, name)
            if os.path.isdir(user_dir) and "wxid_" in name:
                # 检查这个账号下的 Sns.db
                potential_sns = [
                    os.path.join(user_dir, "Sns.db"),
                    os.path.join(user_dir, "Msg", "Sns.db")
                ]
                for p in potential_sns:
                    if os.path.exists(p):
                        mtime = get_file_info(p)
                        print(f"  👤 账号目录: {name}")
                        print(f"     📄 {p}")
                        print(f"     🕒 修改时间: {mtime} <--- 看看是不是这个？")
                        print("-" * 30)

if __name__ == "__main__":
    main()
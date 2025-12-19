import os
import sys

# 引用核心模块
try:
    # 1. 导入获取微信信息的函数 (根据你的文件列表，文件名应该是 get_wx_info.py)
    from wxManager.decrypt.get_wx_info import read_info
    
    # 2. 导入解密函数 (这是这次修正的重点，不再导入 DecryptManager)
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
    
    # 3. 导入朋友圈读取类
    from wxManager.db_v3.sns import Sns
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保 verify.py 和 wxManager 文件夹在同一级目录下。")
    print("且 wxManager 目录下有 __init__.py 文件（哪怕是空的）。")
    sys.exit(1)

def main():
    print("🚀 开始验证核心功能 (修正版)...")

    # --- 第一步：获取微信信息和密钥 ---
    print("\n[1/3] 正在获取微信密钥...")
    # 这里指向你的 version_list.json，确保它存在
    version_path = os.path.join("wxManager", "decrypt", "version_list.json")
    
    try:
        # read_info 可能返回列表，我们需要取第一个登录的账号
        # 参数 True/False 通常代表是否扫描内存，False 代表只读取本地配置(可能读不到key)，True 代表扫内存
        # 建议先试 True，如果报错再改 False
        wx_infos = read_info(version_path, True) 
        
        if not wx_infos:
            print("⚠️ 未检测到运行中的微信，请先登录 PC 微信！")
            return
        
        user_info = wx_infos[0]
        wx_key = user_info.get('key')
        wx_dir = user_info.get('wx_dir')
        
        if not wx_key:
            print("❌ 获取到了微信路径，但没有获取到密钥(Key)。请确保微信已登录。")
            return

        print(f"✅ 成功获取信息！")
        print(f"   用户: {user_info.get('name', '未知')}")
        print(f"   路径: {wx_dir}")
        print(f"   密钥(前6位): {wx_key[:6]}...")
        
    except Exception as e:
        print(f"❌ 获取密钥阶段出错: {e}")
        import traceback
        traceback.print_exc()
        return

    # --- 第二步：解密朋友圈数据库 ---
    print("\n[2/3] 正在解密 Sns.db ...")
    output_dir = os.path.abspath("./decrypted_db")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 构造源文件路径：朋友圈数据通常在 wx_dir 下的 Sns.db 或者 Msg/Sns.db
    # 我们先尝试找一下文件在哪里
    possible_sns_paths = [
        os.path.join(wx_dir, "Sns.db"),         # 常见位置 1
        os.path.join(wx_dir, "Msg", "Sns.db"),  # 常见位置 2
        os.path.join(wx_dir, "SnsMicroMsg.db")  # 旧版本位置
    ]
    
    src_sns_path = None
    for p in possible_sns_paths:
        if os.path.exists(p):
            src_sns_path = p
            break
            
    if not src_sns_path:
        print(f"❌ 在 {wx_dir} 下没找到 Sns.db 文件。你的微信可能没缓存过朋友圈？")
        return

    dst_sns_path = os.path.join(output_dir, "Sns.db")

    try:
        # 🟢 修正点：直接调用函数，传入 (key, 源路径, 目标路径)
        success, msg = decrypt_db_file_v3(wx_key, src_sns_path, dst_sns_path)
        
        if success:
            print(f"✅ 解密成功！文件已生成: {dst_sns_path}")
        else:
            print(f"❌ 解密函数返回失败: {msg}")
            return
            
    except Exception as e:
        print(f"❌ 解密过程抛出异常: {e}")
        traceback.print_exc()
        return

    # --- 第三步：读取数据 ---
    print("\n[3/3] 读取朋友圈数据...")
    try:
        sns = Sns()
        # 初始化数据库连接
        sns.init_database(output_dir)
        
        if not sns.open_flag:
            print("❌ 数据库打开失败，可能是解密后的文件已损坏或路径不对。")
            return

        # 获取数据
        feeds = sns.get_feeds()
        
        if feeds:
            print(f"🎉 验证大成功！读取到 {len(feeds)} 条朋友圈。")
            print("-" * 30)
            first_item = feeds[0]
            # 根据 sns.py 的 SQL: select FeedId, CreateTime, ... Content
            print(f"时间: {first_item[2]}") 
            # item[7] 是 Content (XML)，我们截取一点看看
            xml_content = first_item[7]
            print(f"内容预览: {xml_content[:60]}...") 
        else:
            print("⚠️ 验证成功，但数据库是空的（可能是你电脑上没点开过朋友圈）。")
            
    except Exception as e:
        print(f"❌ 读取阶段出错: {e}")
        traceback.print_exc()
    finally:
        if 'sns' in locals():
            sns.close()

if __name__ == "__main__":
    main()
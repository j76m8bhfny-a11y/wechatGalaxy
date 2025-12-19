import os
import sys
import json
import traceback

# 引用核心模块
try:
    from wxManager.decrypt.get_wx_info import read_info
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
    from wxManager.db_v3.sns import Sns
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保 verify.py 和 wxManager 文件夹在同一级目录下。")
    sys.exit(1)

def main():
    print("🚀 开始验证核心功能 (V2.0 修正版)...")

    # --- 第一步：获取微信信息和密钥 ---
    print("\n[1/3] 正在读取 version_list.json ...")
    version_path = os.path.join("wxManager", "decrypt", "version_list.json")
    
    if not os.path.exists(version_path):
        print(f"❌ 找不到文件: {version_path}")
        return

    # 1. 先把 JSON 读进内存变成字典
    try:
        with open(version_path, "r", encoding="utf-8") as f:
            version_dict = json.load(f)
    except Exception as e:
        print(f"❌ 读取 JSON 配置文件失败: {e}")
        return

    print("✅ 配置加载成功，正在从内存获取微信密钥...")
    
    try:
        # 2. 调用 read_info，只传入字典这一个参数
        wx_infos = read_info(version_dict) 
        
        if not wx_infos:
            print("⚠️ 未检测到运行中的微信，请先登录 PC 微信！")
            return
        
        # 检查是否包含有效信息
        user_info = wx_infos[0]
        
        # 处理可能的错误码
        if user_info.get('errcode') != 200:
            print(f"⚠️ 获取失败: {user_info.get('errmsg')}")
            # 如果是版本不匹配，可能需要更新 version_list.json
            return

        wx_key = user_info.get('key')
        wx_dir = user_info.get('wx_dir')
        
        if not wx_key or wx_key == "None":
            print("❌ 获取到了微信路径，但没有获取到密钥(Key)。请确保微信已登录。")
            return

        print(f"✅ 成功获取信息！")
        print(f"   用户: {user_info.get('name', '未知')}")
        print(f"   路径: {wx_dir}")
        print(f"   密钥(前6位): {wx_key[:6]}...")
        
    except Exception as e:
        print(f"❌ 获取密钥阶段出错: {e}")
        traceback.print_exc()
        return

    # --- 第二步：解密朋友圈数据库 ---
    print("\n[2/3] 正在解密 Sns.db ...")
    output_dir = os.path.abspath("./decrypted_db")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # 自动寻找 Sns.db
    possible_sns_paths = [
        os.path.join(wx_dir, "Sns.db"),         
        os.path.join(wx_dir, "Msg", "Sns.db"),
        os.path.join(wx_dir, "SnsMicroMsg.db") 
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
        # 调用解密函数
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
        sns.init_database(output_dir)
        
        if not sns.open_flag:
            print("❌ 数据库打开失败，可能是解密后的文件已损坏或路径不对。")
            return

        feeds = sns.get_feeds()
        
        if feeds:
            print(f"🎉 验证大成功！读取到 {len(feeds)} 条朋友圈。")
            print("-" * 30)
            print(f"时间: {feeds[0][2]}")
            # XML 内容可能会很长，只打印前100个字符
            xml_preview = str(feeds[0][7])[:100]
            print(f"内容预览: {xml_preview}...") 
        else:
            print("⚠️ 验证成功，但数据库是空的。")
            
    except Exception as e:
        print(f"❌ 读取阶段出错: {e}")
        traceback.print_exc()
    finally:
        if 'sns' in locals():
            sns.close()

if __name__ == "__main__":
    main()
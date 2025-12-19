import os
import sys
import json
import traceback

# 引用核心模块
try:
    from wxManager.decrypt.get_wx_info import read_info
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
    
    # 【关键修改 1】这里不仅导入类，还导入整个模块，方便修改全局变量
    import wxManager.db_v3.sns as sns_module 
    from wxManager.db_v3.sns import Sns
    
except ImportError as e:
    print(f"❌ 导入失败: {e}")
    print("请确保 verify.py 和 wxManager 文件夹在同一级目录下。")
    sys.exit(1)

def main():
    print("🚀 开始验证核心功能 (V3.0 路径修复版)...")

    # --- 第一步：获取微信信息和密钥 ---
    print("\n[1/3] 正在读取配置并获取密钥...")
    version_path = os.path.join("wxManager", "decrypt", "version_list.json")
    
    if not os.path.exists(version_path):
        print(f"❌ 找不到文件: {version_path}")
        return

    try:
        with open(version_path, "r", encoding="utf-8") as f:
            version_dict = json.load(f)
        
        # 获取信息
        wx_infos = read_info(version_dict) 
        if not wx_infos:
            print("⚠️ 未检测到运行中的微信，请先登录 PC 微信！")
            return
        
        user_info = wx_infos[0]
        if user_info.get('errcode') != 200:
            print(f"⚠️ 获取失败: {user_info.get('errmsg')}")
            return

        wx_key = user_info.get('key')
        wx_dir = user_info.get('wx_dir')
        
        if not wx_key or wx_key == "None":
            print("❌ 未获取到密钥，请检查微信登录状态。")
            return

        print(f"✅ 成功获取信息！用户: {user_info.get('name')} | 密钥: {wx_key[:6]}...")
        
    except Exception as e:
        print(f"❌ 第一步出错: {e}")
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
        print(f"❌ 在 {wx_dir} 下没找到 Sns.db。")
        return

    dst_sns_path = os.path.join(output_dir, "Sns.db")

    try:
        # 解密
        success, msg = decrypt_db_file_v3(wx_key, src_sns_path, dst_sns_path)
        if success:
            print(f"✅ 解密成功！文件已生成: {dst_sns_path}")
        else:
            print(f"❌ 解密失败: {msg}")
            return
    except Exception as e:
        print(f"❌ 解密过程异常: {e}")
        traceback.print_exc()
        return

    # --- 第三步：读取数据 (核心修改部分) ---
    print("\n[3/3] 读取朋友圈数据...")
    try:
        # 【关键修改 2】在实例化之前，先强制修改模块里的全局变量 db_path
        # 这样 Sns() 初始化时就不会去连默认路径，而是连我们解密好的路径
        sns_module.db_path = dst_sns_path
        
        # 现在实例化，它会自动连接上面设置好的路径
        sns = Sns()
        
        if not sns.open_flag:
            # 双重保险：如果自动连接失败，手动再连一次
            sns.init_database(output_dir)

        if not sns.open_flag:
            print("❌ 数据库连接失败。")
            return

        # 获取数据
        feeds = sns.get_feeds()
        
        if feeds:
            print(f"🎉 验证大成功！读取到 {len(feeds)} 条朋友圈。")
            print("-" * 30)
            
            # 打印第一条数据
            first_feed = feeds[0]
            # 数据结构: FeedId, CreateTime, StrTime, Type, UserName, Status, StringId, Content
            print(f"📅 时间: {first_feed[2]}")
            
            # 尝试简单的 XML 解析预览
            try:
                import xmltodict
                content_dict = xmltodict.parse(first_feed[7])
                # 尝试提取文字内容，不同类型结构可能不同，这里仅作演示
                timeline_obj = content_dict.get('TimelineObject', {})
                text_content = timeline_obj.get('contentDesc', '无文本')
                print(f"📝 内容: {text_content}")
            except:
                print(f"📝 原始内容: {str(first_feed[7])[:60]}...")
                
        else:
            print("⚠️ 数据库读取成功，但里面没有数据（空表）。")
            
    except Exception as e:
        print(f"❌ 读取阶段出错: {e}")
        traceback.print_exc()
    finally:
        if 'sns' in locals() and hasattr(sns, 'close'):
            sns.close()

if __name__ == "__main__":
    main()
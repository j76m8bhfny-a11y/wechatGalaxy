import os
import sys
import json
import shutil

# 确保能引用到同级目录下的 wxManager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info, decrypt_dat
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"Import Error: {e}"}))
    sys.exit(1)

def main():
    try:
        # 1. 尝试获取微信运行信息 (Key 和 路径)
        # 注意：get_wx_info.read_info() 返回的是一个列表
        wx_infos = get_wx_info.read_info()
        
        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未检测到运行中的微信，请先登录PC微信"}))
            return

        # 默认处理第一个登录的账号
        user_info = wx_infos[0]
        key = user_info.get('key')
        wxid = user_info.get('wxid')
        db_path = user_info.get('db_path') # 这里通常是 .../Msg 目录

        if not key or not db_path:
            print(json.dumps({"status": "error", "message": "获取微信密钥或路径失败"}))
            return

        # 2. 准备输出目录 (解密后的文件放哪里?)
        # 我们放在用户目录下的 .client-radar/decrypted/{wxid} 中
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".client-radar", "decrypted", wxid)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        target_micro = os.path.join(output_dir, "MicroMsg.db")
        target_sns = os.path.join(output_dir, "Sns.db")

        # 3. 开始解密 MicroMsg.db
        source_micro = os.path.join(db_path, "MicroMsg.db")
        if os.path.exists(source_micro):
            # 调用 wxManager 的解密逻辑
            # 注意：decrypt_db 函数可能需要根据你的 wxManager 具体版本调整参数
            # 假设 decrypt_dat.decrypt_db(key, input, output)
            decrypt_dat.decrypt_db(key, source_micro, target_micro)
        else:
            print(json.dumps({"status": "error", "message": "找不到 MicroMsg.db 原文件"}))
            return

        # 4. 开始解密 Sns.db (朋友圈)
        # Sns.db 通常在 Msg 目录的同级或上级，或者就在 Msg 里，这里尝试查找
        # 常见路径结构: .../wxid_xxx/Msg/MicroMsg.db  而 .../wxid_xxx/Sns/Sns.db
        # 所以我们需要往上退一级找 Sns 文件夹
        parent_dir = os.path.dirname(db_path) 
        source_sns = os.path.join(parent_dir, "Sns", "Sns.db")
        
        # 如果不在那里，也可能在 Msg 目录下
        if not os.path.exists(source_sns):
            source_sns = os.path.join(db_path, "Sns.db")

        if os.path.exists(source_sns):
            decrypt_dat.decrypt_db(key, source_sns, target_sns)
        else:
            # 如果找不到 SNS 也没关系，我们先返回 MicroMsg 成功的状态
            target_sns = "" 

        # 5. ✅ 成功！输出 JSON 给 Rust
        result = {
            "status": "success",
            "wxid": wxid,
            "nickname": user_info.get('nickname', ''),
            "micro_db_path": target_micro,
            "sns_db_path": target_sns
        }
        # 这里的 print 是给主程序看的，不要删除
        print(json.dumps(result))

    except Exception as e:
        # 捕获所有异常并输出 JSON
        print(json.dumps({"status": "error", "message": str(e)}))

if __name__ == "__main__":
    main()
import os
import sys
import json
import shutil

# 1. 确保能引用到同级目录下的 wxManager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info, decrypt_dat
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"Import Error: {e}"}))
    sys.exit(1)

def main():
    try:
        # 2. 核心修正：加载 version_list.json
        # 这个文件在 wxManager/decrypt/version_list.json
        json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
        
        if not os.path.exists(json_path):
            print(json.dumps({"status": "error", "message": f"缺失配置文件: {json_path}"}))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            version_list = json.load(f)

        # 3. 获取微信运行信息 (传入 version_list)
        wx_infos = get_wx_info.read_info(version_list) # 👈 修正点：传入参数
        
        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未检测到运行中的微信，请先登录PC微信"}))
            return

        # 默认处理第一个登录的账号
        user_info = wx_infos[0]
        
        # 检查是否成功获取 Key
        if user_info.get('errcode') != 200:
             msg = user_info.get('errmsg', '获取微信Key失败')
             print(json.dumps({"status": "error", "message": msg}))
             return

        key = user_info.get('key')
        wxid = user_info.get('wxid')
        # 注意：get_wx_info 返回的可能是 'wx_dir' 而不是 'db_path'，根据你的代码逻辑调整
        # 通常 wx_dir 是 .../WeChat Files/wxid_xxx/
        # 而数据库在 wx_dir/Msg/ 下
        wx_dir = user_info.get('wx_dir')
        
        if not key or not wx_dir:
            print(json.dumps({"status": "error", "message": "无法获取Key或微信数据目录"}))
            return

        db_base_path = os.path.join(wx_dir, "Msg") 

        # 4. 准备输出目录
        home_dir = os.path.expanduser("~")
        output_dir = os.path.join(home_dir, ".client-radar", "decrypted", wxid)
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        target_micro = os.path.join(output_dir, "MicroMsg.db")
        target_sns = os.path.join(output_dir, "Sns.db")

        # 5. 开始解密 MicroMsg.db
        source_micro = os.path.join(db_base_path, "MicroMsg.db")
        
        if os.path.exists(source_micro):
            decrypt_dat.decrypt_db(key, source_micro, target_micro)
        else:
            print(json.dumps({"status": "error", "message": f"找不到源文件: {source_micro}"}))
            return

        # 6. 开始解密 Sns.db (尝试多个位置)
        # Sns.db 有时在 Msg 目录，有时在 Msg 同级的 Sns 目录
        possible_sns_paths = [
            os.path.join(db_base_path, "Sns.db"),                 # Msg/Sns.db
            os.path.join(os.path.dirname(db_base_path), "Sns", "Sns.db") # WeChat Files/wxid/Sns/Sns.db
        ]
        
        found_sns = False
        for src in possible_sns_paths:
            if os.path.exists(src):
                decrypt_dat.decrypt_db(key, src, target_sns)
                found_sns = True
                break
        
        if not found_sns:
            target_sns = "" # 没找到就不返回路径

        # 7. ✅ 成功！输出 JSON
        result = {
            "status": "success",
            "wxid": wxid,
            "nickname": user_info.get('name', ''),
            "micro_db_path": target_micro,
            "sns_db_path": target_sns
        }
        print(json.dumps(result))

    except Exception as e:
        # 捕获所有异常并输出 JSON
        import traceback
        err_msg = f"{str(e)} | {traceback.format_exc()}"
        print(json.dumps({"status": "error", "message": err_msg}))

if __name__ == "__main__":
    main()
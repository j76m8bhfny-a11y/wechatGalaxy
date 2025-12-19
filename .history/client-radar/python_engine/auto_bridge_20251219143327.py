import os
import sys
import json

# 1. 确保能引用到同级目录下的 wxManager
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from wxManager.decrypt import get_wx_info
    # 📝 修正点1：引入正确的数据库解密模块 (v3对应普通PC微信)
    from wxManager.decrypt.decrypt_v3 import decrypt_db_file_v3
except ImportError as e:
    print(json.dumps({"status": "error", "message": f"Import Error: {e}"}))
    sys.exit(1)

def main():
    try:
        # 2. 加载 version_list.json
        json_path = os.path.join(current_dir, "wxManager", "decrypt", "version_list.json")
        
        if not os.path.exists(json_path):
            print(json.dumps({"status": "error", "message": f"缺失配置文件: {json_path}"}))
            return

        with open(json_path, "r", encoding="utf-8") as f:
            version_list = json.load(f)

        # 3. 获取微信运行信息
        # 注意：get_wx_info 可能会抛出异常，最好捕获一下
        try:
            wx_infos = get_wx_info.read_info(version_list)
        except Exception as e:
            print(json.dumps({"status": "error", "message": f"读取微信信息失败: {str(e)}"}))
            return
        
        if not wx_infos:
            print(json.dumps({"status": "error", "message": "未检测到运行中的微信，请先登录PC微信"}))
            return

        # 默认处理第一个登录的账号
        user_info = wx_infos[0]
        
        if user_info.get('errcode') != 200:
             msg = user_info.get('errmsg', '获取微信Key失败')
             print(json.dumps({"status": "error", "message": msg}))
             return

        key = user_info.get('key')
        wxid = user_info.get('wxid')
        wx_dir = user_info.get('wx_dir') # .../WeChat Files/wxid_xxx/
        
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

        # 5. 解密 MicroMsg.db
        source_micro = os.path.join(db_base_path, "MicroMsg.db")
        
        if os.path.exists(source_micro):
            # 📝 修正点2：调用 v3 解密函数
            # 函数签名: decrypt_db_file_v3(key, db_path, out_path)
            # 返回值: (True/False, msg)
            success, msg = decrypt_db_file_v3(key, source_micro, target_micro)
            if not success:
                print(json.dumps({"status": "error", "message": f"MicroMsg解密失败: {msg}"}))
                return
        else:
            print(json.dumps({"status": "error", "message": f"找不到源文件: {source_micro}"}))
            return

        # 6. 解密 Sns.db
        possible_sns_paths = [
            os.path.join(db_base_path, "Sns.db"),
            os.path.join(os.path.dirname(db_base_path), "Sns", "Sns.db")
        ]
        
        sns_decrypted = False
        for src in possible_sns_paths:
            if os.path.exists(src):
                success, msg = decrypt_db_file_v3(key, src, target_sns)
                if success:
                    sns_decrypted = True
                    break
        
        if not sns_decrypted:
            target_sns = ""

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
        import traceback
        err_msg = f"{str(e)} | {traceback.format_exc()}"
        print(json.dumps({"status": "error", "message": err_msg}))

if __name__ == "__main__":
    main()
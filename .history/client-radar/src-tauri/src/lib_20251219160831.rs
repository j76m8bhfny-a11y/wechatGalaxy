use tauri::Manager;
use rusqlite::{Connection, Result};
use serde::{Serialize, Deserialize};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

// ==========================================
// 1. 数据结构定义
// ==========================================

// 通讯录联系人结构
#[derive(Serialize, Deserialize, Debug)]
struct ContactItem {
    username: String, // wxid
    remark: String,   // 备注
    nickname: String, // 昵称
}

// 朋友圈原始数据结构
#[derive(Serialize, Deserialize, Debug)]
struct SnsRawItem {
    sns_id: String,     // 朋友圈ID
    create_time: u32,   // 发布时间戳
    content: String,    // XML原始内容
}

// ==========================================
// 2. Tauri 命令定义
// ==========================================

// 🟢 命令1：读取通讯录 (MicroMsg.db)
#[tauri::command]
fn read_contacts_from_db(db_path: String) -> Result<Vec<ContactItem>, String> {
    let conn = Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;

    // SQL: 只查询有效的个人好友 (排除群聊和公众号)
    let mut stmt = conn.prepare(
        "SELECT UserName, Remark, NickName 
         FROM Contact 
         WHERE UserName NOT LIKE '%@chatroom' 
         AND UserName NOT LIKE 'gh_%'
         AND VerifyFlag = 0"
    ).map_err(|e| format!("SQL预处理失败: {}", e))?;

    let contact_iter = stmt.query_map([], |row| {
        Ok(ContactItem {
            username: row.get(0)?,
            remark: row.get(1).unwrap_or_default(),
            nickname: row.get(2).unwrap_or_default(),
        })
    }).map_err(|e| format!("查询失败: {}", e))?;

    let mut contacts = Vec::new();
    for contact in contact_iter {
        if let Ok(c) = contact {
            if !c.username.is_empty() {
                contacts.push(c);
            }
        }
    }

    Ok(contacts)
}

// 🔵 命令2：读取朋友圈 (Sns.db)
#[tauri::command]
fn read_moments_from_db(db_path: String) -> Result<Vec<SnsRawItem>, String> {
    let conn = Connection::open(&db_path).map_err(|e| format!("打开SNS库失败: {}", e))?;

    // SQL: 查询最近的200条朋友圈，且内容不为空
    // 注意：SnsInfo 表有时也叫 SnsInfo2，如果报错提示 no such table，请尝试改为 SnsInfo2
    let mut stmt = conn.prepare(
        "SELECT SnsId, CreateTime, content 
         FROM SnsInfo 
         WHERE content IS NOT NULL AND content != ''
         ORDER BY CreateTime DESC 
         LIMIT 200"
    ).map_err(|e| format!("SNS SQL预处理失败: {}", e))?;

    let iter = stmt.query_map([], |row| {
        // content 字段通常是 BLOB 类型，需要转成 String (忽略非法字符)
        let content_blob: Vec<u8> = row.get(2).unwrap_or_default();
        let content_str = String::from_utf8_lossy(&content_blob).to_string();

        // SnsId 可能是大整数或字符串，统一转为字符串处理
        let id_val: rusqlite::types::Value = row.get(0)?;
        let id_str = match id_val {
            rusqlite::types::Value::Integer(i) => i.to_string(),
            rusqlite::types::Value::Text(s) => s,
            _ => "0".to_string(),
        };

        Ok(SnsRawItem {
            sns_id: id_str,
            create_time: row.get(1).unwrap_or_default(),
            content: content_str,
        })
    }).map_err(|e| format!("SNS 查询失败: {}", e))?;

    let mut moments = Vec::new();
    for item in iter {
        if let Ok(m) = item {
            // 简单过滤：只有以 < 开头的才像是 XML，排除乱码
            if m.content.trim().starts_with('<') {
                moments.push(m);
            }
        }
    }

    Ok(moments)
}

// 🚀 命令3：自动调用 Python 脚本解密微信
#[tauri::command]
async fn auto_decrypt_wechat(app: tauri::AppHandle) -> Result<String, String> {
    // 调用 Sidecar (decrypt-engine)
    // 注意：Tauri 会自动寻找带架构后缀的文件 (如 decrypt-engine-x86_64-pc-windows-msvc.exe)
    let sidecar_command = app.shell().sidecar("decrypt-engine").map_err(|e| e.to_string())?;
    
    // 执行并获取输出流
    let (mut rx, _child) = sidecar_command.spawn().map_err(|e| e.to_string())?;
    
    let mut json_output = String::new();

    // 实时读取 stdout 输出
    while let Some(event) = rx.recv().await {
        if let CommandEvent::Stdout(line) = event {
            let line_str = String::from_utf8_lossy(&line);
            json_output.push_str(&line_str);
        }
    }

    // 返回 JSON 字符串给前端解析
    Ok(json_output)
}

// ==========================================
// 3. 程序入口
// ==========================================

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // 注册插件
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        // 注册所有命令
        .invoke_handler(tauri::generate_handler![
            read_contacts_from_db,
            read_moments_from_db,
            auto_decrypt_wechat
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
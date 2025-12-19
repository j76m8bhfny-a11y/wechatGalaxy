use tauri::Manager;
use rusqlite::{Connection, Result};
use serde::{Serialize, Deserialize};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

// 1. 定义数据结构，对应前端需要的格式
#[derive(Serialize, Deserialize, Debug)]
struct ContactItem {
    username: String, // wxid
    remark: String,   // 备注
    nickname: String, // 昵称
}

// 2. 定义 Tauri 命令：读取数据库
#[tauri::command]
fn read_contacts_from_db(db_path: String) -> Result<Vec<ContactItem>, String> {
    // 尝试连接数据库
    let conn = Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;

    // 准备 SQL：只查真实好友 (排除群聊、公众号等)
    // VerifyFlag = 0 通常代表个人号
    // UserName 不包含 @chatroom 代表不是群
    let mut stmt = conn.prepare(
        "SELECT UserName, Remark, NickName 
         FROM Contact 
         WHERE UserName NOT LIKE '%@chatroom' 
         AND UserName NOT LIKE 'gh_%'
         AND VerifyFlag = 0"
    ).map_err(|e| format!("SQL预处理失败: {}", e))?;

    // 执行查询并映射结果
    let contact_iter = stmt.query_map([], |row| {
        Ok(ContactItem {
            username: row.get(0)?,
            remark: row.get(1).unwrap_or_default(),   // 备注可能为空
            nickname: row.get(2).unwrap_or_default(), // 昵称可能为空
        })
    }).map_err(|e| format!("查询失败: {}", e))?;

    // 收集结果
    let mut contacts = Vec::new();
    for contact in contact_iter {
        if let Ok(c) = contact {
            // 简单过滤：如果没有备注也没有昵称，或者是系统号，跳过
            if !c.username.is_empty() {
                contacts.push(c);
            }
        }
    }

    Ok(contacts)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        // 👇 3. 别忘了在这里注册命令！
        .invoke_handler(tauri::generate_handler![read_contacts_from_db])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
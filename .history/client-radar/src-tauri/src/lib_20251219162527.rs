use tauri::Manager;
use rusqlite::{Connection, Result};
use serde::{Serialize, Deserialize};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

// ==========================================
// 1. 数据结构定义
// ==========================================

#[derive(Serialize, Deserialize, Debug)]
struct ContactItem {
    username: String,
    remark: String,
    nickname: String,
}

#[derive(Serialize, Deserialize, Debug)]
struct SnsRawItem {
    sns_id: String,
    create_time: u32,
    content: String,
}

// ==========================================
// 2. 核心逻辑
// ==========================================

#[tauri::command]
fn read_contacts_from_db(db_path: String) -> Result<Vec<ContactItem>, String> {
    let conn = Connection::open(&db_path).map_err(|e| format!("打开数据库失败: {}", e))?;

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

// 🔵 增强修复版：智能探测 SnsInfo 表
#[tauri::command]
fn read_moments_from_db(db_path: String) -> Result<Vec<SnsRawItem>, String> {
    let conn = Connection::open(&db_path).map_err(|e| format!("打开SNS库失败: {}", e))?;

    // 1. 🔍 获取数据库中所有的表名
    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table'").map_err(|e| format!("查询系统表失败: {}", e))?;
    let table_names: Vec<String> = stmt.query_map([], |row| row.get(0))
        .map_err(|e| format!("遍历表名失败: {}", e))?
        .filter_map(Result::ok)
        .collect();

    // 2. 🕵️‍♀️ 智能匹配：寻找包含 "SnsInfo" 的表 (忽略大小写)
    // 优先找完全匹配 SnsInfo 或 SnsInfo2，如果没有，找任何包含 snsinfo 的
    let target_table = table_names.iter()
        .find(|n| n.eq_ignore_ascii_case("SnsInfo") || n.eq_ignore_ascii_case("SnsInfo2"))
        .or_else(|| table_names.iter().find(|n| n.to_lowercase().contains("snsinfo")))
        .cloned();

    // 3. 检查结果
    let table_name = match target_table {
        Some(name) => name,
        None => {
            // ❌ 如果没找到，返回详细报错，把现有表名打印出来方便排查
            return Err(format!("未找到朋友圈表. 当前库中包含的表: {:?}", table_names));
        }
    };

    // 4. 动态构建 SQL
    let sql = format!(
        "SELECT SnsId, CreateTime, content 
         FROM {} 
         WHERE content IS NOT NULL AND content != ''
         ORDER BY CreateTime DESC 
         LIMIT 200", 
        table_name 
    );

    let mut stmt = conn.prepare(&sql).map_err(|e| format!("SQL预处理失败 (表名: {}): {}", table_name, e))?;

    // 5. 执行查询
    let iter = stmt.query_map([], |row| {
        let content_blob: Vec<u8> = row.get(2).unwrap_or_default();
        let content_str = String::from_utf8_lossy(&content_blob).to_string();

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
            if m.content.trim().starts_with('<') {
                moments.push(m);
            }
        }
    }

    Ok(moments)
}

#[tauri::command]
async fn auto_decrypt_wechat(app: tauri::AppHandle) -> Result<String, String> {
    let sidecar_command = app.shell().sidecar("decrypt-engine").map_err(|e| e.to_string())?;
    let (mut rx, _child) = sidecar_command.spawn().map_err(|e| e.to_string())?;
    
    let mut json_output = String::new();
    while let Some(event) = rx.recv().await {
        if let CommandEvent::Stdout(line) = event {
            let line_str = String::from_utf8_lossy(&line);
            json_output.push_str(&line_str);
        }
    }
    Ok(json_output)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            read_contacts_from_db,
            read_moments_from_db,
            auto_decrypt_wechat
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
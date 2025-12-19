use tauri::Manager;
use rusqlite::{Connection, Result};
use serde::{Serialize, Deserialize};
use tauri_plugin_shell::ShellExt;
use tauri_plugin_shell::process::CommandEvent;

// ==========================================
// 1. 数据结构
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
    content: String, // 这里可能包含乱码，前端去清洗
}

// ==========================================
// 2. 核心功能
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

// 🟢 宽容模式：移除严格过滤，增强列名匹配
#[tauri::command]
fn read_moments_from_db(db_path: String) -> Result<Vec<SnsRawItem>, String> {
    let conn = Connection::open(&db_path).map_err(|e| format!("打开SNS库失败: {}", e))?;

    // 1. 找表名
    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table'").map_err(|e| format!("系统表查询失败: {}", e))?;
    let table_names: Vec<String> = stmt.query_map([], |row| row.get(0))
        .map_err(|e| format!("表名读取失败: {}", e))?
        .filter_map(Result::ok)
        .collect();

    let target_table = table_names.iter()
        .find(|n| n.eq_ignore_ascii_case("FeedsV20"))
        .or_else(|| table_names.iter().find(|n| n.eq_ignore_ascii_case("SnsInfo")))
        .or_else(|| table_names.iter().find(|n| n.eq_ignore_ascii_case("SnsInfo2")))
        .or_else(|| table_names.iter().find(|n| n.to_lowercase().contains("feeds")))
        .or_else(|| table_names.iter().find(|n| n.to_lowercase().contains("snsinfo")))
        .cloned();

    let table_name = match target_table {
        Some(name) => name,
        None => return Err(format!("未找到朋友圈表. 现有表: {:?}", table_names)),
    };

    // 2. 找列名 (新增 objectDesc 支持)
    let sql_columns = format!("PRAGMA table_info({})", table_name);
    let mut stmt_cols = conn.prepare(&sql_columns).map_err(|e| format!("列名探测失败: {}", e))?;
    let columns: Vec<String> = stmt_cols.query_map([], |row| row.get(1))
        .map_err(|e| format!("列名读取失败: {}", e))?
        .filter_map(Result::ok)
        .collect();

    let id_col = columns.iter()
        .find(|c| c.eq_ignore_ascii_case("FeedId") || c.eq_ignore_ascii_case("SnsId"))
        .unwrap_or(&"SnsId".to_string()).to_string();

    let time_col = columns.iter()
        .find(|c| c.eq_ignore_ascii_case("CreateTime") || c.eq_ignore_ascii_case("Timestamp"))
        .unwrap_or(&"CreateTime".to_string()).to_string();

    // 重点：增加 objectDesc 匹配，这是 FeedsV20 常用的内容列
    let content_col = columns.iter()
        .find(|c| c.eq_ignore_ascii_case("Content") || c.eq_ignore_ascii_case("Buffer") || c.eq_ignore_ascii_case("objectDesc"))
        .unwrap_or(&"content".to_string()).to_string();

    // 3. 查询 (移除 content != '' 过滤，防止漏掉被识别为空的二进制)
    let sql = format!(
        "SELECT {}, {}, {} 
         FROM {} 
         WHERE {} IS NOT NULL
         ORDER BY {} DESC 
         LIMIT 300", 
        id_col, time_col, content_col,
        table_name,
        content_col,
        time_col
    );

    let mut stmt = conn.prepare(&sql).map_err(|e| format!("SQL错误: {}", e))?;
    let iter = stmt.query_map([], |row| {
        let content_blob: Vec<u8> = row.get(2).unwrap_or_default();
        // 强制转字符串，即使有乱码也保留，交给前端处理
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
    }).map_err(|e| format!("查询执行失败: {}", e))?;

    let mut moments = Vec::new();
    for item in iter {
        if let Ok(m) = item {
            // ❌ 彻底移除 starts_with('<') 检查
            // 只要内容长度大于 10，我们就认为它可能包含有效信息
            if m.content.len() > 10 {
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
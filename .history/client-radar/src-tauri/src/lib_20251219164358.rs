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
    content: String, 
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

// 🔵 诊断修复版：如果不成功，返回表结构信息
#[tauri::command]
fn read_moments_from_db(db_path: String) -> Result<Vec<SnsRawItem>, String> {
    let conn = Connection::open(&db_path).map_err(|e| format!("打开SNS库失败: {}", e))?;

    // 1. 找表名
    let mut stmt = conn.prepare("SELECT name FROM sqlite_master WHERE type='table'").map_err(|e| format!("系统表查询失败: {}", e))?;
    let table_names: Vec<String> = stmt.query_map([], |row| row.get(0))
        .map_err(|e| format!("表名读取失败: {}", e))?
        .filter_map(Result::ok)
        .collect();

    // 优先找 FeedsV20，其次 SnsInfo
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

    // 2. 找列名 (列出所有列，方便调试)
    let sql_columns = format!("PRAGMA table_info({})", table_name);
    let mut stmt_cols = conn.prepare(&sql_columns).map_err(|e| format!("列名探测失败: {}", e))?;
    let all_columns: Vec<String> = stmt_cols.query_map([], |row| row.get(1))
        .map_err(|e| format!("列名读取失败: {}", e))?
        .filter_map(Result::ok)
        .collect();

    // 3. 智能匹配关键列
    let id_col = all_columns.iter()
        .find(|c| ["FeedId", "SnsId", "Id"].iter().any(|k| c.eq_ignore_ascii_case(k)))
        .unwrap_or(&"rowid".to_string()).to_string(); // 如果找不到ID，就用 rowid

    let time_col = all_columns.iter()
        .find(|c| ["CreateTime", "Timestamp", "Time"].iter().any(|k| c.eq_ignore_ascii_case(k)))
        .unwrap_or(&"0".to_string()).to_string(); // 如果找不到时间，就填0

    // 重点：尝试匹配所有可能的 Content 列名
    let content_col = all_columns.iter()
        .find(|c| ["Content", "Buffer", "objectDesc", "detail", "stringSeq", "xml"].iter().any(|k| c.eq_ignore_ascii_case(k)))
        .cloned();

    // 如果找不到 Content 列，直接报错并把所有列名打印出来给用户看
    if content_col.is_none() {
        return Err(format!("匹配不到内容列！表 [{}] 的所有列名: {:?}", table_name, all_columns));
    }
    let content_col_name = content_col.unwrap();

    // 4. 查询
    let sql = format!(
        "SELECT {}, {}, {} 
         FROM {} 
         WHERE {} IS NOT NULL 
         LIMIT 200", 
        id_col, time_col, content_col_name,
        table_name,
        content_col_name
    );

    let mut stmt = conn.prepare(&sql).map_err(|e| format!("SQL预处理失败: {} | SQL: {}", e, sql))?;
    let iter = stmt.query_map([], |row| {
        let content_blob: Vec<u8> = row.get(2).unwrap_or_default();
        let content_str = String::from_utf8_lossy(&content_blob).to_string();

        let id_val: rusqlite::types::Value = row.get(0)?;
        let id_str = match id_val {
            rusqlite::types::Value::Integer(i) => i.to_string(),
            rusqlite::types::Value::Text(s) => s,
            _ => "0".to_string(),
        };
        
        // 时间处理
        let time_val: rusqlite::types::Value = row.get(1).unwrap_or(rusqlite::types::Value::Integer(0));
        let time_int = match time_val {
            rusqlite::types::Value::Integer(i) => i as u32,
             _ => 0,
        };

        Ok(SnsRawItem {
            sns_id: id_str,
            create_time: time_int,
            content: content_str,
        })
    }).map_err(|e| format!("查询执行失败: {}", e))?;

    let mut moments = Vec::new();
    for item in iter {
        if let Ok(m) = item {
             // 只要有数据就塞进去，不做任何过滤
             moments.push(m);
        }
    }

    // ⚠️ 诊断逻辑：如果结果为空，返回报错信息，告知用户表里是空的或者列选错了
    if moments.is_empty() {
        return Err(format!("读取成功但数据为空。可能表 [{}] 是空的，或者列名 [{}] 不对。所有列: {:?}", table_name, content_col_name, all_columns));
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
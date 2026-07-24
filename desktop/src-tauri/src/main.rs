// AIHouse 桌面端 — 系统托盘 + 监控仪表盘窗口
//
// 功能：
// 1. 系统托盘图标（根据 API 状态内联生成颜色图标）
// 2. 点击托盘图标切换窗口显示/隐藏
// 3. 右键菜单：显示窗口 / 设置 / 退出

use tauri::{
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager, WindowEvent,
};

const API_URL: &str = "http://127.0.0.1:9800/api/status";

/// 根据颜色名生成 32x32 纯色 RGBA 图标
fn make_icon(color: &str) -> Image {
    let (r, g, b) = match color {
        "green"  => (34, 197, 94),
        "blue"   => (59, 130, 246),
        "yellow" => (234, 179, 8),
        "red"    => (239, 68, 68),
        _        => (34, 197, 94),
    };
    let w = 32u8;
    let h = 32u8;
    let mut rgba = Vec::with_capacity((w as usize) * (h as usize) * 4);
    for y in 0..h {
        for x in 0..w {
            let cx = w as f32 / 2.0;
            let cy = h as f32 / 2.0;
            let dist = (((x as f32 - cx).powi(2) + (y as f32 - cy).powi(2)).sqrt()) as u8;
            if dist < 15 {
                rgba.extend_from_slice(&[r, g, b, 255]);
            } else {
                rgba.extend_from_slice(&[0, 0, 0, 0]);
            }
        }
    }
    Image::new_owned(rgba, w.into(), h.into())
}

fn main() {
    tauri::Builder::default()
        .setup(|app| {
            let open_item = MenuItem::with_id(app, "open", "显示窗口", true, None::<&str>)?;
            let settings_item = MenuItem::with_id(app, "settings", "设置", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "退出", true, Some("CmdOrCtrl+Q"))?;
            let menu = Menu::with_items(app, &[&open_item, &settings_item, &quit_item])?;

            TrayIconBuilder::new()
                .icon(make_icon("green"))
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => toggle_window(app),
                    "settings" => {
                        let _ = open::that("/Users/Zhuanz/.aihouse/config.yaml");
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let TrayIconEvent::Click {
                        button: MouseButton::Left,
                        button_state: MouseButtonState::Up,
                        ..
                    } = event
                    {
                        toggle_window(tray.app_handle());
                    }
                })
                .build(app)?;

            // 启动时创建主窗口
            create_main_window(app.handle());

            // 定时更新托盘图标
            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                loop {
                    std::thread::sleep(std::time::Duration::from_secs(10));
                    update_tray_icon(&app_handle);
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

/// 创建主监控窗口
fn create_main_window(app: &tauri::AppHandle) {
    let _window = tauri::WebviewWindowBuilder::new(
        app, "main",
        tauri::WebviewUrl::App("index.html".into()),
    )
    .title("AIHouse")
    .inner_size(720.0, 560.0)
    .min_inner_size(520.0, 420.0)
    .resizable(true)
    .always_on_top(true)
    .decorations(true)
    .build()
    .expect("failed to build main window");
}

/// 切换主窗口显示/隐藏
fn toggle_window(app: &tauri::AppHandle) {
    if let Some(window) = app.get_webview_window("main") {
        if window.is_visible().unwrap_or(false) {
            window.hide().ok();
        } else {
            window.show().ok();
            window.set_focus().ok();
        }
    } else {
        create_main_window(app);
    }
}

/// 从 API 获取状态并更新托盘图标
fn update_tray_icon(app: &tauri::AppHandle) {
    let client = match reqwest::blocking::Client::builder()
        .timeout(std::time::Duration::from_secs(5))
        .build()
    {
        Ok(c) => c,
        Err(_) => return,
    };

    let color = match client.get(API_URL).send() {
        Ok(r) => r.json::<serde_json::Value>()
            .ok()
            .and_then(|v| v["summary"]["color"].as_str().map(String::from))
            .unwrap_or_else(|| "green".into()),
        Err(_) => "green".into(),
    };

    if let Some(tray) = app.tray_by_id("main") {
        let _ = tray.set_icon(Some(make_icon(&color)));
    }
}

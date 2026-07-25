use std::net::TcpStream;
use std::process::{Command, Child};
use std::time::Duration;

use tauri::{
    Emitter,
    image::Image,
    menu::{Menu, MenuItem},
    tray::{MouseButton, MouseButtonState, TrayIconBuilder, TrayIconEvent},
    Manager,
};

const API_BASE: &str = "http://127.0.0.1:9800";

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

fn is_api_alive() -> bool {
    TcpStream::connect_timeout(
        &"127.0.0.1:9800".parse().unwrap(),
        Duration::from_secs(2),
    )
    .is_ok()
}

fn log_msg(msg: &str) {
    if let Ok(mut f) = std::fs::OpenOptions::new()
        .create(true).append(true).open("/tmp/aihouse-bootstrap.log")
    {
        use std::io::Write;
        let _ = writeln!(f, "{}", msg);
    }
}

fn find_python() -> Option<String> {
    let candidates = [
        "/opt/homebrew/bin/python3.11",
        "/opt/homebrew/bin/python3",
        "/usr/local/bin/python3",
        "/usr/bin/python3",
    ];
    for p in &candidates {
        let path = std::path::Path::new(p);
        if path.exists() {
            let out = Command::new(p)
                .args(["-c", "import aihouse; print('ok')"])
                .output();
            match out {
                Ok(o) if o.status.success() => {
                    log_msg(&format!("find_python: {} works", p));
                    return Some(p.to_string());
                }
                Ok(o) => {
                    let msg = String::from_utf8_lossy(&o.stderr);
                    log_msg(&format!("find_python: {} import fail: {}", p, msg.lines().next().unwrap_or("?")));
                }
                Err(e) => {
                    log_msg(&format!("find_python: {} run fail: {}", p, e));
                }
            }
        } else {
            log_msg(&format!("find_python: {} not found", p));
        }
    }
    for name in &["python3", "python"] {
        if let Ok(path) = which::which(name) {
            let p = path.to_string_lossy().to_string();
            let out = Command::new(&p)
                .args(["-c", "import aihouse; print('ok')"])
                .output();
            if let Ok(o) = out {
                if o.status.success() {
                    log_msg(&format!("find_python: {} works (via which)", p));
                    return Some(p);
                }
            }
        }
    }
    log_msg("find_python: no python with aihouse found");
    None
}

fn start_backend() -> Option<Child> {
    let python = find_python()?;
    log_msg(&format!("start_backend: using {}", python));
    match Command::new(&python)
        .args(["-m", "aihouse", "daemon"])
        .spawn()
    {
        Ok(child) => {
            log_msg(&format!("start_backend: spawned PID {}", child.id()));
            Some(child)
        }
        Err(e) => {
            log_msg(&format!("start_backend: spawn failed: {}", e));
            None
        }
    }
}

fn wait_for_backend(timeout_secs: u64) -> bool {
    let start = std::time::Instant::now();
    while start.elapsed().as_secs() < timeout_secs {
        if is_api_alive() {
            return true;
        }
        std::thread::sleep(Duration::from_millis(500));
    }
    false
}

/// Tauri IPC command: proxy HTTP GET to the Python backend
#[tauri::command]
fn fetch_api(path: String) -> Result<String, String> {
    let url = format!("{}{}", API_BASE, path);
    let client = reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(10))
        .build()
        .map_err(|e| format!("client: {}", e))?;
    let resp = client.get(&url)
        .send()
        .map_err(|e| format!("request: {}", e))?;
    resp.text().map_err(|e| format!("body: {}", e))
}

fn main() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![fetch_api])
        .setup(|app| {
            let open_item = MenuItem::with_id(app, "open", "显示窗口", true, None::<&str>)?;
            let restart_item = MenuItem::with_id(app, "restart", "重启后端", true, None::<&str>)?;
            let settings_item = MenuItem::with_id(app, "settings", "设置", true, None::<&str>)?;
            let quit_item = MenuItem::with_id(app, "quit", "退出", true, Some("CmdOrCtrl+Q"))?;
            let menu = Menu::with_items(app, &[&open_item, &restart_item, &settings_item, &quit_item])?;

            TrayIconBuilder::new()
                .icon(make_icon("green"))
                .menu(&menu)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "open" => toggle_window(app),
                    "restart" => restart_backend(app),
                    "settings" => {
                        let home = std::env::var("HOME").unwrap_or_default();
                        let _ = open::that(format!("{}/.aihouse/config.yaml", home));
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

            // 自动启动后端（如果未运行）
            if !is_api_alive() {
                log_msg("backend not running, starting...");
                if let Some(_child) = start_backend() {
                    log_msg("backend process spawned, waiting up to 8s...");
                    if wait_for_backend(8) {
                        log_msg("backend ready");
                    } else {
                        log_msg("backend start timeout");
                    }
                } else {
                    log_msg("failed to start backend");
                }
            } else {
                log_msg("backend already running");
            }

            create_main_window(app.handle());

            let app_handle = app.handle().clone();
            std::thread::spawn(move || {
                loop {
                    std::thread::sleep(Duration::from_secs(10));
                    update_tray_icon(&app_handle);
                }
            });

            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}

fn create_main_window(app: &tauri::AppHandle) {
    let _window = tauri::WebviewWindowBuilder::new(
        app, "main",
        tauri::WebviewUrl::App("index.html".into()),
    )
    .title("AIHouse")
    .inner_size(720.0, 560.0)
    .min_inner_size(520.0, 420.0)
    .resizable(true)
    .decorations(true)
    .build()
    .expect("failed to build main window");
}

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

fn restart_backend(app: &tauri::AppHandle) {
    let _ = reqwest::blocking::Client::new()
        .post("http://127.0.0.1:9800/shutdown")
        .timeout(Duration::from_secs(2))
        .send();

    std::thread::sleep(Duration::from_secs(1));

    if let Some(_child) = start_backend() {
        if wait_for_backend(8) {
            log_msg("backend restarted");
        } else {
            log_msg("backend restart timeout");
        }
    }

    if let Some(window) = app.get_webview_window("main") {
        let _ = window.emit("backend-restarted", ());
    }
}

fn update_tray_icon(app: &tauri::AppHandle) {
    let client = match reqwest::blocking::Client::builder()
        .timeout(Duration::from_secs(5))
        .build()
    {
        Ok(c) => c,
        Err(_) => return,
    };

    let color = match client.get(format!("{}/api/status", API_BASE)).send() {
        Ok(r) => r.json::<serde_json::Value>()
            .ok()
            .and_then(|v| v["summary"]["color"].as_str().map(String::from))
            .unwrap_or_else(|| {
                if is_api_alive() { "green".into() } else { "red".into() }
            }),
        Err(_) => "red".into(),
    };

    if let Some(tray) = app.tray_by_id("main") {
        let _ = tray.set_icon(Some(make_icon(&color)));
    }
}

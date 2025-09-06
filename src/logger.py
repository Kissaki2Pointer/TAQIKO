from datetime import datetime
import os


def slog(system_state, log_message):
    """
    ログを出力する関数
    
    Args:
        system_state (str): システム状態（例：RUNNING, ERROR, INFO など）
        log_message (str): ログ出力内容
    
    フォーマット: {日付} {時刻} {システム状態} {ログ出力}
    """
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    
    formatted_log = f"{date_str} {time_str} {system_state} {log_message}"
    
    print(formatted_log)
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    logs_dir = os.path.join(project_root, "logs")
    log_filename = os.path.join(logs_dir, f"{date_str}.log")
    
    os.makedirs(logs_dir, exist_ok=True)
    
    with open(log_filename, 'a', encoding='utf-8') as f:
        f.write(formatted_log + '\n')
# -*- coding: utf-8 -*-
"""IT知识库 - 一键启动器（WSL 打包，Windows 运行）"""
import os
import socket
import sys
import time
import webbrowser
from pathlib import Path

PORT = 8501
BASE_DIR = Path(__file__).parent.resolve()
os.chdir(BASE_DIR)

ASCII_ART = """
╔══════════════════════════════════════╗
║  🦞 IT 问题知识库                    ║
║  Streamlit + GitHub 即数据库         ║
║  地址: http://127.0.0.1:8501         ║
╚══════════════════════════════════════╝
"""


def port_in_use(port: int) -> bool:
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main() -> None:
    print(ASCII_ART)
    print(f"[+] 工作目录: {BASE_DIR}")
    print(f"[+] 数据文件: {BASE_DIR / 'entries'}")

    # 端口检查
    for _ in range(30):
        if not port_in_use(PORT):
            break
        print(f"[!] 端口 {PORT} 被占用，等待释放...")
        time.sleep(1)
    else:
        print(f"[x] 端口 {PORT} 一直被占用，换一个吧")
        input("按回车退出...")
        sys.exit(1)

    # 打开浏览器（留 2 秒缓冲）
    def _open():
        time.sleep(2.5)
        webbrowser.open(f"http://127.0.0.1:{PORT}")
        print(f"[+] 浏览器已打开 http://127.0.0.1:{PORT}")

    import threading
    threading.Thread(target=_open, daemon=True).start()

    print("\n[+] 正在启动 Streamlit...")
    print("[+] 关闭此窗口即可停止服务\n")

    # 启动 Streamlit
    sys.argv = [
        "streamlit", "run", "app/app.py",
        "--server.port", str(PORT),
        "--server.address", "127.0.0.1",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]
    from streamlit.web.cli import main as st_main
    st_main()


if __name__ == "__main__":
    main()

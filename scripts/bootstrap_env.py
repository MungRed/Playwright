import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VENV_DIR = ROOT / ".venv"
REQ_FILE = ROOT / ".mcp" / "requirements.txt"
MCP_JSON = ROOT / ".vscode" / "mcp.json"
MCP_EXAMPLE_JSON = ROOT / ".vscode" / "mcp.example.json"
SCENES_DIR = ROOT / "docs" / "scenes"


class CheckResult:
    def __init__(self, name: str, ok: bool, detail: str):
        self.name = name
        self.ok = ok
        self.detail = detail


def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return proc.returncode, proc.stdout.strip()


def python_ok() -> CheckResult:
    major, minor = sys.version_info.major, sys.version_info.minor
    ok = (major, minor) >= (3, 10)
    return CheckResult(
        "Python 版本",
        ok,
        f"当前 {major}.{minor}，要求 >= 3.10",
    )


def ensure_venv(check_only: bool) -> CheckResult:
    if VENV_DIR.exists():
        return CheckResult("虚拟环境", True, f"已存在：{VENV_DIR}")

    if check_only:
        return CheckResult("虚拟环境", False, "未找到 .venv（check-only 模式未创建）")

    code, out = run([sys.executable, "-m", "venv", str(VENV_DIR)])
    if code == 0:
        return CheckResult("虚拟环境", True, f"已创建：{VENV_DIR}")
    return CheckResult("虚拟环境", False, f"创建失败：{out[-300:]}")


def venv_python() -> Path:
    if os.name == "nt":
        return VENV_DIR / "Scripts" / "python.exe"
    return VENV_DIR / "bin" / "python"


def install_deps(check_only: bool) -> CheckResult:
    if not REQ_FILE.exists():
        return CheckResult("依赖安装", False, f"缺少依赖文件：{REQ_FILE}")

    py = venv_python()
    if not py.exists():
        return CheckResult("依赖安装", False, "未找到虚拟环境解释器，请先创建 .venv")

    if check_only:
        return CheckResult("依赖安装", True, f"已检测到依赖文件：{REQ_FILE}")

    code1, out1 = run([str(py), "-m", "pip", "install", "--upgrade", "pip"])
    code2, out2 = run([str(py), "-m", "pip", "install", "-r", str(REQ_FILE)])

    if code1 == 0 and code2 == 0:
        return CheckResult("依赖安装", True, f"安装完成：{REQ_FILE}")

    msg = (out1 + "\n" + out2)[-500:]
    return CheckResult("依赖安装", False, f"安装失败：{msg}")


def ensure_dirs(check_only: bool) -> CheckResult:
    if SCENES_DIR.exists():
        return CheckResult("目录检查", True, f"目录已存在：{SCENES_DIR}")

    if check_only:
        return CheckResult("目录检查", False, f"目录缺失：{SCENES_DIR}（check-only 未创建）")

    SCENES_DIR.mkdir(parents=True, exist_ok=True)
    return CheckResult("目录检查", True, f"已创建目录：{SCENES_DIR}")


def ensure_mcp_config(check_only: bool) -> CheckResult:
    if MCP_JSON.exists():
        return CheckResult("MCP 配置", True, f"已找到本地配置：{MCP_JSON}")

    if not MCP_EXAMPLE_JSON.exists():
        return CheckResult(
            "MCP 配置",
            False,
            "缺少 .vscode/mcp.example.json，无法生成本地配置",
        )

    if check_only:
        return CheckResult(
            "MCP 配置",
            False,
            "未找到 .vscode/mcp.json（check-only 模式未创建，请复制 mcp.example.json 后填写 API_KEY）",
        )

    MCP_JSON.parent.mkdir(parents=True, exist_ok=True)
    MCP_JSON.write_text(MCP_EXAMPLE_JSON.read_text(encoding="utf-8"), encoding="utf-8")
    return CheckResult(
        "MCP 配置",
        True,
        f"已从模板生成：{MCP_JSON}（请自行填写 API_KEY）",
    )


def import_check() -> CheckResult:
    py = venv_python() if venv_python().exists() else Path(sys.executable)
    snippet = (
        "import tkinter\n"
        "import httpx\n"
        "from PIL import Image\n"
        "from mcp.server import Server\n"
        "print('OK')\n"
    )
    code, out = run([str(py), "-c", snippet])
    if code == 0:
        return CheckResult("模块导入", True, "tkinter/httpx/Pillow/mcp 导入成功")
    return CheckResult("模块导入", False, f"导入失败：{out[-300:]}")


def print_summary(results: list[CheckResult]) -> int:
    print("\n=== 本地环境自检结果 ===")
    failed = 0
    for item in results:
        mark = "PASS" if item.ok else "FAIL"
        if not item.ok:
            failed += 1
        print(f"[{mark}] {item.name}: {item.detail}")

    print("\n=== 结论 ===")
    if failed == 0:
        print("已完成：环境可直接运行。")
        print(f"运行命令：{venv_python()} {ROOT / 'main.py'}")
        return 0

    print(f"部分完成：共有 {failed} 项未通过。")
    print("建议先修复失败项后再运行 main.py。")
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并部署项目本地环境")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="仅检查，不执行创建/安装动作",
    )
    args = parser.parse_args()

    results: list[CheckResult] = []
    results.append(python_ok())

    if not results[-1].ok:
        return print_summary(results)

    results.append(ensure_venv(args.check_only))
    results.append(install_deps(args.check_only))
    results.append(ensure_dirs(args.check_only))
    results.append(ensure_mcp_config(args.check_only))
    results.append(import_check())

    return print_summary(results)


if __name__ == "__main__":
    raise SystemExit(main())

import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LANGUAGES = {
    "python": {
        "suffix": ".py",
        "run": lambda file: sys.executable,
    },
    "py": {
        "suffix": ".py",
        "run": lambda file: sys.executable,
    },
    "c": {
        "suffix": ".c",
        "compile": lambda src,
        exe: [ "gcc", src, "-o", exe,],
        "run_exe": True,
    },
    "cpp": {
        "suffix": ".cpp",
        "compile": lambda src,
        exe: [ "g++", src, "-o", exe,],
        "run_exe": True,
    },
    "javascript": {
        "suffix": ".js",
        "run": lambda file: ["node", file],
    },

    "js": {
        "suffix": ".js",
        "run": lambda file: ["node", file],
    },

    "go": {
        "suffix": ".go",
        "run": lambda file: ["go", "run", file],
    },

    "bash": {
        "suffix": ".sh",
        "run": lambda file: ["bash", file],
    },
}


def extract_code_blocks(markdown):
    
    pattern = r"```([a-zA-Z0-9+#_-]+)\s*\n(.*?)```"
    
    return re.findall(
        pattern,
        markdown,
        re.DOTALL,
    )


def run_block(language, code, number):

    language = language.lower()

    print()
    print("=" * 60)
    print(f"[Block {number}] {language}")
    print("=" * 60)

    if language not in LANGUAGES:
        print("Unsupported language.")
        return

    config = LANGUAGES[language]

    try:

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            source = temp_dir / ( "main" + config["suffix"])
            source.write_text(code, encoding="utf-8",)

            # コンパイル型
            if "compile" in config:
                exe = temp_dir / "program"
                compile_cmd = config["compile"](str(source),str(exe),)
                result = subprocess.run(compile_cmd,capture_output=True,text=True,)
                
                if result.returncode != 0:
                    print("[Compile Error]")
                    print(result.stderr)
                    return

                command = [str(exe)]

            # インタプリタ型
            else:
                command = config["run"](str(source))

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print("[stderr]")
                print(result.stderr)

    except FileNotFoundError as e:
        print("実行環境が見つかりません:", e,)

    except subprocess.TimeoutExpired:
        print("Timeout: 30秒を超えました。")

commands = {
    "Python": sys.executable,
    "Git": "git",
    "GCC (C)": "gcc",
    "G++ (C++)": "g++",
    "Node.js": "node",
    "Go": "go",
    "Rust": "rustc",
    "Java": "java",
}

print("=== Rough-and-ready-think Environment Check ===\n")

for name, command in commands.items():

    # Pythonだけ絶対パスが入る可能性あり
    if name == "Python":
        path = sys.executable
    else:
        path = shutil.which(command)

    if path:
        print(f"[OK] {name:<12} : {path}")
    else:
        print(f"[--] {name:<12} : not found")


def main():

    if len(sys.argv) < 2:
        print(
            "Usage:" 
            " python tools/mdrun.py <markdown>"
        )
        sys.exit(1)

    path = Path(sys.argv[1])

    if not path.exists():
        print("File not found:", path)
        sys.exit(1)

    markdown = path.read_text(encoding="utf-8",)
    blocks = extract_code_blocks(markdown)

    if not blocks:
        print("コードブロックがありません。")
        return

    print(f"{len(blocks)} code block(s) found.")

    for number, (language, code) in enumerate(
        blocks,
        start=1,
    ):

        run_block(
            language,
            code,
            number,
        )

if __name__ == "__main__":
    main()

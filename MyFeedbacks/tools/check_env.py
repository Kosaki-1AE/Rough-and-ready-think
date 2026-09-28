import shutil
import sys

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

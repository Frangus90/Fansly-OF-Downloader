import os, sys

root = r"C:\Users\aleks\Desktop\Project\FanslyDLNG\fansly-downloader-ng"
exts = {'.md', '.txt', '.json', '.py', '.toml', '.cfg', '.ini', '.yaml', '.yml'}

for dirpath, _, files in os.walk(root):
    for fname in files:
        if any(fname.endswith(e) for e in exts):
            fpath = os.path.join(dirpath, fname)
            try:
                with open(fpath, 'r', encoding='utf-8', errors='surrogatepass') as f:
                    content = f.read()
                for i, c in enumerate(content):
                    if 0xD800 <= ord(c) <= 0xDFFF:
                        print(f"SURROGATE FOUND: {fpath} at char {i}")
            except Exception as e:
                print(f"ERROR reading {fpath}: {e}")

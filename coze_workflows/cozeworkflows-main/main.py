#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
容错版：外层 zip 损坏时 → 直接当粘连流切分
python batch_share2poor_robust.py
"""
import json, yaml, tempfile, zipfile, re, sys
from pathlib import Path

OUT_DIR0 = Path('穷人粘贴版')
OUT_DIR = Path('coze_workflows/coze_workflows-main/穷人粘贴版')
MAP_FILE = OUT_DIR / '文件名-desc对照表.txt'

JSON_PAT = re.compile(rb'-draft\.json(.*)MANIFEST\.yml', re.DOTALL)

def json_from_raw(raw: bytes) -> dict:
    start = raw.index(b'{')
    depth, i = 1, start + 1
    while i < len(raw) and depth:
        if raw[i] == ord('{'): depth += 1
        elif raw[i] == ord('}'): depth -= 1
        i += 1
    if depth: raise ValueError('JSON 括号不平衡')
    return json.loads(raw[start:i])

def convert_from_blob(blob: bytes) -> tuple[str, str]:
    """粘连流 -> clipboard json + desc"""
    m = JSON_PAT.search(blob)
    if not m: raise ValueError('未找到 JSON/MANIFEST 段')
    draft = json_from_raw(m.group(1))
    for node in draft["nodes"]:
        node["_temp"] = {
            "bounds": {
                "x": 0,
                "y": 0,
                "width": 0,
                "height": 0
            }
        }
    # 1. 删掉指定 id 的节点
    draft["nodes"] = [n for n in draft["nodes"] if n.get("id") not in {"100001", "900001"}]

    # 2. 再删掉与这些 id 相关的边
    draft["edges"] = [
        e for e in draft["edges"]
        if e.get("sourceNodeID") not in {"100001", "900001"} and
           e.get("targetNodeID") not in {"100001", "900001"}
    ]

    manifest = yaml.safe_load(blob[blob.rfind(b'MANIFEST.yml'):].split(b'\n', 1)[1].decode('utf-8', errors='ignore'))
    clipboard = {
        "type": "coze-workflow-clipboard-data",
        "source": {
            "workflowId": str(manifest["main"]["id"]),
            "spaceId": "",
            "host": "www.coze.cn",
            "isDouyin": False,
            "flowMode": manifest["main"].get("flowMode", 0),
        },
        "json": draft,
        "bounds":{"x":0,"y":0,"width":4567,"height":1234}
    }
    return json.dumps(clipboard, ensure_ascii=False, separators=(",", ":")), manifest["main"]["desc"]

def safe_name(base: str) -> Path:
    target = OUT_DIR / f"{base}.json"
    idx = 1
    while target.exists():
        target = OUT_DIR / f"{base}_{idx}.json"
        idx += 1
    return target

def main():
    top = Path(__file__).parent / '工作流200+合集分享'
    if not top.exists():
        sys.exit('目录「工作流200+合集分享」不存在')
    OUT_DIR.mkdir(exist_ok=True)

    map_lines = []
    for outer in top.glob('*.zip'):
        try:
            # ① 先当正常 zip 解
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                try:
                    with zipfile.ZipFile(outer, 'r') as zf:
                        zf.extractall(tmp)
                    inner = tmp / (outer.stem + '.zip')
                    if not inner.exists():
                        raise FileNotFoundError('内层 zip 不存在')
                    single_line_json, desc = convert_from_blob(inner.read_bytes())
                except (zipfile.BadZipFile, FileNotFoundError):
                    # ② 失败 → 直接当粘连流
                    single_line_json, desc = convert_from_blob(outer.read_bytes())

            out_file = safe_name(outer.stem)
            out_file.write_text(single_line_json, encoding='utf-8')
            map_lines.append(f"{out_file.name}\t{desc}")
            print(f'✅ 完成: {out_file.name}')
        except Exception as e:
            print(f'❌ 失败: {outer.name}  {e}')

    if map_lines:
        MAP_FILE.write_text('\n'.join(map_lines), encoding='utf-8')
        print(f'✅ 对照表已生成: {MAP_FILE}')

if __name__ == '__main__':
        # 先删再建
        import shutil
        if OUT_DIR0.exists():
            shutil.rmtree(OUT_DIR0)
        if OUT_DIR.exists():
            shutil.rmtree(OUT_DIR)
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        
        main()

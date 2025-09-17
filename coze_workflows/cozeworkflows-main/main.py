#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批量  外层zip→内层zip→coze-clipboard-data
输出到 穷人粘贴版/*.json
并生成 文件名-desc对照表.txt
"""
import json, yaml, tempfile, zipfile, sys
from pathlib import Path

OUT_DIR = Path('穷人粘贴版')
MAP_FILE = OUT_DIR / '文件名-desc对照表.txt'

def json_from_raw(raw: bytes) -> dict:
    start = raw.index(b'{')
    depth, i = 1, start + 1
    while i < len(raw) and depth:
        if raw[i] == ord('{'): depth += 1
        elif raw[i] == ord('}'): depth -= 1
        i += 1
    if depth: raise ValueError('JSON 括号不平衡')
    return json.loads(raw[start:i])

def convert_one(inner_zip: Path) -> tuple[str, str]:
    with zipfile.ZipFile(inner_zip, 'r') as zf:
        draft = json_from_raw(zf.read(next(n for n in zf.namelist() if n.endswith('-draft.json'))))
        manifest = yaml.safe_load(zf.read('MANIFEST.yml'))
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
    }
    return json.dumps(clipboard, ensure_ascii=False, separators=(",", ":")), manifest["main"]["desc"]

def safe_name(base: str) -> Path:
    """重名自动加序号"""
    target = OUT_DIR / f"{base}.json"
    idx = 1
    while target.exists():
        target = OUT_DIR / f"{base}_{idx}.json"
        idx += 1
    return target

def main():
    #top = Path.cwd()
    # 脚本放在上一级，扫描下一级「工作流200+合集分享」
    top = Path(__file__).parent / '工作流200+合集分享'

    if not OUT_DIR.exists():
        OUT_DIR.mkdir(exist_ok=True)

    map_lines = []
    for outer in top.glob('*.zip'):
        try:
            with tempfile.TemporaryDirectory() as tmp:
                tmp = Path(tmp)
                with zipfile.ZipFile(outer, 'r') as zf:
                    zf.extractall(tmp)
                inner = tmp / (outer.stem + '.zip')
                if not inner.exists():
                    print(f'⚠️  内层zip缺失: {outer.name}')
                    continue
                single_line_json, desc = convert_one(inner)
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
    main()

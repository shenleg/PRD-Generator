"""以已保存的真实模型候选重放当前首稿脚本；不调用模型，不改原始模型输出。"""

import argparse
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def read(path):
    """读取可信留证 path 并返回 JSON；文件及解析错误直接使重放失败。"""
    return json.loads(path.read_text(encoding="utf-8"))


def save(path, value):
    """在新的留证目录保存 value，返回 path；序列化和文件错误原样抛出。"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return path


def fingerprint(root):
    """返回 root 内文件原始字节摘要映射，目录遍历和读取失败原样抛出。"""
    import hashlib
    return {str(path.relative_to(root)): "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(root.rglob("*")) if path.is_file()}


def call(folder, name, script, args, root):
    """执行公开 script 和 args，保存 root 前后快照及真实响应，返回解析 JSON；非 JSON 响应抛异常。"""
    before = fingerprint(root)
    command = [sys.executable, "-I", "-B", str(script), *map(str, args)]
    response = subprocess.run(command, capture_output=True, text=True, cwd="/", timeout=60)
    save(folder / (name + ".json"), {"command": command, "stdout": response.stdout, "stderr": response.stderr,
                                      "exit_code": response.returncode, "before": before, "after": fingerprint(root)})
    return json.loads(response.stdout)


def main(argv=None):
    """按 argv 在全新输出目录重放十二份模型草稿；返回0成功、1有失败，参数/文件异常明确抛出。

    review 为程序评分目录，output 必须不存在。只重放已由真实成功响应定位的模型候选；
    同一分析重复保存验证0.1至0.2，不把脚本重放称为新的模型生成或人工评审。
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", type=Path, default=ROOT / "tests/results/prd-generator/stage-3-model-review")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    for name in ("prd-generator", "requirement-analyst"):
        shutil.copytree(ROOT / "skill" / name, output / "source-snapshot" / name, ignore=shutil.ignore_patterns("__pycache__"))
    scripts = output / "source-snapshot/prd-generator/scripts"
    spec = importlib.util.spec_from_file_location("model_replay_renderer", scripts / "render_info.py")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    manifest = {"model_run": False, "replay_of_actual_model_outputs": True, "human_review": "pending",
                "source_fingerprints": fingerprint(output / "source-snapshot"), "requirements": []}
    groups = read(args.review / "programmatic-summary.json")
    for group in groups:
        for row in group["requirements"]:
            rid = row["requirement_id"]
            folder = output / group["group"] / group["configuration"] / rid
            root = folder / "requirement"
            original = ROOT / "workspace-sandbox/prd-generator/stage-3-model/iteration-1/inputs" / group["group"] / rid
            shutil.copytree(original, root)
            before = fingerprint(root)
            candidate = ROOT / row["first_successful_candidate"]
            patch = read(candidate / "inputs/numbering-patch.json")
            patch_path = save(folder / "numbering-patch.json", patch)
            body = folder / "model-body.md"
            shutil.copyfile(candidate / "inputs/body.md", body)
            entry = {"requirement_id": rid, "group": group["group"], "configuration": group["configuration"],
                     "actual_model_candidate": row["first_successful_candidate"], "status": "fail"}
            manifest["requirements"].append(entry)
            try:
                gate = call(folder, "gate", scripts / "check_gate.py", [root], root)
                if not gate.get("allowed"):
                    raise ValueError("重放门禁拒绝")
                allocated = call(folder, "assign", scripts / "assign_ids.py", [root, "--patch", patch_path], root)
                if allocated.get("items") != read(candidate / "prd/prd-trace.json")["items"]:
                    raise ValueError("当前编号候选与实际模型原映射不同")
                saved = call(folder, "write", scripts / "write_draft.py", [root, "--patch", patch_path, "--body", body,
                               "--gaps", candidate / "prd/gap-requests.json", "--candidate-dir", folder / "candidate-1"], root)
                if not saved.get("generated"):
                    raise ValueError("当前首稿保存失败")
                first_text = (root / "prd/prd.md").read_text()
                first_trace = read(root / "prd/prd-trace.json")
                repeat_patch = deepcopy(patch)
                repeat_patch["base_prd_version"] = "0.1"
                repeat_path = save(folder / "repeat-patch.json", repeat_patch)
                repeat_body = folder / "repeat-body.md"
                repeat_body.write_text(first_text, encoding="utf-8")
                repeated = call(folder, "repeat", scripts / "write_draft.py", [root, "--patch", repeat_path, "--body", repeat_body,
                                  "--candidate-dir", folder / "candidate-2"], root)
                if not repeated.get("generated"):
                    raise ValueError("当前重复生成失败")
                final_text = (root / "prd/prd.md").read_text()
                first_body = renderer._take_section(renderer._take_section(first_text, "info"), "changes").strip("\r\n")
                final_body = renderer._take_section(renderer._take_section(final_text, "info"), "changes").strip("\r\n")
                if first_trace["items"] != read(root / "prd/prd-trace.json")["items"] or first_body != final_body:
                    raise ValueError("当前编号或包括章节外内容的需求正文不稳定")
                checked = call(folder, "validate", scripts / "validate_prd.py", [root], root)
                if checked["status"] == "fail":
                    raise ValueError("当前最终校验失败")
                if any((root / name).read_bytes() != (original / name).read_bytes() for name in before if name.startswith("analysis/")):
                    raise ValueError("重放改写分析原始字节")
                entry.update(status="pass", validation=checked["status"], version=read(root / "requirement.json")["prd"]["version"],
                             repeat_stable=True, analysis_unchanged=True)
            except (OSError, ValueError, KeyError, TypeError) as error:
                entry["error"] = str(error)
            finally:
                save(output / "manifest.json", manifest)
    return int(any(row["status"] != "pass" for row in manifest["requirements"]))


if __name__ == "__main__":
    raise SystemExit(main())

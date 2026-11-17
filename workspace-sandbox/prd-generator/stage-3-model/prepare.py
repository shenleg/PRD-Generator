"""为阶段3模型试跑创建独立冻结输入与生产快照；不改历史样例或替模型写PRD。"""

import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).parent / "iteration-1"
OUTPUT.mkdir(exist_ok=False)
for name in ("prd-generator", "requirement-analyst"):
    shutil.copytree(ROOT / "skill" / name, OUTPUT / "skill-snapshot" / name, ignore=shutil.ignore_patterns("__pycache__"))
catalog = json.loads((ROOT / "tests/fixtures/prd-generator/sample-catalog.json").read_text())
records = []
for sample in catalog["samples"]:
    rid, group = sample["requirement_id"], sample["group"]
    target = OUTPUT / "inputs" / group / rid
    (target / "analysis").mkdir(parents=True)
    analysis_path = ROOT / sample["analysis"]
    manifest_path = ROOT / sample["source_manifest"]
    shutil.copyfile(analysis_path, target / "analysis/analysis-result.json")
    project = "high-low-voltage" if group == "switch-combinations" else "task-management"
    metadata_path = ROOT / f"workspace-sandbox/stage-3/workspace/projects/{project}/requirements/{rid}/requirement.json"
    metadata = json.loads(metadata_path.read_text())
    metadata.pop("prd", None)
    (target / "requirement.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    source = ROOT / ("tests/fixtures/requirement-analyst/high-low-voltage/original-requirement.md" if group == "switch-combinations" else "tests/fixtures/requirement-analyst/sample-02-task-management.md")
    material = OUTPUT / "sources" / source.name
    material.parent.mkdir(exist_ok=True)
    if not material.exists():
        shutil.copyfile(source, material)
    manifest = json.loads(manifest_path.read_text())
    relocations = []
    for entry in manifest:
        relocations.append({"source_id": entry["source_id"], "from": entry["path"], "to": str(material)})
        entry["path"] = str(material)
    (target / "analysis/source-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    records.append({"requirement_id": rid, "group": group, "historical_analysis": str(analysis_path.relative_to(ROOT)),
                    "analysis_sha256": "sha256:" + hashlib.sha256(analysis_path.read_bytes()).hexdigest(),
                    "common_source": str(metadata_path.relative_to(ROOT)), "source_relocations": relocations})
(OUTPUT / "input-provenance.json").write_text(json.dumps({"role": "model_trial_setup_not_model_output", "historical_files_changed": False,
                    "samples": records}, ensure_ascii=False, indent=2) + "\n")
print(OUTPUT)

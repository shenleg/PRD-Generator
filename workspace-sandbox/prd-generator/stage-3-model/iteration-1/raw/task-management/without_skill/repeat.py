"""重复草稿生成，保留调用日志并比较正文和编号。"""
import json, pathlib, subprocess, re, shutil
O=pathlib.Path(__file__).parent
P=O/'skill/prd-generator/scripts'
PY=['uv','run','--offline','--no-project','--python','/usr/bin/python3','--with-requirements',str(O/'skill/requirement-analyst/scripts/requirements.txt'),'python','-I','-B']
for d in sorted((O/'workspaces').iterdir()):
 r=O/'runs'/d.name
 shutil.copyfile(d/'prd/prd.md',r/'first-prd.md');shutil.copyfile(d/'prd/prd-trace.json',r/'first-trace.json')
 patch=json.loads((r/'patch.json').read_text());patch['base_prd_version']='0.1';(r/'patch-repeat.json').write_text(json.dumps(patch,ensure_ascii=False,indent=2)+'\n')
 args=PY+[str(P/'write_draft.py'),str(d),'--patch',str(r/'patch-repeat.json'),'--body',str(r/'body.md'),'--gaps',str(r/'gaps.json'),'--candidate-dir',str(r/'candidate-repeat')]
 a=subprocess.run(args,capture_output=True,text=True);(r/'write-repeat.stdout').write_text(a.stdout);(r/'write-repeat.stderr').write_text(a.stderr)
 v=subprocess.run(PY+[str(P/'validate_prd.py'),str(d)],capture_output=True,text=True);(r/'validate.stdout').write_text(v.stdout);(r/'validate.stderr').write_text(v.stderr)
 first=json.loads((r/'first-trace.json').read_text());second=json.loads((d/'prd/prd-trace.json').read_text());p=r'<!-- prd:section (?:info|changes) -->.*?<!-- /prd:section -->'; b1=(r/'first-prd.md').read_text();b2=(d/'prd/prd.md').read_text();same=re.sub(p,'',b1,flags=re.S)==re.sub(p,'',b2,flags=re.S)
 comparison={'items_stable':first['items']==second['items'],'body_stable_excluding_info_changes':same};(r/'stability.json').write_text(json.dumps(comparison,indent=2)+'\n')
 print(d.name,'repeat',a.returncode,a.stdout,'validate',v.returncode,v.stdout,'stable',comparison)

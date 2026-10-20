"""Static connection inventory; complements executable/runtime regression checks."""
import argparse
import ast
from collections import defaultdict
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]


def inventory():
    files=sorted(p for base in ('underworld','scripts','tests') for p in (ROOT/base).rglob('*.py'))
    edges=[];errors=[];duplicates=defaultdict(list)
    for file in files:
        tree=ast.parse(file.read_text(encoding='utf-8-sig'),filename=str(file))
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                if node.level:
                    base=file.parent
                    for _ in range(node.level-1):base=base.parent
                    target=base.joinpath(*(node.module or '').split('.')) if node.module else base
                    if node.module and not(target.with_suffix('.py').is_file() or (target/'__init__.py').is_file()):
                        errors.append({'file':str(file.relative_to(ROOT)),'line':node.lineno,'missing_relative_module':node.module})
                    edges.append({'from':str(file.relative_to(ROOT)),'module':'.'*node.level+(node.module or ''),'names':[a.name for a in node.names]})
                elif node.module and (node.module.startswith(('underworld','scripts')) or (file.parent/(node.module+'.py')).is_file()):
                    edges.append({'from':str(file.relative_to(ROOT)),'module':node.module,'names':[a.name for a in node.names]})
            if file.parent==ROOT/'underworld' and isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef)) and len(node.body)>=6:
                # Compare substantial whole functions, excluding names/docstrings.
                shape=ast.FunctionDef(name='function',args=node.args,body=node.body,decorator_list=[],returns=node.returns,type_comment=None)
                duplicates[ast.dump(shape,include_attributes=False)].append(f'{file.relative_to(ROOT)}:{node.lineno}:{node.name}')
    headers=[]
    for file in sorted((ROOT/'core').glob('*')):
        if file.suffix not in ('.cpp','.hpp'):continue
        for name in re.findall(r'#include\s+"([^"]+)"',file.read_text()):
            headers.append({'from':str(file.relative_to(ROOT)),'include':name})
            if not (file.parent/name).exists():errors.append({'file':str(file),'missing_header':name})
    assets=[]
    for file in sorted((ROOT/'underworld/web').glob('*.js')):
        for name in re.findall(r"(?:from\s*|import\s*\()['\"](/[^'\"]+\.js)['\"]",file.read_text()):
            assets.append(name)
            if not (ROOT/'underworld/web'/name.lstrip('/')).exists():errors.append({'file':str(file),'missing_asset':name})
    return {'python_files_parsed':len(files),'python_local_import_edges':edges,'native_local_header_edges':headers,'javascript_local_module_assets':sorted(set(assets)),
            'repeated_substantial_production_functions':[v for v in duplicates.values() if len(v)>1],'errors':errors,
            'limits':'Static inventory does not prove all branches, platform integrations or dynamic imports correct; use regression and packaged smoke evidence.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    report=inventory();args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k not in ('python_local_import_edges','native_local_header_edges')},indent=2))
    return 1 if report['errors'] else 0


if __name__=='__main__':raise SystemExit(main())

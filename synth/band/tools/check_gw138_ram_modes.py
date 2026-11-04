"""Reject the GW5AST-138B DPB modes explicitly rejected by vendor PA2122.

This checks a known incompatibility only; it is not a placement/timing gate.
"""
from pathlib import Path
import re, sys

def check(path):
    text=Path(path).read_text()
    violations=[]
    for module,body in re.findall(r'module\s+(\S+)\s*\((.*?)endmodule',text,re.S):
        for instance in re.findall(r'\bDPB\s+(\S+)\s*\(',body):
            for port,mode in re.findall(r'defparam\s+'+re.escape(instance)+r'\.WRITE_MODE([01])\s*=\s*([^;]+);',body):
                mode=re.sub(r'\s+','',mode)
                if mode in ("2'b10","2'd2",'2'):
                    violations.append(f'{module}/{instance}.WRITE_MODE{port}={mode}')
    if violations:
        raise RuntimeError('GW5AST-138B unsupported DPB read-before-write mode (PA2122): '+', '.join(violations))
    return {'status':'passed_known_mode_check_only','netlist':str(Path(path).resolve())}

if __name__=='__main__':print(check(sys.argv[1]))

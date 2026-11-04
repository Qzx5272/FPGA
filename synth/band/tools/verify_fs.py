"""Detect truncated GW5AST ASCII bitstream files; not a vendor checksum decoder."""
from pathlib import Path

def verify_fs(path):
    path=Path(path)
    if path.stat().st_size<1_000_000:raise ValueError('Implausibly short GW5AST bitstream: '+str(path))
    with path.open('rb') as f:
        header=f.read(2048);f.seek(-2048,2);tail=f.read()
    if b'//Device: GW5AST-138' not in header:raise ValueError('Unexpected device header')
    expected=[b'00001000000000000000000000000000',b'1'*64,b'1'*16]
    if tail.splitlines()[-3:]!=expected:raise ValueError('Missing Gowin bitstream termination; possible disk-full truncation')
    return {'file_bytes':path.stat().st_size,'termination_checked':True,'vendor_checksum_decoded':False}

if __name__=='__main__':
    import sys,json
    print(json.dumps(verify_fs(sys.argv[1]),indent=2))

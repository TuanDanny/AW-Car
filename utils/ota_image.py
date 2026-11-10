"""Reject wrong roles/merged images before any network update request."""
import hashlib
from pathlib import Path
import struct

PROJECTS={'brain':'aw_car_brain','motion':'simplev1_motion'}
BINARIES={'brain':'aw_car_brain.bin','motion':'simplev1_motion.bin'}


def inspect_image(path: Path,role: str,manifest: dict) -> dict:
    if manifest.get('board')!=role:
        raise ValueError('Firmware manifest belongs to another board')
    with path.open('rb') as source:
        prefix=source.read(288)
        source.seek(0)
        digest=hashlib.file_digest(source,'sha256').hexdigest()
    if len(prefix)!=288 or prefix[0]!=0xe9 or struct.unpack_from('<H',prefix,12)[0]!=9 or prefix[23]!=1:
        raise ValueError('An ESP32-S3 application image with appended hash is required')
    if struct.unpack_from('<I',prefix,32)[0]!=0xabcd5432:
        raise ValueError('Missing application descriptor; do not upload a merged flash image')
    project=prefix[80:112].split(b'\0',1)[0].decode('ascii',errors='replace')
    if project!=PROJECTS[role]:
        raise ValueError('Application image belongs to another board/project')
    entry=manifest.get('images',{}).get(BINARIES[role],{})
    if entry.get('sha256')!=digest or entry.get('bytes')!=path.stat().st_size:
        raise ValueError('Image size/SHA256 does not match the build manifest')
    if not isinstance(manifest.get('build_id'),str):
        raise ValueError('Build identity missing')
    return {'sha256':digest,'elf_sha256':prefix[176:208].hex(),'bytes':path.stat().st_size,'project':project,'build':manifest['build_id']}

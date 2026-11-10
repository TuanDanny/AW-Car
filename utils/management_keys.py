"""Private development keys. No secrets in Git, console output or HTTP requests."""
import hashlib
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys


def key_file(root: Path, board: str) -> Path:
    directory = Path(os.environ.get('AWCAR_KEY_DIR', root/'build/private/management-keys'))
    return directory / (board + '.key')


def read_key(path: Path) -> str:
    value = path.read_text(encoding='ascii').strip()
    if not re.fullmatch('[0-9a-f]{64}', value):
        raise ValueError('Invalid management key file')
    return value


def prepare(root: Path, board: str, sdk_python: Path) -> tuple[Path, str]:
    path = key_file(root, board)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        pass
    else:
        with os.fdopen(descriptor, 'w', encoding='ascii') as out:
            out.write(secrets.token_hex(32) + '\n')
    key = read_key(path)
    certificate = path.with_suffix('.crt')
    tls_key = path.with_suffix('.tls.key')
    if not certificate.exists() and not tls_key.exists():
        subprocess.run([str(sdk_python), str(Path(__file__).resolve()), '--generate-certificate',
                        str(path), board], check=True)
    if not certificate.exists() or not tls_key.exists():
        raise ValueError('Incomplete local TLS key/certificate pair; restore the private files')
    identity = hashlib.sha256(key.encode() + certificate.read_bytes()).hexdigest()[:12]
    generated = root/'build'/('generated-' + board)
    generated.mkdir(parents=True, exist_ok=True)
    header = generated/'management_key.hpp'
    value = ('#pragma once\nnamespace awcar_private {\n'
             'inline constexpr char key[]="' + key + '";\n'
             'inline constexpr char key_id[]="' + identity + '";\n'
             'inline constexpr char certificate[]=R"AWCAR(' + certificate.read_text() + ')AWCAR";\n'
             'inline constexpr char tls_key[]=R"AWCAR(' + tls_key.read_text() + ')AWCAR";\n}\n')
    if not header.exists() or header.read_text() != value:
        header.write_text(value, encoding='ascii')
    return generated, identity


def generate_certificate(path: Path, board: str):
    from datetime import datetime, timedelta, timezone
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID, ExtendedKeyUsageOID
    private = ec.generate_private_key(ec.SECP256R1())
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'awcar-' + board + '.local')])
    now = datetime.now(timezone.utc)
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(private.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=1)).not_valid_after(now + timedelta(days=3650))
            .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
            .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('awcar-' + board + '.local')]), critical=False)
            .sign(private, hashes.SHA256()))
    for target, data in [(path.with_suffix('.tls.key'), private.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())),
            (path.with_suffix('.crt'), cert.public_bytes(serialization.Encoding.PEM))]:
        descriptor = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(descriptor, 'wb') as out:
            out.write(data)


if __name__ == '__main__':
    if len(sys.argv) != 4 or sys.argv[1] != '--generate-certificate':
        raise SystemExit('Internal certificate generator; run utils/build_esp.py')
    generate_certificate(Path(sys.argv[2]), sys.argv[3])

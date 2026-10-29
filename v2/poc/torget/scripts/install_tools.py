"""Install official project-local authoring tools; selectively fetch Godot templates.
Run with a Python interpreter and network access. No admin privileges required.
"""
from pathlib import Path
import concurrent.futures, hashlib, json, shutil, struct, subprocess, urllib.request, zlib

ROOT = Path(__file__).resolve().parents[3]
DEST = ROOT / '.tools'
CACHE = DEST / 'downloads'
CACHE.mkdir(parents=True, exist_ok=True)
BLENDER_URL = 'https://download.blender.org/release/Blender4.5/blender-4.5.9-macos-arm64.dmg'
GODOT_BASE = 'https://github.com/godotengine/godot/releases/download/4.7.2-stable/'
GODOT_URL = GODOT_BASE + 'Godot_v4.7.2-stable_macos.universal.zip'
TEMPLATE_URL = GODOT_BASE + 'Godot_v4.7.2-stable_export_templates.tpz'
receipt = []


def download(url):
    target = CACHE / url.rsplit('/', 1)[-1]
    expected = int(urllib.request.urlopen(urllib.request.Request(url, method='HEAD')).headers['Content-Length'])
    if not target.exists() or target.stat().st_size != expected:
        partial = target.with_suffix(target.suffix + '.partial')
        print(f'Downloading {target.name}: {expected / 1e6:.1f} MB', flush=True)
        with urllib.request.urlopen(url) as source, partial.open('wb') as sink:
            shutil.copyfileobj(source, sink, 1024 * 1024)
        if partial.stat().st_size != expected:
            raise RuntimeError('Incomplete download: ' + str(target))
        partial.replace(target)
    return target


def read_range(url, start, end):
    request = urllib.request.Request(url, headers={'Range': f'bytes={start}-{end}'})
    with urllib.request.urlopen(request) as response:
        if response.status != 206:
            raise RuntimeError('Server does not support selective range download')
        result = response.read()
    if len(result) != end - start + 1:
        raise RuntimeError('Incorrect range length')
    return result


def templates():
    total = int(urllib.request.urlopen(urllib.request.Request(TEMPLATE_URL, method='HEAD')).headers['Content-Length'])
    tail = read_range(TEMPLATE_URL, total - 65536, total - 1)
    eocd = struct.unpack_from('<4s4H2LH', tail, tail.rfind(b'PK\x05\x06'))
    directory = read_range(TEMPLATE_URL, eocd[6], eocd[6] + eocd[5] - 1)
    output = DEST / 'export_templates' / '4.7.2.stable'
    output.mkdir(parents=True, exist_ok=True)
    selected = {'web_nothreads_release.zip', 'web_nothreads_debug.zip', 'macos.zip', 'version.txt'}
    cursor = 0
    while directory[cursor:cursor + 4] == b'PK\x01\x02':
        entry = struct.unpack_from('<4s6H3L5H2L', directory, cursor)
        name = directory[cursor + 46:cursor + 46 + entry[10]].decode()
        cursor += 46 + entry[10] + entry[11] + entry[12]
        filename = name.rsplit('/', 1)[-1]
        if filename not in selected:
            continue
        target = output / filename
        if target.exists() and target.stat().st_size == entry[9]:
            continue
        offset = entry[16]
        local = struct.unpack('<4s5H3L2H', read_range(TEMPLATE_URL, offset, offset + 29))
        start = offset + 30 + local[9] + local[10]
        print(f'Downloading template {filename}: {entry[8] / 1e6:.1f} MB', flush=True)
        compressed = read_range(TEMPLATE_URL, start, start + entry[8] - 1)
        data = zlib.decompress(compressed, -15) if entry[4] == 8 else compressed
        if len(data) != entry[9] or zlib.crc32(data) != entry[7]:
            raise RuntimeError('Template checksum mismatch: ' + name)
        target.write_bytes(data)
    return output


with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    jobs = [pool.submit(download, BLENDER_URL), pool.submit(download, GODOT_URL), pool.submit(templates)]
    blender_dmg, godot_zip, template_dir = [job.result() for job in jobs]

if not (DEST / 'Godot.app').exists():
    subprocess.run(['ditto', '-x', '-k', str(godot_zip), str(DEST)], check=True)
if not (DEST / 'Blender.app').exists():
    mount = DEST / 'blender-mount'
    mount.mkdir(exist_ok=True)
    subprocess.run(['hdiutil', 'attach', '-nobrowse', '-readonly', '-mountpoint', str(mount), str(blender_dmg)], check=True)
    try:
        subprocess.run(['ditto', str(mount / 'Blender.app'), str(DEST / 'Blender.app')], check=True)
    finally:
        subprocess.run(['hdiutil', 'detach', str(mount)], check=True)
for artifact in [blender_dmg, godot_zip, *template_dir.iterdir()]:
    receipt.append({'file': str(artifact.relative_to(DEST)), 'bytes': artifact.stat().st_size, 'sha256': hashlib.file_digest(artifact.open('rb'), 'sha256').hexdigest()})
(DEST / 'install-receipt.json').write_text(json.dumps(receipt, indent=2))
for executable in [DEST/'Blender.app/Contents/MacOS/Blender', DEST/'Godot.app/Contents/MacOS/Godot']:
    subprocess.run([str(executable), '--version'], check=True)
print('Project-local tools ready at', DEST, flush=True)

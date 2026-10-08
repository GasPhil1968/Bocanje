"""Full build: render -> QA -> OGG -> manifest / guide / QA report -> ZIP (+ ZIP verification).

usage: python3 build.py <work_dir> <zip_out_path>
"""
import os, sys, json, shutil, subprocess, zipfile, wave, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sounds, master, qa, docs

PACK = 'galeb_nad_jadranom_complete_sfx'


def ogg_encode(root, rel_wavs):
    """WAV -> Ogg Vorbis (q5 short SFX, q4 ambience) and decode-verify sample counts."""
    if not shutil.which('ffmpeg'):
        return None
    res = {}
    for rel in rel_wavs:
        src = os.path.join(root, rel)
        dst_rel = os.path.join('ogg', os.path.splitext(rel)[0] + '.ogg')
        dst = os.path.join(root, dst_rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        q = '4' if rel.startswith('ambience') else '5'
        subprocess.run(['ffmpeg', '-nostdin', '-y', '-loglevel', 'error', '-i', src, '-c:a', 'libvorbis', '-q:a', q,
                        '-map_metadata', '-1', dst], check=True)
        with wave.open(src) as w:
            n_wav, ch = w.getnframes(), w.getnchannels()
        dec = subprocess.run(['ffmpeg', '-nostdin', '-loglevel', 'error', '-i', dst, '-f', 's16le', '-acodec', 'pcm_s16le',
                              '-ar', '44100', '-ac', str(ch), '-'], check=True, capture_output=True).stdout
        n_ff = len(dec) // (2 * ch)
        try:                                   # reference libvorbis decode (honours the end granule position)
            import soundfile as sf
            x, _ = sf.read(dst, always_2d=True)
            n_ref = len(x)
        except ImportError:
            x = np.frombuffer(dec, '<i2').astype(float).reshape(-1, ch) / 32768; n_ref = n_ff
        res[rel] = dict(ogg=dst_rel, bytes=os.path.getsize(dst), frames_wav=n_wav, frames_ogg=n_ref, frames_ffmpeg=n_ff,
                        length_match=(n_ref == n_wav), ffmpeg_tail_loss=n_wav - n_ff,
                        peak_dbfs=round(float(20 * np.log10(np.max(np.abs(x)) + 1e-12)), 2))
    return res


def main(work, zip_out):
    t0 = time.time()
    root = os.path.join(work, PACK)
    if os.path.isdir(root):
        shutil.rmtree(root)
    os.makedirs(root)
    print('== render + master')
    info = master.render_all(root)
    print('== QA')
    q = qa.run(root)
    bad = {k: v['problems'] for k, v in q['files'].items() if v['problems']}
    if bad:
        print('QA FAILED:', json.dumps(bad, indent=1))
        sys.exit(1)
    print('== OGG')
    rels = [q['files'][n]['file'] for n in sounds.REG]
    oggs = ogg_encode(root, rels)
    if oggs:
        nbad = [k for k, v in oggs.items() if not v['length_match'] or v['peak_dbfs'] > -1.0
                or (k.startswith('ambience') and v['ffmpeg_tail_loss'] != 0) or v['ffmpeg_tail_loss'] > 256]
        print(f'{len(oggs)} ogg files, length mismatches / overs: {nbad}')
    print('== manifest + docs')
    manifest = docs.manifest(q, oggs)
    with open(os.path.join(root, 'audio_manifest.json'), 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)
    with open(os.path.join(root, 'AUDIO_INTEGRATION_GUIDE.md'), 'w', encoding='utf-8') as f:
        f.write(docs.guide(manifest, q, oggs))
    with open(os.path.join(root, 'AUDIO_QA_REPORT.md'), 'w', encoding='utf-8') as f:
        f.write(docs.qa_report(q, oggs, info))
    print('== zip')
    if os.path.exists(zip_out):
        os.remove(zip_out)
    files = []
    for dp, dn, fn in os.walk(root):
        dn.sort()
        for f in sorted(fn):
            files.append(os.path.join(dp, f))
    with zipfile.ZipFile(zip_out, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in files:
            z.write(p, os.path.relpath(p, work))
    # verify the archive
    with zipfile.ZipFile(zip_out) as z:
        assert z.testzip() is None
        names = set(z.namelist())
    missing = [q['files'][n]['file'] for n in q['files'] if f'{PACK}/{q["files"][n]["file"]}' not in names]
    for extra in ('audio_manifest.json', 'AUDIO_INTEGRATION_GUIDE.md', 'AUDIO_QA_REPORT.md'):
        if f'{PACK}/{extra}' not in names: missing.append(extra)
    nwav = sum(1 for n in names if n.endswith('.wav')); nogg = sum(1 for n in names if n.endswith('.ogg'))
    print(f'zip: {zip_out} {os.path.getsize(zip_out) / 1e6:.1f} MB, {len(names)} entries, {nwav} wav, {nogg} ogg, missing={missing}')
    print(f'done in {time.time() - t0:.0f}s')
    return 0 if not missing else 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))

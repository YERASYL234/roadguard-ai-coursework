"""Source-image-disjoint split, mask-derived patch labels, duplicate audit."""
from pathlib import Path
import hashlib
import json
import random
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def main():
    base = ROOT / 'data/raw/DeepCrack-master/dataset'
    print('Dataset folders:', [str(p.relative_to(base)) for p in base.rglob('*') if p.is_dir()], flush=True)
    pairs = {}
    for split in ['train', 'test']:
        imgs = sorted((base / f'{split}_img').glob('*'))
        masks = {p.stem: p for p in (base / f'{split}_lab').glob('*')}
        pairs[split] = [(p, masks[p.stem]) for p in imgs if p.stem in masks]
    if not all(pairs.values()):
        raise RuntimeError('Original train/test folders not found')
    rng = random.Random(42)
    rng.shuffle(pairs['train'])
    nval = round(len(pairs['train']) * .2)
    pairs['val'] = pairs['train'][:nval]
    pairs['train'] = pairs['train'][nval:]
    rows, seen, removed = [], {}, []
    # Reserve official test images first. Exact RGB duplicate sources cannot leak.
    for split in ['test', 'val', 'train']:
        for src, mask_path in pairs[split]:
            image = Image.open(src).convert('RGB')
            mask = Image.open(mask_path).convert('L')
            digest = hashlib.sha256(image.tobytes()).hexdigest()
            if digest in seen:
                removed.append({'source': str(src), 'duplicate_of': seen[digest]})
                continue
            seen[digest] = str(src)
            if mask.size != image.size:
                raise ValueError(f'Mask size mismatch: {src}')
            w, h = image.size
            # Non-overlapping, approximately 128px tiles; no artificial negatives.
            nx, ny = max(1, round(w/128)), max(1, round(h/128))
            for y in range(ny):
                for x in range(nx):
                    box = (x*w//nx, y*h//ny, (x+1)*w//nx, (y+1)*h//ny)
                    coverage = float((np.asarray(mask.crop(box)) > 127).mean())
                    label = int(coverage > 0)  # Every annotated crack counts, including thin ones.
                    relative = f'data/patches/{split}/{src.stem}_{x}_{y}.png'
                    out = ROOT / relative
                    out.parent.mkdir(parents=True, exist_ok=True)
                    image.crop(box).save(out)
                    rows.append({'path': relative, 'split': split, 'label': label,
                                 'source': src.name, 'source_sha256': digest,
                                 'mask_coverage': coverage, 'box': box})
    (ROOT / 'data/manifest.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    stats = {s: {'sources': len({r['source_sha256'] for r in rows if r['split']==s}),
                  'patches': sum(r['split']==s for r in rows),
                  'positive': sum(r['split']==s and r['label']==1 for r in rows),
                  'negative': sum(r['split']==s and r['label']==0 for r in rows)} for s in pairs}
    stats['duplicates_removed'] = removed
    (ROOT / 'data/split_summary.json').write_text(json.dumps(stats, indent=2), encoding='utf-8')
    print(json.dumps(stats, indent=2), flush=True)

if __name__ == '__main__':
    main()

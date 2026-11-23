"""Download the original DeepCrack educational dataset and ImageNet weights."""
from pathlib import Path
import hashlib
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    raw = ROOT / 'data' / 'raw'
    raw.mkdir(parents=True, exist_ok=True)
    url = 'https://codeload.github.com/yhlleo/DeepCrack/zip/refs/heads/master'
    archive = raw / 'DeepCrack.zip'
    if not archive.exists():
        print('Downloading original DeepCrack dataset...', flush=True)
        urllib.request.urlretrieve(url, archive.with_suffix('.part'))
        archive.with_suffix('.part').replace(archive)
    with zipfile.ZipFile(archive) as z:
        for item in z.infolist():
            if '/dataset/' in item.filename or item.filename.endswith('/README.md'):
                target = (raw / item.filename).resolve()
                if not target.is_relative_to(raw.resolve()):
                    raise ValueError('Unsafe archive path')
                z.extract(item, raw)
    nested = raw / 'DeepCrack-master/dataset/DeepCrack.zip'
    with zipfile.ZipFile(nested) as z:
        for item in z.infolist():
            target = (nested.parent / item.filename).resolve()
            if not target.is_relative_to(nested.parent.resolve()):
                raise ValueError('Unsafe nested archive path')
            z.extract(item, nested.parent)
    (raw / 'provenance.json').write_text(json.dumps({
        'dataset': 'DeepCrack', 'source': 'https://github.com/yhlleo/DeepCrack',
        'download': url, 'archive_sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
        'license': 'Non-commercial research and educational use only; see original README.',
        'citation': 'Liu et al. DeepCrack, Neurocomputing 338 (2019), 139–153. DOI:10.1016/j.neucom.2019.01.036'
    }, indent=2), encoding='utf-8')
    import torch
    from torchvision.models import resnet18, ResNet18_Weights
    torch.hub.set_dir(str(ROOT / 'models' / 'pretrained'))
    resnet18(weights=ResNet18_Weights.DEFAULT)
    print('Dataset and pretrained weights ready.', flush=True)

if __name__ == '__main__':
    main()

"""Train a nonlinear neural head on ImageNet ResNet18 features; select only on val."""
from pathlib import Path
import argparse
import copy
import json
import random
import sys
import time
import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from model import CrackNet, TRANSFORM
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

def scores(y, p, threshold):
    pred = p >= threshold
    return { 'accuracy': float(accuracy_score(y, pred)),
             'precision': float(precision_score(y, pred, zero_division=0)),
             'recall': float(recall_score(y, pred, zero_division=0)),
             'f1': float(f1_score(y, pred, zero_division=0)) }

class Patches(Dataset):
    def __init__(self, rows): self.rows = rows
    def __len__(self): return len(self.rows)
    def __getitem__(self, i):
        with Image.open(ROOT / self.rows[i]['path']) as im:
            return TRANSFORM(im.convert('RGB'))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--epochs', type=int, default=100)
    ap.add_argument('--evaluate', action='store_true', help='Evaluate the frozen selected checkpoint once on test')
    args = ap.parse_args()
    torch.set_num_threads(6)
    torch.manual_seed(42); np.random.seed(42); random.seed(42)
    rows = json.loads((ROOT/'data/manifest.json').read_text())
    model = CrackNet()
    model.backbone.load_state_dict({k:v for k,v in torch.load(ROOT/'models/pretrained/checkpoints/resnet18-f37072fd.pth', weights_only=True).items() if not k.startswith('fc.')}, strict=True)
    cache = ROOT / 'data/features.pt'
    if cache.exists():
        features = torch.load(cache, weights_only=True)
    else:
        features = {}
        model.eval()
        for split in ['train','val','test']:
            subset = [r for r in rows if r['split']==split]
            chunks = []
            loader = DataLoader(Patches(subset), batch_size=64, num_workers=0)
            with torch.inference_mode():
                for i, batch in enumerate(loader):
                    chunks.append(model.backbone(batch))
                    if i % 10 == 0: print(f'Extract {split}: {i+1}/{len(loader)}', flush=True)
            features[split] = {'x': torch.cat(chunks), 'y': torch.tensor([r['label'] for r in subset], dtype=torch.float32)}
        torch.save(features, cache)
    if args.evaluate:
        ck = torch.load(ROOT/'models/cracknet.pt', weights_only=True)
        model.load_state_dict(ck['state_dict']); model.eval()
        with torch.inference_mode(): p = model.head(features['test']['x']).squeeze(-1).sigmoid().numpy()
        y = features['test']['y'].numpy()
        result = scores(y,p,ck['threshold'])
        report = {'model':'ResNet18 + trained MLP head', 'dataset':'DeepCrack',
            'task':'Binary classification of non-overlapping image patches; not severity or segmentation accuracy',
            'test':result, 'test_samples':len(y), 'threshold':ck['threshold'],
            'validation':ck['validation'], 'best_epoch':ck['epoch'],
            'confusion_matrix':confusion_matrix(y,p>=ck['threshold']).tolist(),
            'class_order':['no_crack','crack'], 'split':json.loads((ROOT/'data/split_summary.json').read_text()),
            'seed':42, 'target_met_85':all(v>=.85 for v in result.values()),
            'minimum_met_80':all(v>=.8 for v in result.values())}
        (ROOT/'reports/metrics.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        predictions = [{'path':r['path'],'target':r['label'],'probability':float(prob)} for r,prob in zip([r for r in rows if r['split']=='test'],p)]
        (ROOT/'reports/test_predictions.json').write_text(json.dumps(predictions,indent=2))
        print(json.dumps(report,indent=2), flush=True)
        return
    train, val = features['train'], features['val']
    # Frozen CNN transfer learning: only train split changes learned head parameters.
    optimizer = torch.optim.AdamW(model.head.parameters(), lr=.001, weight_decay=.01)
    weight = (1-train['y']).sum()/train['y'].sum()
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=weight)
    best, history = -1., []
    (ROOT/'models').mkdir(exist_ok=True); (ROOT/'reports').mkdir(exist_ok=True)
    start = time.time()
    for epoch in range(1,args.epochs+1):
        model.head.train(); total = 0.
        for ix in torch.randperm(len(train['y'])).split(128):
            optimizer.zero_grad()
            loss = loss_fn(model.head(train['x'][ix]).squeeze(-1), train['y'][ix])
            loss.backward(); optimizer.step(); total += loss.item()*len(ix)
        model.head.eval()
        with torch.inference_mode(): p = model.head(val['x']).squeeze(-1).sigmoid().numpy()
        y = val['y'].numpy()
        candidates = [(float(t),scores(y,p,t)) for t in np.arange(.15,.851,.025)]
        threshold, metrics = max(candidates,key=lambda c:(min(c[1].values()),c[1]['f1']))
        criterion = min(metrics.values())
        history.append({'epoch':epoch, 'loss':total/len(train['y']), 'val':metrics,'threshold':threshold})
        if criterion > best:
            best = criterion
            torch.save({'state_dict':copy.deepcopy(model.state_dict()), 'threshold':threshold,
                        'epoch':epoch,'validation':metrics,'image_size':128,
                        'architecture':'resnet18_mlp','seed':42}, ROOT/'models/cracknet.pt')
        if epoch % 10 == 0 or epoch==1:
            print(f'Epoch {epoch}/{args.epochs} val={metrics} best_min={best:.4f}',flush=True)
    (ROOT/'reports/training_history.json').write_text(json.dumps(history,indent=2))
    print(f'Training finished in {time.time()-start:.1f}s. Best validation minimum: {best:.4f}',flush=True)

if __name__=='__main__': main()

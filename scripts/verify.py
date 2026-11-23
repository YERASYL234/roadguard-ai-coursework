"""Integration checks against the running local server, no synthetic metric claims."""
from pathlib import Path
import argparse
import hashlib
import json
import urllib.request
import urllib.error

ROOT=Path(__file__).resolve().parents[1]
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--port',type=int,default=8000);args=ap.parse_args()
    base=f'http://127.0.0.1:{args.port}'
    def get(path):
        with urllib.request.urlopen(base+path,timeout=30) as r:return r.status,r.read()
    def post(raw):
        req=urllib.request.Request(base+'/api/predict',data=raw,headers={'Content-Type':'image/jpeg','X-Demo-Road':'2'})
        with urllib.request.urlopen(req,timeout=60) as r:return json.load(r)
    assert get('/')[0]==200
    assert json.loads(get('/api/health')[1])['ready']
    report=json.loads(get('/api/metrics')[1])
    assert report==json.loads((ROOT/'reports/metrics.json').read_text())
    rows=json.loads((ROOT/'data/manifest.json').read_text())
    groups={s:{r['source_sha256'] for r in rows if r['split']==s} for s in ['train','val','test']}
    assert not(groups['train']&groups['val'] or groups['train']&groups['test'] or groups['val']&groups['test'])
    findings=[]
    for sample in json.loads((ROOT/'web/samples.json').read_text(encoding='utf-8')):
        result=post((ROOT/'web'/sample['url'].lstrip('/')).read_bytes())
        assert result['level'] in ('clear','damage','danger')
        assert result['total_tiles']==len(result['cells'])
        assert 0<=result['affected_tile_fraction']<=1
        assert result['road_is_demo'] and '32' in result['road']
        assert result['width']<=1024 and result['height']<=1024
        assert all(0<=cell['probability']<=1 for cell in result['cells'])
        findings.append({'sample':sample['filename'],'level':result['level'],
                         'positive_tiles':result['positive_tiles'],'tiles':result['total_tiles'],
                         'elapsed_ms':result['elapsed_ms']})
    try:post(b'not an image')
    except urllib.error.HTTPError as err:assert err.code==400
    else:raise AssertionError('Invalid upload accepted')
    for path in ['/unknown','/samples/../app.py']:
        try:get(path)
        except urllib.error.HTTPError as err:assert err.code==404
        else:raise AssertionError('Unexpected file exposure')
    # Recompute binary metrics from saved test predictions, not display constants.
    predictions=json.loads((ROOT/'reports/test_predictions.json').read_text())
    tp=tn=fp=fn=0
    for r in predictions:
        pred=r['probability']>=report['threshold']
        tp+=int(pred and r['target']==1);tn+=int(not pred and r['target']==0)
        fp+=int(pred and r['target']==0);fn+=int(not pred and r['target']==1)
    expected={'accuracy':(tp+tn)/len(predictions),'precision':tp/(tp+fp),'recall':tp/(tp+fn),'f1':2*tp/(2*tp+fp+fn)}
    assert all(abs(expected[k]-report['test'][k])<1e-10 for k in expected)
    result={'passed':True,'checks':['HTTP UI and health','real model inference on 3 files','invalid image rejection',
              '404 / traversal protection','source image SHA256 split isolation','metrics independently recomputed'],
              'examples':findings,'checkpoint_sha256':hashlib.sha256((ROOT/'models/cracknet.pt').read_bytes()).hexdigest()}
    (ROOT/'reports/verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()

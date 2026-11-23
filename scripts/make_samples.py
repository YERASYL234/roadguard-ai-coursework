"""Prepare UI examples by annotation coverage only, never by model correctness."""
from pathlib import Path
import json
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
rows=json.loads((ROOT/'data/manifest.json').read_text())
test=[r for r in rows if r['split']=='test']
out=ROOT/'web/samples';out.mkdir(parents=True,exist_ok=True)
samples=[]
# A real healthy patch, a full photo, and a second full photo with higher annotation coverage.
healthy=next(r for r in test if r['label']==0)
sources={r['source']:[] for r in test}
for r in test:sources[r['source']].append(r)
ordered=sorted(sources,key=lambda name:sum(r['mask_coverage'] for r in sources[name])/len(sources[name]))
localized=min(sorted(sources),key=lambda name:sum(r['label'] for r in sources[name]))
choices=[(ROOT/healthy['path'],'Жарықсыз бөлік','healthy.jpg'),
         (ROOT/'data/raw/DeepCrack-master/dataset/test_img'/localized,'Жергілікті жарық','road.jpg'),
         (ROOT/'data/raw/DeepCrack-master/dataset/test_img'/ordered[len(ordered)*9//10],'Айқын жарықтар','cracks.jpg')]
for src,label,name in choices:
    with Image.open(src) as im:im.convert('RGB').save(out/name,quality=95)
    samples.append({'url':'/samples/'+name,'filename':name,'label':label,'source':str(src.relative_to(ROOT))})
(ROOT/'web/samples.json').write_text(json.dumps(samples,ensure_ascii=False,indent=2),encoding='utf-8')
print('3 examples ready')

"""RoadGuard local inference server: python app.py --port 8000."""
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlsplit
import argparse
import base64
import io
import json
import math
import threading
import time
import warnings
import torch
from PIL import Image, ImageOps, UnidentifiedImageError
from model import CrackNet, TRANSFORM

ROOT = Path(__file__).resolve().parent
MAX_UPLOAD = 12 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 25_000_000
warnings.simplefilter('error', Image.DecompressionBombWarning)
ROADS = ['Астана — Қарағанды · М-36', 'Алматы — Қонаев · А-3', 'Қызылорда — Шымкент · М-32', 'Ақтөбе — Орал · А-27']

class Predictor:
    def __init__(self):
        torch.set_num_threads(4)
        ck = torch.load(ROOT/'models/cracknet.pt',map_location='cpu',weights_only=True)
        self.model = CrackNet()
        self.model.load_state_dict(ck['state_dict']); self.model.eval()
        self.threshold = ck['threshold']
        self.lock = threading.Lock()

    def predict(self, raw, road=0):
        started = time.perf_counter()
        with Image.open(io.BytesIO(raw)) as opened:
            if opened.format not in ('JPEG','PNG','WEBP'):
                raise ValueError('JPG, PNG немесе WebP фотосын таңдаңыз.')
            image = ImageOps.exif_transpose(opened).convert('RGB')
        if min(image.size) < 64:
            raise ValueError('Сурет өлшемі кемінде 64 × 64 болуы керек.')
        original_size = image.size
        image.thumbnail((1024,1024))
        w,h = image.size
        nx,ny = max(1,round(w/128)),max(1,round(h/128))
        boxes = [(x*w//nx,y*h//ny,(x+1)*w//nx,(y+1)*h//ny) for y in range(ny) for x in range(nx)]
        batch = torch.stack([TRANSFORM(image.crop(b)) for b in boxes])
        with self.lock, torch.inference_mode():
            probabilities = torch.cat([self.model(b).sigmoid() for b in batch.split(32)]).tolist()
        cells = [{'box':list(b),'probability':round(p,5),'crack':p>=self.threshold} for b,p in zip(boxes,probabilities)]
        area = sum((c['box'][2]-c['box'][0])*(c['box'][3]-c['box'][1]) for c in cells if c['crack'])/(w*h)
        # Transparent demonstration rule, NOT a separately trained severity classifier.
        level = 'danger' if area>=.35 else 'damage' if area>0 else 'clear'
        buffer = io.BytesIO(); image.save(buffer,format='JPEG',quality=88)
        return {'level':level,'affected_tile_fraction':round(area,4),
            'max_crack_score':round(max(probabilities),4), 'threshold':self.threshold,
            'cells':cells,'positive_tiles':sum(c['crack'] for c in cells),'total_tiles':len(cells),
            'width':w,'height':h,'original_size':list(original_size),
            'preview':'data:image/jpeg;base64,'+base64.b64encode(buffer.getvalue()).decode(),
            'road':ROADS[road%len(ROADS)],'road_is_demo':True,
            'elapsed_ms':round((time.perf_counter()-started)*1000),
            'severity_method':'Demo rule: 0% clear, >0–<35% damage, >=35% danger; fraction of positive tiles, not crack pixels.',
            'model':'ResNet18 + MLP', 'timestamp':time.strftime('%Y-%m-%dT%H:%M:%S%z')}

class Handler(BaseHTTPRequestHandler):
    predictor = None
    def send_bytes(self,body,status=200,mime='application/json; charset=utf-8'):
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Cache-Control','no-store')
        self.end_headers(); self.wfile.write(body)
    def send_json(self,value,status=200):
        self.send_bytes(json.dumps(value,ensure_ascii=False).encode(),status)
    def do_GET(self):
        path = urlsplit(self.path).path
        if path=='/api/health':
            return self.send_json({'ready':True,'model':'ResNet18 + MLP'})
        if path=='/api/metrics':
            report=ROOT/'reports/metrics.json'
            return self.send_bytes(report.read_bytes()) if report.exists() else self.send_json({'error':'Evaluation not completed'},503)
        if path=='/api/samples':
            return self.send_json(json.loads((ROOT/'web/samples.json').read_text(encoding='utf-8')))
        allowed = {'/':('index.html','text/html; charset=utf-8'),'/app.js':('app.js','text/javascript; charset=utf-8'),'/style.css':('style.css','text/css; charset=utf-8')}
        if path in allowed:
            name,mime=allowed[path]; return self.send_bytes((ROOT/'web'/name).read_bytes(),mime=mime)
        if path.startswith('/samples/'):
            name=path.removeprefix('/samples/')
            if name and Path(name).name==name and (ROOT/'web/samples'/name).is_file():
                return self.send_bytes((ROOT/'web/samples'/name).read_bytes(),mime='image/jpeg')
        self.send_json({'error':'Not found'},404)
    def do_POST(self):
        if urlsplit(self.path).path!='/api/predict': return self.send_json({'error':'Not found'},404)
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length<=0 or length>MAX_UPLOAD: return self.send_json({'error':'Файл бос немесе 12 МБ шегінен үлкен.'},413)
            self.connection.settimeout(30)
            raw=self.rfile.read(length)
            if len(raw)!=length: raise ValueError('Файл толық жүктелмеді.')
            road=int(self.headers.get('X-Demo-Road','0'))
            result=self.predictor.predict(raw,road)
            self.send_json(result)
        except (ValueError,UnidentifiedImageError,Image.DecompressionBombError,Image.DecompressionBombWarning,OSError):
            self.send_json({'error':'Фотосуретті оқу мүмкін емес. JPG/PNG/WebP, 64 px–25 MP, 12 МБ дейін.'},400)
        except Exception as exc:
            print(f'Prediction error: {type(exc).__name__}: {exc}',flush=True)
            self.send_json({'error':'Талдау қатесі. Сервер журналын тексеріңіз.'},500)

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--port',type=int,default=8000); args=ap.parse_args()
    if not (ROOT/'models/cracknet.pt').exists():
        raise SystemExit('Model missing. Run scripts/train.py first.')
    Handler.predictor=Predictor()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'RoadGuard ready: http://127.0.0.1:{args.port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()

if __name__=='__main__': main()

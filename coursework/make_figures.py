from pathlib import Path
import json
import subprocess
from PIL import Image,ImageDraw,ImageFont,ImageOps
from reportlab.graphics.shapes import Drawing,String
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics import renderPDF
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'coursework/figures';OUT.mkdir(exist_ok=True)
FONT='C:/Windows/Fonts/times.ttf';BOLD='C:/Windows/Fonts/timesbd.ttf'
def font(size=28,bold=False):return ImageFont.truetype(BOLD if bold else FONT,size)
def text(draw,xy,s,size=28,bold=False,anchor='mm',fill='#142c40'):
    draw.multiline_text(xy,s,font=font(size,bold),anchor=anchor,align='center',fill=fill,spacing=9)
def box(draw,bounds,label,fill='#f0f5f7',size=29):
    draw.rounded_rectangle(bounds,radius=12,fill=fill,outline='#52768a',width=3)
    text(draw,((bounds[0]+bounds[2])/2,(bounds[1]+bounds[3])/2),label,size)
def arrow(draw,a,b):
    draw.line([a,b],fill='#4c6677',width=4)
    x,y=b
    if abs(a[0]-b[0])>abs(a[1]-b[1]):draw.polygon([(x,y),(x-15,y-9),(x-15,y+9)],fill='#4c6677')
    else:draw.polygon([(x,y),(x-9,y-15),(x+9,y-15)],fill='#4c6677')

im=Image.new('RGB',(1500,660),'white');d=ImageDraw.Draw(im)
items=[(40,80,350,235,'RGB бөлік\n128 × 128'),(420,80,850,235,'ResNet18 backbone\nImageNet салмақтары'),(930,80,1460,235,'512 өлшемді\nбелгі векторы')]
for x1,y1,x2,y2,s in items:box(d,(x1,y1,x2,y2),s)
arrow(d,(350,157),(420,157));arrow(d,(850,157),(930,157));arrow(d,(1195,235),(1195,340))
box(d,(930,340,1460,500),'Linear 512 → 128\nReLU + Dropout 0,3','#fcf4e7')
box(d,(420,340,850,500),'Linear 128 → 1\nлогит → sigmoid','#fcf4e7')
box(d,(40,340,350,500),'p ≥ 0,65\nжарық бар / жоқ')
d.line([(930,420),(850,420)],fill='#4c6677',width=4);d.polygon([(850,420),(865,411),(865,429)],fill='#4c6677')
d.line([(420,420),(350,420)],fill='#4c6677',width=4);d.polygon([(350,420),(365,411),(365,429)],fill='#4c6677')
text(d,(750,580),'Backbone бекітілген. Сары блоктардағы head параметрлері оқытылады.',28)
im.save(OUT/'architecture.png')

im=Image.new('RGB',(1500,780),'white');d=ImageDraw.Draw(im)
text(d,(750,40),'Оқыту тармағы',32,True)
for b,s in [((40,85,400,225),'DeepCrack\nсурет + маска'),((560,85,940,225),'Дайындау және\nMLP head оқыту'),((1100,85,1460,225),'cracknet.pt\nсалмақтар + шек')]:box(d,b,s)
arrow(d,(400,155),(560,155));arrow(d,(940,155),(1100,155))
text(d,(750,305),'Пайдаланушы фотосын өңдеу',32,True)
for b,s in [((40,355,400,510),'Браузер\nфото + демо трасса'),((560,355,940,510),'Python сервері\nдайындау + модель'),((1100,355,1460,510),'JSON жауап\nтор + деңгей')]:box(d,b,s)
arrow(d,(400,430),(560,430));arrow(d,(940,430),(1100,430));d.line([(1280,225),(1280,260),(750,260)],fill='#4c6677',width=4);arrow(d,(750,260),(750,355))
box(d,(560,595,940,725),'Canvas және тарих\nJSON есепті жүктеу')
d.line([(1280,510),(1280,660),(940,660)],fill='#4c6677',width=4);d.polygon([(940,660),(955,651),(955,669)],fill='#4c6677')
im.save(OUT/'system.png')

rows=json.loads((ROOT/'data/manifest.json').read_text());preds=json.loads((ROOT/'reports/test_predictions.json').read_text());lookup={r['path']:r for r in rows}
base=ROOT/'data/raw/DeepCrack-master/dataset'
sample='11236-1.jpg';photo=Image.open(base/'test_img'/sample).convert('RGB');mask=Image.open(base/'test_lab'/Path(sample).with_suffix('.png')).convert('RGB') if (base/'test_lab'/Path(sample).with_suffix('.png')).exists() else Image.open(next((base/'test_lab').glob(Path(sample).stem+'.*'))).convert('RGB')
im=Image.new('RGB',(1500,850),'white');d=ImageDraw.Draw(im)
for j,(pic,label) in enumerate([(photo,'Бастапқы RGB сурет'),(mask,'Авторлық жарық маскасы')]):
    p=ImageOps.contain(pic,(700,450));x=30+j*750;im.paste(p,(x,70));text(d,(x+350,35),label,30,True)
sub=[r for r in rows if r['source']==sample and r['split']=='test']
examples=[next(r for r in sub if r['label']==0),next(r for r in sub if r['label']==1)]
for j,r in enumerate(examples):
    p=Image.open(ROOT/r['path']).convert('RGB').resize((240,220));x=420+j*430;im.paste(p,(x,560));text(d,(x+120,815),f"label = {r['label']}",27)
text(d,(750,540),'Маскадан алынған бөлік белгілері',28,True)
im.save(OUT/'dataset.png')

pdfmetrics.registerFont(TTFont('TimesLocal',FONT))
hist=json.loads((ROOT/'reports/training_history.json').read_text())
chart=Drawing(900,340)
for j,(key,label) in enumerate([('loss','Train loss'),('f1','Validation F1')]):
    lp=LinePlot();lp.x=60+j*445;lp.y=55;lp.width=365;lp.height=235
    lp.data=[[(h['epoch'],h['loss'] if key=='loss' else h['val']['f1']) for h in hist]]
    lp.xValueAxis.valueMin=1;lp.xValueAxis.valueMax=100;lp.xValueAxis.valueSteps=[1,18,40,60,80,100]
    lp.yValueAxis.valueMin=0 if key=='loss' else .85;lp.yValueAxis.valueMax=.7 if key=='loss' else .96
    lp.yValueAxis.labels.fontName='TimesLocal';lp.xValueAxis.labels.fontName='TimesLocal'
    lp.yValueAxis.labels.fontSize=11;lp.xValueAxis.labels.fontSize=11
    lp.lines[0].strokeColor=colors.HexColor('#285776' if j==0 else '#2e7d52');lp.lines[0].strokeWidth=1.8
    lp.yValueAxis.visibleGrid=1;lp.yValueAxis.gridStrokeColor=colors.HexColor('#dddddd')
    chart.add(lp);chart.add(String(230+j*445,310,label,fontName='TimesLocal',fontSize=16,textAnchor='middle'))
    chart.add(String(230+j*445,17,'Epoch',fontName='TimesLocal',fontSize=12,textAnchor='middle'))
renderPDF.drawToFile(chart,str(OUT/'learning.pdf'))
subprocess.run([r'C:\Users\alpys\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe','-png','-scale-to','1800','-singlefile',str(OUT/'learning.pdf'),str(OUT/'learning')],check=True)

fp=next(r for r in preds if r['target']==0 and r['probability']>=.65)
fn=next(r for r in preds if r['target']==1 and r['probability']<.65)
im=Image.new('RGB',(1500,720),'white');d=ImageDraw.Draw(im)
for j,(r,title) in enumerate([(fp,'Жалған оң болжам FP'),(fn,'Жалған теріс болжам FN')]):
    m=lookup[r['path']];src=next((base/'test_lab').glob(Path(m['source']).stem+'.*'))
    patch=Image.open(ROOT/r['path']).convert('RGB');gt=Image.open(src).crop(m['box']).convert('RGB')
    x=j*750; text(d,(x+375,45),title,32,True)
    im.paste(patch.resize((330,330)),(x+30,100));im.paste(gt.resize((330,330)),(x+390,100))
    text(d,(x+195,470),'RGB бөлік',28);text(d,(x+555,470),'Эталон маска',28)
    text(d,(x+375,535),f"Нақты label = {r['target']}; p = {r['probability']:.3f}",28)
    text(d,(x+375,585),Path(r['path']).name,23)
text(d,(750,665),'Шешім шегі 0,65. Мысалдар сақталған test болжамдарынан алынды.',27)
im.save(OUT/'errors.png')
print('Figures ready')

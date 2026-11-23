"""Use packaged render_docx rasterization with a Word-exported PDF on Windows."""
from pathlib import Path
import importlib.util
import os
import sys
import tempfile

ROOT=Path(__file__).resolve().parent
os.environ['PATH']=r'C:\Users\alpys\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin'+os.pathsep+os.environ['PATH']
(ROOT/'tmp').mkdir(exist_ok=True)
tempfile.tempdir=str(ROOT/'tmp')
skill=Path(r'C:\Users\alpys\.codex\plugins\cache\openai-primary-runtime\documents\26.1017.22136\skills\documents')
spec=importlib.util.spec_from_file_location('renderer',skill/'render_docx.py')
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)
pdf=Path(sys.argv[1]).resolve();out=Path(sys.argv[2]).resolve()
renderer.convert_to_pdf=lambda *a,**kw:(str(pdf),'PDF exported by Microsoft Word; bundled LibreOffice unavailable.')
renderer.rasterize(str(pdf.with_suffix('.docx')),str(out),110,False,False)
from PIL import Image,ImageOps,ImageDraw
files=sorted(out.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
for batch in range(0,len(files),8):
    sheet=Image.new('RGB',(1000,1440),'#d7d7d7');draw=ImageDraw.Draw(sheet)
    for j,p in enumerate(files[batch:batch+8]):
        im=Image.open(p);im.thumbnail((480,330))
        x=(j%2)*500+(500-im.width)//2;y=(j//2)*360+20
        sheet.paste(im,(x,y));draw.text(((j%2)*500+10,y-16),p.stem,fill='black')
    sheet.save(out/f'contact-{batch//8+1}.png')
print('Rendered',len(files),'pages')

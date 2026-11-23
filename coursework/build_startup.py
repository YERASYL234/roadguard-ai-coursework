from pathlib import Path
from copy import deepcopy
from lxml import etree as E
import zipfile, hashlib, json

ROOT=Path(__file__).resolve().parents[1]
W=ROOT/'coursework'/'startup';W.mkdir(exist_ok=True)
SOURCE=Path(r'C:\Users\alpys\Downloads\Айболатқызы Қарлығаш_СРО_SuBalans_.docx')
OUT=ROOT/'RoadGuard_AI_стартап_есебі.docx'
ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main','wp':'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
def q(t):return '{'+ns[t.split(':')[0]]+'}'+t.split(':')[1]
with zipfile.ZipFile(SOURCE) as z: parts={n:z.read(n) for n in z.namelist()}
root=E.fromstring(parts['word/document.xml']);body=root.find('w:body',ns)
ps=body.findall('w:p',ns);tables=body.findall('w:tbl',ns)
base=deepcopy(ps[6]);head=deepcopy(ps[2]);title=deepcopy(ps[0]);bullet=deepcopy(ps[10]);imagep=deepcopy(next(p for p in ps if p.find('.//w:drawing',ns) is not None));sect=deepcopy(body.find('w:sectPr',ns))
inventory={n:{'size':len(v),'sha256':hashlib.sha256(v).hexdigest()} for n,v in parts.items()}
(W/'reference_inventory.json').write_text(json.dumps(inventory,indent=2),encoding='utf-8')
(W/'artifact.md').write_text('''Reference: '''+str(SOURCE)+'''\nSHA256: '''+hashlib.sha256(SOURCE.read_bytes()).hexdigest()+'''
16 reference pages; one Letter portrait section, 21.59 x 27.94 cm, all margins 2.54 cm. No visible page numbers or separate title page.
Direct Times New Roman on runs, body 11 pt inherited from docDefaults; line spacing 259/240; paragraph after 8 pt. Heading 1 16 pt bold, before 18 pt after 6 pt; Heading 2 13 pt bold, before 14 pt after 5 pt. Left aligned body, no first-line indent. Preserve source styles, numbering and section XML byte-for-byte. Reference render: ../subalans-render/page-1.png through page-16.png.
All document.xml body content is editable, including 15 numbered section headings, title/date, table cells, bibliography and figure. Rebuild each with clones of original pPr/rPr, source table properties and grids. Table patterns 0..12 mapped in content by @index. Plain grid borders and unshaded headers retained. Clone data rows without source merges. Repeat header and prevent row splitting as pagination repair. Lists retain source numbering. Preserve every package part except document.xml and replaced architecture image. Old unused relationships remain preserved; no visible old content.
Architecture slot replaced with RoadGuard system figure, preserving source drawing but updating aspect ratio and description. Source heading/title style overrides generic Title requirement because user requests template fidelity. No added academic cover or TOC. Body grows or contracts naturally; source page count is not forced.
All project facts derive from README and metrics. Budget and future milestones explicitly planned. Financial tables use recalculated totals. Final gate: Word export then packaged render_docx rasterization, inspect all pages and verify unchanged package parts and source checksum.
''',encoding='utf-8')
def paragraph(template,text):
 p=deepcopy(template);rpr=p.find('.//w:rPr',ns)
 rpr=deepcopy(rpr) if rpr is not None else E.Element(q('w:rPr'))
 for n in list(p):
  if n.tag!=q('w:pPr'):p.remove(n)
 r=E.SubElement(p,q('w:r'));r.append(rpr);t=E.SubElement(r,q('w:t'));t.text=text;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')
 return p
def table(idx,rows):
 template=tables[idx];t=deepcopy(template);old=template.findall('w:tr',ns)
 for r in t.findall('w:tr',ns):t.remove(r)
 for ri,values in enumerate(rows):
  tr=deepcopy(old[0] if ri==0 else old[1])
  pr=tr.find('w:trPr',ns)
  if pr is None:pr=E.Element(q('w:trPr'));tr.insert(0,pr)
  for x in list(pr):
   if x.tag in [q('w:trHeight'),q('w:tblHeader')]:pr.remove(x)
  E.SubElement(pr,q('w:cantSplit'))
  if ri==0:E.SubElement(pr,q('w:tblHeader'))
  cells=tr.findall('w:tc',ns);assert len(cells)==len(values),(idx,len(cells),values)
  for cell,value in zip(cells,values):
   cp=cell.find('w:tcPr',ns)
   if cp is not None:
    for m in cp.findall('w:vMerge',ns):cp.remove(m)
   oldp=cell.find('w:p',ns)
   if idx==4 and cell is cells[0] and ri>0:value=['Талап','Дерек','Модель','Сапа','Пайда'][ri-1]
   p=paragraph(oldp if oldp is not None else base,value)
   if ri==0:
    pp=p.find('w:pPr',ns)
    if pp is None:pp=E.Element(q('w:pPr'));p.insert(0,pp)
    E.SubElement(pp,q('w:keepNext'))
   for x in list(cell):
    if x.tag!=q('w:tcPr'):cell.remove(x)
   cell.append(p)
  t.append(tr)
 return t
for n in list(body):body.remove(n)
lines=(ROOT/'coursework/startup_report.txt').read_text(encoding='utf-8').splitlines();i=0
while i<len(lines):
 line=lines[i];i+=1
 if not line:continue
 if line.startswith('@'):
  idx=int(line[1:]);rows=[]
  while lines[i]!='@end':rows.append(lines[i].split('|'));i+=1
  i+=1;body.append(table(idx,rows));continue
 if line=='IMAGE':body.append(deepcopy(imagep));continue
 if line.startswith('TITLE '):p=paragraph(title,line[6:])
 elif line.startswith('SUB '):p=paragraph(base,line[4:])
 elif line.startswith('# '):p=paragraph(head,line[2:])
 elif line.startswith('- '):p=paragraph(bullet,line[2:])
 else:p=paragraph(base,line)
 body.append(p)
body.append(sect)
# Replace retained figure relationship target without touching relationship XML.
rid=imagep.find('.//a:blip',ns).get(q('r:embed'))
rels=E.fromstring(parts['word/_rels/document.xml.rels'])
target=next(x.get('Target') for x in rels if x.get('Id')==rid)
imagepart='word/'+target
parts[imagepart]=(ROOT/'coursework/figures/system.png').read_bytes()
for drawing in body.findall('.//w:drawing',ns):
 ext=drawing.find('.//wp:extent',ns);cx=int(ext.get('cx'));cy=round(cx*780/1500);ext.set('cy',str(cy))
 for e in drawing.findall('.//a:xfrm/a:ext',ns):e.set('cx',str(cx));e.set('cy',str(cy))
 for e in drawing.findall('.//wp:docPr',ns):e.set('descr','RoadGuard AI жүйесінің деректер қозғалысы');e.set('name','RoadGuard architecture')
parts['word/document.xml']=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
with zipfile.ZipFile(OUT,'w',zipfile.ZIP_DEFLATED) as z:
 for n,v in parts.items():z.writestr(n,v)
changed=[n for n,v in parts.items() if hashlib.sha256(v).hexdigest()!=inventory[n]['sha256']]
assert set(changed)=={'word/document.xml',imagepart},changed
assert 'SuBalans' not in ''.join(body.itertext())
(W/'audit.json').write_text(json.dumps({'changed_parts':changed,'tables':len(body.findall('w:tbl',ns)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'paragraphs':len(body.findall('w:p',ns))},indent=2),encoding='utf-8')
print(OUT)

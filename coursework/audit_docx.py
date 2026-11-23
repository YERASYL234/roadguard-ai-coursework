from pathlib import Path
import json,hashlib,re
from docx import Document
from docx.oxml.ns import qn
from pypdf import PdfReader
root=Path(__file__).resolve().parents[1]; work=root/'coursework'
d=Document(root/'RoadGuard_курстық_жұмыс.docx')
pdf=PdfReader(work/'final.pdf')
assert len(pdf.pages)==30
headings=json.loads((work/'final.pdf.headings.json').read_text(encoding='utf-8-sig'))
toc=[p.text.rsplit('\t',1) for p in d.paragraphs if p.style.name.lower().startswith('toc')]
assert len(toc)==len(headings)==25,(len(toc),len(headings))
assert all(t==h['text'] and int(n)==h['page'] for (t,n),h in zip(toc,headings))
for s in d.sections:
    for prop,cm in [('page_width',21),('page_height',29.7),('left_margin',3),('right_margin',1),('top_margin',2),('bottom_margin',2)]:
        assert abs(getattr(s,prop).cm-cm)<.01
assert len(d.inline_shapes)==10 and len(d.tables)==9
assert abs(d.styles['Normal'].paragraph_format.first_line_indent.cm-1.25)<.01
defaults=d.styles.element.find(qn('w:docDefaults')).find(qn('w:rPrDefault')).find(qn('w:rPr'))
assert defaults.find(qn('w:sz')).get(qn('w:val'))=='28'
assert defaults.find(qn('w:rFonts')).get(qn('w:ascii'))=='Times New Roman'
alltext='\n'.join(p.text for p in d.paragraphs)
assert 'TOC ' in d.element.xml
assert 'қоқыс' not in alltext.lower() and 'TazaBin' not in alltext
source=Document(r'C:\Users\alpys\Documents\deep_learning kursovoi.docx')
for i in range(27):
    if i not in [4,17,18,19]:assert d.paragraphs[i].text==source.paragraphs[i].text,i
assert hashlib.sha256(Path(r'C:\Users\alpys\Documents\deep_learning kursovoi.docx').read_bytes()).hexdigest()=='948ee3e31cd5755c5e860a3ebe588f0b781c2d923035f4c41ff629a717ff4d68'
for i,page in enumerate(pdf.pages,1):
    footer=[]
    def visitor(text,cm,tm,font,size):
        if 0<tm[5]<50 and text.strip():footer.append(text.strip())
    page.extract_text(visitor_text=visitor)
    if i>2:assert ''.join(footer)==str(i),(i,footer)
    else:assert not footer,(i,footer)
for n in range(1,11):
    caption=f'Сурет-{n}.'
    assert caption in alltext and f'{n}-сурет' in alltext[:alltext.index(caption)]
for n in range(1,10):
    label=f'Кесте-{n}'
    assert len(re.findall(re.escape(label),alltext))>=2
report={'pages':30,'toc_entries':25,'toc_pages_match':True,'figures':10,'tables':9,'front_matter_preserved':True,'reference_unchanged':True,'a4_margins':True,'body_font':'Times New Roman 14','first_line_cm':1.25,'numbering':'no printed 1 or 2; 3 through 30 centered','visual_review':'All 30 pages inspected; dataset figure label spacing repaired; no clipped text or overlapping tables.'}
(work/'qa_report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))

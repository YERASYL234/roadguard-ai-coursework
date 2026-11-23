from pathlib import Path
from copy import deepcopy
import hashlib
import json
import re
import zipfile
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT,WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'coursework'
SOURCE=Path(r'C:\Users\alpys\Documents\deep_learning kursovoi.docx')
OUT=ROOT/'RoadGuard_курстық_жұмыс.docx'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()=='948ee3e31cd5755c5e860a3ebe588f0b781c2d923035f4c41ff629a717ff4d68'
doc=Document(SOURCE)
topic='Терең оқыту негізінде жол жабынындағы жарықтарды анықтаудың интеллектуалды жүйесін әзірлеу'
def replace_paragraph(p,text):
    first=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    for child in list(p._p):
        if child.tag!=qn('w:pPr'):p._p.remove(child)
    r=p.add_run(text)
    if first is not None:r._r.insert(0,first)
replace_paragraph(doc.paragraphs[4],'ТАҚЫРЫБЫ: «'+topic+'»')
replace_paragraph(doc.paragraphs[17],'Тақырыбы: '+topic)
replace_paragraph(doc.paragraphs[18],'Мақсатты бағыт: жол фотосынан жарықтарды анықтау, нейрондық модельді оқыту және нәтижені веб-интерфейсте көрсету.')
replace_paragraph(doc.paragraphs[19],'Жұмыс мазмұны: теориялық талдау; жүйені жобалау; датасетті дайындау; модельді оқыту; прототипті іске қосу; нәтижелер мен шектеулерді талдау.')
# Keep the first two sections and all their original front matter.
body=doc._element.body;cut=doc.paragraphs[27]._p
start=list(body).index(cut)
for element in list(body)[start:]:
    if element.tag!=qn('w:sectPr'):body.remove(element)

def set_font(style,size=14,bold=False):
    style.font.name='Times New Roman';style.font.size=Pt(size);style.font.color.rgb=RGBColor(0,0,0);style.font.bold=bold
    rpr=style.element.get_or_add_rPr();rf=rpr.find(qn('w:rFonts'))
    if rf is None:rf=OxmlElement('w:rFonts');rpr.insert(0,rf)
    for key in ['ascii','hAnsi','eastAsia','cs']:rf.set(qn('w:'+key),'Times New Roman')
    for key in ['asciiTheme','hAnsiTheme','eastAsiaTheme','cstheme']:
        rf.attrib.pop(qn('w:'+key),None)

normal=doc.styles['Normal'];set_font(normal)
pf=normal.paragraph_format;pf.first_line_indent=Cm(1.25);pf.line_spacing=1;pf.space_before=Pt(0);pf.space_after=Pt(0);pf.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
pf.widow_control=True
for name in ['Heading 1','Heading 2']:
    s=doc.styles[name];set_font(s,14,True);f=s.paragraph_format
    f.line_spacing=1;f.space_before=Pt(10 if name=='Heading 2' else 0);f.space_after=Pt(6);f.first_line_indent=Cm(1.25);f.keep_with_next=True;f.keep_together=True
    f.page_break_before=name=='Heading 1';f.alignment=WD_ALIGN_PARAGRAPH.LEFT
for name in ['toc 1','toc 2']:
    s=doc.styles[name];set_font(s,12);f=s.paragraph_format;f.first_line_indent=Cm(0);f.space_after=Pt(2);f.space_before=Pt(0);f.line_spacing=1;f.keep_with_next=False;f.alignment=WD_ALIGN_PARAGRAPH.LEFT
    f.left_indent=Cm(.4 if name=='toc 2' else 0)
cap=doc.styles['Caption'];set_font(cap,12);cap.paragraph_format.line_spacing=1;cap.paragraph_format.first_line_indent=Cm(0);cap.paragraph_format.space_after=Pt(6);cap.paragraph_format.space_before=Pt(3)
for section in doc.sections:
    section.page_width=Cm(21);section.page_height=Cm(29.7)
    section.top_margin=Cm(2);section.bottom_margin=Cm(2);section.left_margin=Cm(3);section.right_margin=Cm(1)
    section.footer_distance=Cm(1)
# Keep cover's custom course-title out of the outline and TOC.
for p in doc.paragraphs:
    pp=p._p.get_or_add_pPr();ol=pp.find(qn('w:outlineLvl'))
    if ol is None:ol=OxmlElement('w:outlineLvl');pp.append(ol)
    ol.set(qn('w:val'),'9')

p=doc.add_paragraph('МАЗМҰНЫ');p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.space_after=Pt(8);p.runs[0].bold=True
p=doc.add_paragraph();p.paragraph_format.first_line_indent=Cm(0)
def field(p,instruction,result=''):
    r=p.add_run();begin=OxmlElement('w:fldChar');begin.set(qn('w:fldCharType'),'begin');r._r.append(begin)
    r=p.add_run();ins=OxmlElement('w:instrText');ins.set(qn('xml:space'),'preserve');ins.text=instruction;r._r.append(ins)
    r=p.add_run();sep=OxmlElement('w:fldChar');sep.set(qn('w:fldCharType'),'separate');r._r.append(sep)
    p.add_run(result)
    r=p.add_run();end=OxmlElement('w:fldChar');end.set(qn('w:fldCharType'),'end');r._r.append(end)
field(p,' TOC \\o "1-2" \\h \\z ','Мазмұн Word тақырыптарынан жаңартылады.')

figures=0;tables=0;refs_mode=False;abbrev_mode=False
def add_table(parts):
    global tables
    tables+=1;title=parts[1];rows=[r.split(';') for r in parts[2:]]
    p=doc.add_paragraph(f'Кесте-{tables}');p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.keep_with_next=True
    p=doc.add_paragraph(title);p.paragraph_format.first_line_indent=Cm(1.25);p.paragraph_format.keep_with_next=True;p.paragraph_format.space_after=Pt(4)
    t=doc.add_table(rows=0,cols=len(rows[0]));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    widths={2:[8,9],3:[5.2,6.8,5],5:[4,2.4,3,3.8,3.8]}[len(rows[0])]
    for col,width in zip(t.columns,widths):col.width=Cm(width)
    props=t._tbl.tblPr
    borders=OxmlElement('w:tblBorders')
    for name in ['top','left','bottom','right','insideH','insideV']:
        b=OxmlElement('w:'+name);b.set(qn('w:val'),'single');b.set(qn('w:sz'),'4');b.set(qn('w:color'),'B0B0B0');borders.append(b)
    props.append(borders)
    for i,values in enumerate(rows):
        row=t.add_row();trpr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trpr.append(cant)
        if i==0:
            repeat=OxmlElement('w:tblHeader');trpr.append(repeat)
        for j,(cell,value) in enumerate(zip(row.cells,values)):
            cell.width=Cm(widths[j]);cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text=value;p=cell.paragraphs[0];f=p.paragraph_format;f.first_line_indent=Cm(0);f.line_spacing=1;f.space_before=Pt(3);f.space_after=Pt(3);f.keep_with_next=False
            p.alignment=WD_ALIGN_PARAGRAPH.LEFT if j==0 else WD_ALIGN_PARAGRAPH.CENTER
            for r in p.runs:r.font.size=Pt(12);r.font.name='Times New Roman';r.bold=i==0
            pr=cell._tc.get_or_add_tcPr();mar=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                m=OxmlElement('w:'+side);m.set(qn('w:w'),'65');m.set(qn('w:type'),'dxa');mar.append(m)
            pr.append(mar)

for line in (WORK/'content.txt').read_text(encoding='utf-8').splitlines():
    if not line.strip():continue
    assert '—' not in line,'Long dash in authored text'
    if line.startswith('# '):
        title=line[2:];doc.add_paragraph(title,'Heading 1');refs_mode=title.startswith('ПАЙДАЛАНЫЛҒАН');abbrev_mode=title.startswith('БЕЛГІЛЕУЛЕР')
    elif line.startswith('## '):doc.add_paragraph(line[3:],'Heading 2')
    elif line.startswith('@TABLE|'):add_table(line.split('|'))
    elif line.startswith('@FIG|'):
        figures+=1;_,file,caption,width=line.split('|');path=WORK/'figures'/file
        w,h=Image.open(path).size;cm=float(width)
        limit=10 if file.endswith('-result.png') else 11.6
        if h/w*cm>limit:cm=limit*w/h
        p=doc.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.keep_with_next=True;p.paragraph_format.space_before=Pt(4)
        shape=p.add_run().add_picture(str(path),width=Cm(cm));shape._inline.docPr.set('descr',caption)
        p=doc.add_paragraph(f'Сурет-{figures}. {caption}','Caption');p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    else:
        p=doc.add_paragraph(line)
        if refs_mode:
            p.paragraph_format.first_line_indent=Cm(0);p.paragraph_format.space_after=Pt(4)
            for r in p.runs:r.font.size=Pt(12)
        if abbrev_mode:p.paragraph_format.space_after=Pt(3)

settings=doc.settings.element
up=settings.find(qn('w:updateFields'))
if up is None:up=OxmlElement('w:updateFields');settings.append(up)
up.set(qn('w:val'),'true')
doc.core_properties.title=topic;doc.core_properties.subject='Терең оқыту пәні бойынша курстық жұмыс';doc.core_properties.author='Алпысбайұлы Ерасыл';doc.core_properties.last_modified_by='Алпысбайұлы Ерасыл'
doc.save(OUT)
print(json.dumps({'output':str(OUT),'figures':figures,'tables':tables,'paragraphs':len(doc.paragraphs),'sections':len(doc.sections)},ensure_ascii=False))

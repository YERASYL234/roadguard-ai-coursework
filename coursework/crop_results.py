from pathlib import Path
from PIL import Image
p=Path(__file__).parent
c=p/'content.txt'
s=c.read_text(encoding='utf-8')
for name,box in {'clear':(679,110,1241,954),'damage':(679,110,1241,821),'danger':(679,110,1241,809)}.items():
    Image.open(p/f'figures/ui-{name}.png').crop(box).save(p/f'figures/ui-{name}-result.png')
    s=s.replace(f'@FIG|ui-{name}.png|',f'@FIG|ui-{name}-result.png|')
c.write_text(s,encoding='utf-8')

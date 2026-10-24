"""Memory footer rounded type and photo labels with their original fonts."""
from pathlib import Path
from urllib.request import urlopen
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

ROOT = Path(__file__).resolve().parents[1]
FONT = ROOT / 'assets/fonts/ZenMaruGothic-Medium.ttf'
BUBBLE_URL = 'https://fukidesign.com/e/e1547/m_e1547_0.png'


def lettering(label, size, color='#594537', padding=6):
    font = ImageFont.truetype(str(FONT), size)
    box = font.getbbox(label)
    image = Image.new('RGBA', (box[2]-box[0]+padding*2, box[3]-box[1]+padding*2))
    ImageDraw.Draw(image).text((padding-box[0], padding-box[1]), label, font=font, fill=color)
    return image


def photo_label(label, width=160, font_path='C:/Windows/Fonts/segoeuil.ttf', tail_side='left'):
    # Keep only the text-bearing design in the project, rather than redistribute
    # the site's standalone material. Source and terms are recorded in docs.
    with urlopen(BUBBLE_URL, timeout=30) as response:
        source = Image.open(io.BytesIO(response.read())).convert('RGBA')
    size = (width*3, 46*3)
    # Mirror the original tail-free left half to retain the soft e1547 body,
    # then replace its sideways pointer with a downward photo pointer.
    left = source.getchannel('A').crop((0, 0, source.width//2, source.height))
    body = Image.new('L', (left.width*2, left.height))
    body.paste(left, (0, 0))
    body.paste(left.transpose(Image.Transpose.FLIP_LEFT_RIGHT), (left.width, 0))
    alpha = body.resize((size[0]-12, 96), Image.Resampling.LANCZOS)
    mask = Image.new('L', size)
    mask.paste(alpha, (6, 6))
    tail_x = 150 if tail_side == 'left' else size[0]-150
    ImageDraw.Draw(mask).polygon([(tail_x-24, 86), (tail_x+24, 86),
        (tail_x, size[1]-6)], fill=255)
    border = Image.new('RGBA', size, '#A98B6E')
    border.putalpha(mask.filter(ImageFilter.MaxFilter(5)))
    fill = Image.new('RGBA', size, '#FFFCF4')
    fill.putalpha(mask)
    border.alpha_composite(fill)
    font = ImageFont.truetype(str(font_path), 36)
    box = font.getbbox(label)
    text = Image.new('RGBA', (box[2]-box[0], box[3]-box[1]))
    ImageDraw.Draw(text).text((-box[0], -box[1]), label, font=font, fill='#594537')
    if text.width > size[0]-54:
        ratio = (size[0]-54)/text.width
        text = text.resize((round(text.width*ratio), round(text.height*ratio)), Image.Resampling.LANCZOS)
    border.alpha_composite(text, ((size[0]-text.width)//2, (108-text.height)//2))
    return border

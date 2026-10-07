"""Subsets Arimo Regular/Bold to Latin and writes WOFF2 copies next to the TTFs.

    venv/bin/pip install fonttools brotli
    venv/bin/python tools/make_arimo_woff2.py

The Odds client loads the .woff2 files (about 20 KB each instead of about 318 KB as TTF). Characters outside
this set fall back to the system font, same as before for anything Arimo lacked.
"""
import os
from fontTools import subset

FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'client', 'odds_src', 'assets', 'fonts')

# basic Latin, Latin-1 (accents, ©, ×), general punctuation, arrows, minus sign
UNICODES = (
    list(range(0x20, 0x7F)) + list(range(0xA0, 0x100)) + [0x2013, 0x2014, 0x2018, 0x2019, 0x201C, 0x201D, 0x2022, 0x2026, 0x2190, 0x2191, 0x2192, 0x2193, 0x2212]
)

for name in ('Arimo-Regular', 'Arimo-Bold'):
    src = os.path.join(FONT_DIR, name + '.ttf')
    out = os.path.join(FONT_DIR, name + '.woff2')
    options = subset.Options()
    options.flavor = 'woff2'
    options.layout_features = ['*']
    options.notdef_outline = True
    font = subset.load_font(src, options)
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=UNICODES)
    subsetter.subset(font)
    subset.save_font(font, out, options)
    print(f'{name}: {os.path.getsize(src) // 1024} KB ttf -> {os.path.getsize(out) // 1024} KB woff2')

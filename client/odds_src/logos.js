// team abbreviation -> logo URL (Vite fingerprints the files in assets/logos/).
// no-inline keeps them as separate files: inlined, all 32 would bloat the main bundle for every visitor.
const files = import.meta.glob('./assets/logos/*.png', { eager: true, query: '?url&no-inline', import: 'default' });

const logos = {};
for (const [path, url] of Object.entries(files)) {
    logos[path.split('/').pop().replace('.png', '')] = url;
}

export function logoFor(abbrv) {
    return logos[abbrv];
}

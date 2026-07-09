import re
import os
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/clean', methods=['POST'])
def clean_filename():
    """Pulisce un testo e lo trasforma in un nome file valido."""
    data = request.get_json(silent=True) or {}
    text = data.get('text', '')
    rules = data.get('rules', {})

    # Step 1: normalizza gli spazi unicode in spazi regolari
    cleaned = re.sub(
        r'[\u00A0\u1680\u2000-\u200A\u2028\u2029\u202F\u205F\u3000]',
        ' ', text
    )

    # Step 2: rimuovi SEMPRE i caratteri non validi nei file system
    # Windows: \ / : * ? " < > |
    # + caratteri di controllo (0x00-0x1F, 0x7F DEL)
    cleaned = re.sub(r'[\\/:*?"<>|]', '', cleaned)
    cleaned = re.sub(r'[\x00-\x1f\x7f]', '', cleaned)

    # Step 3: opzionalmente rimuovi TUTTI i caratteri non alfanumerici
    # (tranne spazio, punto, trattino, underscore gestiti dopo)
    if rules.get('removeSpecial', False):
        cleaned = re.sub(r'[^a-zA-Z0-9\s.\-_]', '', cleaned)

    # Step 4: gestisci gli spazi
    space_handling = rules.get('spaces', 'dash')
    if space_handling == 'dash':
        cleaned = re.sub(r'\s+', '-', cleaned)
    elif space_handling == 'underscore':
        cleaned = re.sub(r'\s+', '_', cleaned)
    elif space_handling == 'remove':
        cleaned = re.sub(r'\s+', '', cleaned)
    # 'keep' mantiene gli spazi così come sono

    # Step 5: collassa separatori multipli consecutivi
    cleaned = re.sub(r'-{2,}', '-', cleaned)
    cleaned = re.sub(r'_{2,}', '_', cleaned)
    cleaned = re.sub(r'\.{2,}', '.', cleaned)

    # Step 6: rimuovi separatori e spazi da inizio e fine
    cleaned = cleaned.strip('-_.,;:! \t')

    # Step 7: converti in minuscolo se richiesto
    if rules.get('lowercase', False):
        cleaned = cleaned.lower()

    # Step 8: applica prefisso e suffisso
    prefix = rules.get('prefix', '').strip()
    suffix = rules.get('suffix', '').strip()

    # Pulisci anche prefisso e suffisso dai caratteri non validi
    if prefix:
        prefix = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', '', prefix)
    if suffix:
        suffix = re.sub(r'[\\/:*?"<>|\x00-\x1f\x7f]', '', suffix)

    if cleaned:
        cleaned = prefix + cleaned + suffix
    else:
        cleaned = prefix + 'untitled' + suffix

    # Step 9: applica limite di lunghezza massima
    max_len = rules.get('maxLength', None)
    if max_len and isinstance(max_len, (int, float)) and max_len > 0:
        max_len = int(max_len)
        if len(cleaned) > max_len:
            plen = len(prefix)
            slen = len(suffix)
            core_max = max_len - plen - slen
            if core_max <= 0:
                # Prefisso+suffisso da soli superano il limite
                cleaned = (prefix + suffix)[:max_len].rstrip('-_.,;:! \t')
            else:
                core = cleaned[plen:len(cleaned)-slen] if slen else cleaned[plen:]
                core = core[:core_max].rstrip('-_.,;:! \t')
                cleaned = prefix + core + suffix

    # Step 10: assicurati che il risultato non sia vuoto
    if not cleaned or not cleaned.strip('-_.,;:! \t'):
        cleaned = 'untitled'

    return jsonify({'filename': cleaned})


@app.route('/robots.txt')
def robots():
    return (
        'User-agent: *\n'
        'Allow: /\n'
        'Sitemap: https://cristianporco.it/app/cleanfile/sitemap.xml\n'
    ), 200, {'Content-Type': 'text/plain'}


@app.route('/sitemap.xml')
def sitemap():
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        '  <url>\n'
        '    <loc>https://cristianporco.it/app/cleanfile/</loc>\n'
        '    <lastmod>2026-07-09</lastmod>\n'
        '    <changefreq>monthly</changefreq>\n'
        '    <priority>0.8</priority>\n'
        '  </url>\n'
        '</urlset>\n'
    ), 200, {'Content-Type': 'application/xml'}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 4599)))

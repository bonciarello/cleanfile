"""Test suite per il generatore di nomi file."""

import pytest
import json
from app import app


@pytest.fixture
def client():
    """Crea un client di test Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# ── Rimozione caratteri non validi ──────────────────────

def test_removes_windows_invalid_chars(client):
    """I caratteri backslash, slash, due punti, asterisco, ecc. devono essere sempre rimossi."""
    resp = client.post('/api/clean', json={
        'text': 'te\\st/fi:le*na?me"<ok>|.txt',
        'rules': {}
    })
    assert resp.status_code == 200
    assert resp.json['filename'] == 'testfilenameok.txt'


def test_removes_control_characters(client):
    """I caratteri di controllo devono essere rimossi."""
    resp = client.post('/api/clean', json={
        'text': 'hello\x00\x1f\x7fworld',
        'rules': {}
    })
    assert resp.json['filename'] == 'helloworld'


# ── Gestione spazi ──────────────────────────────────────

def test_spaces_to_dash_default(client):
    """Default: gli spazi diventano trattini."""
    resp = client.post('/api/clean', json={
        'text': 'il mio file',
        'rules': {}
    })
    assert resp.json['filename'] == 'il-mio-file'


def test_spaces_to_underscore(client):
    """Opzione underscore: gli spazi diventano underscore."""
    resp = client.post('/api/clean', json={
        'text': 'il mio file',
        'rules': {'spaces': 'underscore'}
    })
    assert resp.json['filename'] == 'il_mio_file'


def test_spaces_remove(client):
    """Opzione remove: gli spazi vengono eliminati."""
    resp = client.post('/api/clean', json={
        'text': 'il mio file',
        'rules': {'spaces': 'remove'}
    })
    assert resp.json['filename'] == 'ilmiofile'


def test_spaces_keep(client):
    """Opzione keep: gli spazi vengono mantenuti."""
    resp = client.post('/api/clean', json={
        'text': 'il mio file',
        'rules': {'spaces': 'keep'}
    })
    assert resp.json['filename'] == 'il mio file'


def test_multiple_spaces_collapsed(client):
    """Spazi multipli vengono collassati in un singolo separatore."""
    resp = client.post('/api/clean', json={
        'text': 'tanto    spazio   qui',
        'rules': {'spaces': 'dash'}
    })
    assert resp.json['filename'] == 'tanto-spazio-qui'


# ── Rimozione caratteri speciali ────────────────────────

def test_remove_special_chars(client):
    """Con toggle ON, i caratteri non alfanumerici vengono rimossi."""
    resp = client.post('/api/clean', json={
        'text': 'file@nome#2024!finale',
        'rules': {'removeSpecial': True}
    })
    assert resp.json['filename'] == 'filenome2024finale'


def test_keep_special_chars_when_toggle_off(client):
    """Con toggle OFF, i caratteri speciali (non filesystem) restano."""
    resp = client.post('/api/clean', json={
        'text': 'file@nome#2024!finale',
        'rules': {'removeSpecial': False}
    })
    assert resp.json['filename'] == 'file@nome#2024!finale'


# ── Lowercase ───────────────────────────────────────────

def test_lowercase_conversion(client):
    """Con toggle ON, il testo viene convertito in minuscolo."""
    resp = client.post('/api/clean', json={
        'text': 'Il Mio File IMPORTANTE',
        'rules': {'spaces': 'dash', 'lowercase': True}
    })
    assert resp.json['filename'] == 'il-mio-file-importante'


def test_no_lowercase_by_default(client):
    """Default: il case originale viene mantenuto."""
    resp = client.post('/api/clean', json={
        'text': 'Il Mio File',
        'rules': {'spaces': 'dash'}
    })
    assert resp.json['filename'] == 'Il-Mio-File'


# ── Lunghezza massima ───────────────────────────────────

def test_max_length(client):
    """Se la lunghezza supera il limite, il nome viene troncato."""
    resp = client.post('/api/clean', json={
        'text': 'questo è un nome molto lungo che supera il limite',
        'rules': {'spaces': 'dash', 'maxLength': 25}
    })
    assert len(resp.json['filename']) <= 25


def test_max_length_with_prefix_suffix(client):
    """Il troncamento rispetta prefisso e suffisso."""
    resp = client.post('/api/clean', json={
        'text': 'documento-importante-2024',
        'rules': {
            'spaces': 'dash',
            'maxLength': 25,
            'prefix': 'v2-',
            'suffix': '-final'
        }
    })
    assert len(resp.json['filename']) <= 25
    assert resp.json['filename'].startswith('v2-')
    assert resp.json['filename'].endswith('-final')


# ── Prefisso e suffisso ─────────────────────────────────

def test_prefix(client):
    """Il prefisso viene anteposto al nome."""
    resp = client.post('/api/clean', json={
        'text': 'relazione',
        'rules': {'prefix': 'bozza-'}
    })
    assert resp.json['filename'] == 'bozza-relazione'


def test_suffix(client):
    """Il suffisso viene aggiunto in coda."""
    resp = client.post('/api/clean', json={
        'text': 'relazione',
        'rules': {'suffix': '-v3'}
    })
    assert resp.json['filename'] == 'relazione-v3'


def test_prefix_and_suffix_together(client):
    """Prefisso e suffisso possono coesistere."""
    resp = client.post('/api/clean', json={
        'text': 'report',
        'rules': {'prefix': '2026-', 'suffix': '-final'}
    })
    assert resp.json['filename'] == '2026-report-final'


# ── Casi limite ─────────────────────────────────────────

def test_empty_input_returns_untitled(client):
    """Un input vuoto restituisce 'untitled'."""
    resp = client.post('/api/clean', json={
        'text': '',
        'rules': {}
    })
    assert resp.json['filename'] == 'untitled'


def test_only_invalid_chars_returns_untitled(client):
    """Solo caratteri non validi → 'untitled'."""
    resp = client.post('/api/clean', json={
        'text': '?<>|*"/\\:',
        'rules': {}
    })
    assert resp.json['filename'] == 'untitled'


def test_only_whitespace_returns_untitled(client):
    """Solo spazi bianchi → 'untitled'."""
    resp = client.post('/api/clean', json={
        'text': '    \t\n   ',
        'rules': {}
    })
    assert resp.json['filename'] == 'untitled'


def test_normal_text_unchanged_without_rules(client):
    """Un testo semplice senza spazi né caratteri speciali resta invariato."""
    resp = client.post('/api/clean', json={
        'text': 'documento-2024',
        'rules': {}
    })
    assert resp.json['filename'] == 'documento-2024'


def test_leading_trailing_separators_stripped(client):
    """Separatori a inizio e fine vengono rimossi."""
    resp = client.post('/api/clean', json={
        'text': '---   mio file   ---',
        'rules': {'spaces': 'dash'}
    })
    assert resp.json['filename'] == 'mio-file'


def test_content_type_json(client):
    """L'endpoint restituisce JSON."""
    resp = client.post('/api/clean', json={'text': 'test', 'rules': {}})
    assert resp.status_code == 200
    assert resp.content_type == 'application/json'
    assert 'filename' in resp.json


def test_malformed_body(client):
    """Un body vuoto o malformato non deve rompere il server."""
    resp = client.post('/api/clean', data='not json', content_type='application/json')
    assert resp.status_code == 200
    assert resp.json['filename'] == 'untitled'


# ── Route statiche ──────────────────────────────────────

def test_index_page(client):
    """La pagina principale è servita correttamente."""
    resp = client.get('/')
    assert resp.status_code == 200
    assert b'<!DOCTYPE html>' in resp.data


def test_robots_txt(client):
    """robots.txt è servito."""
    resp = client.get('/robots.txt')
    assert resp.status_code == 200
    assert b'Sitemap:' in resp.data


def test_sitemap_xml(client):
    """sitemap.xml è servito."""
    resp = client.get('/sitemap.xml')
    assert resp.status_code == 200
    assert b'<urlset' in resp.data

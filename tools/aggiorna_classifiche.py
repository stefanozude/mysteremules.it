"""Aggiorna le classifiche UISP (Over 40 e Over 50) dentro index.html.
Uso: python3 -I tools/aggiorna_classifiche.py index.html
Scarica le pagine UISP direttamente (non serve WebFetch), legge la tabella
"Classifica" e modifica SOLO standings.o40 / standings.o50 nel JSON site-data.
Stampa un riepilogo; esce con codice 0 se ha cambiato qualcosa, 3 se invariate,
1 se una pagina non e' leggibile (in quel caso quella classifica non viene toccata)."""
import sys, re, json, html, datetime, urllib.request

PAGES = {'o40': 'https://gestionalepallacanestro.uisp.it/Bologna/82/99',
         'o50': 'https://gestionalepallacanestro.uisp.it/Bologna/83/118'}
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
        'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']

def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (mysteremules.it classifiche)'})
    return urllib.request.urlopen(req, timeout=40).read().decode('utf-8', 'replace')

def parse(page):
    i = page.find('>Classifica</th>')
    if i < 0: raise ValueError('tabella Classifica non trovata')
    body = page[i:page.find('</tbody>', i)]
    rows = []
    for tr in re.findall(r'<tr>(.*?)</tr>', body, re.S):
        cells = [re.sub(r'<[^>]+>', '', c).strip() for c in re.findall(r'<td[^>]*>(.*?)</td>', tr, re.S)]
        cells = [html.unescape(c) for c in cells if c != '']
        # formato nuovo (nov 2026): team, Pt, "G/V/P", "F/S"
        if len(cells) >= 4 and re.fullmatch(r'\d+/\d+/\d+', cells[-2]) and re.fullmatch(r'\d+/\d+', cells[-1]) and cells[-3].isdigit():
            team, pt = cells[-4], int(cells[-3])
            _, v, s = map(int, cells[-2].split('/'))
            pf, ps = map(int, cells[-1].split('/'))
        else:  # formato vecchio: team, Pt, V, S, PF, PS
            if len(cells) < 6: continue
            team, nums = cells[-6], cells[-5:]
            if not all(n.lstrip('-').isdigit() for n in nums): continue
            pt, v, s, pf, ps = map(int, nums)
        rows.append({'team': ' '.join(team.split()).upper(), 'pt': pt, 'v': v, 's': s, 'pf': pf, 'ps': ps})
    if not rows: raise ValueError('nessuna riga letta')
    return rows

def main(path):
    src = open(path, encoding='utf-8').read()
    m = re.search(r'(<script type="application/json" id="site-data">)(.*?)(</script>)', src, re.S)
    d = json.loads(m.group(2))
    st = d.setdefault('standings', {})
    oggi = datetime.date.today()
    data_it = '%d %s %d' % (oggi.day, MESI[oggi.month - 1], oggi.year)
    changed, errors, summary = [], [], []
    for key, url in PAGES.items():
        label = 'Over 40' if key == 'o40' else 'Over 50'
        try:
            rows = parse(fetch(url))
        except Exception as e:
            errors.append('%s: pagina UISP non leggibile (%s)' % (label, e)); continue
        old = (st.get(key) or {}).get('rows')
        if rows != old:
            st[key] = {'updated': data_it, 'rows': rows}; changed.append(label)
        for pos, r in enumerate(rows, 1):
            if 'MYSTERE' in r['team']:
                summary.append('%s: Mystere Mules %d° con %d punti (%d-%d)' % (label, pos, r['pt'], r['v'], r['s']))
    if changed:
        raw = json.dumps(d, ensure_ascii=False, separators=(', ', ': ')).replace('<', '\\u003c')
        open(path, 'w', encoding='utf-8').write(src[:m.start(2)] + raw + src[m.end(2):])
    print('AGGIORNATE: ' + ', '.join(changed) if changed else 'INVARIATE')
    for l in summary + errors: print(l)
    return 1 if errors and not changed else (0 if changed else 3)

if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else 'index.html'))

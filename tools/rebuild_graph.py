#!/usr/bin/env python3
"""Bygger om kunskapsgrafen i graphify-out/ med det KURERADE filurvalet.

Kör detta i stället för `graphify update .` — det bara kommandot drar in
three.module.js (Three.js internals) och data.js (4 MB genererad kartdata) och
sväller grafen från ~250 till ~2 500 noder, vilket dränker vår egen kod i brus
och slår sönder community-indelningen.

Gratis och deterministiskt: AST-lagret parsas om från källkoden, det semantiska
lagret (arkitekturbesluten ur ARKITEKTUR.md m.fl.) återanvänds ur graphify-out/cache/.
Kör om det semantiska lagret bara när DOKUMENTEN ändrats — se GRAFEN.md.

    python3 tools/rebuild_graph.py

Kräver graphify (installeras av /graphify-skillen) och körs från repo-roten.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'graphify-out'

# Kurerat urval: vår egen kod. Allt annat är vendorerat, genererat eller binärt.
CODE_FILES = [
    'public/game.js',
    'tools/build_classmap.py',
    'tools/build_data.py',
    'tools/build_data2.py',
    'tools/fetch_elev.py',
    'tools/fetch_lidar.py',
    'tools/fetch_ortho.py',
    'tools/fetch_ortho_lm.py',
    'tools/fetch_tiles.py',
    'tools/make_ortho8k.py',
    'tools/rebuild_graph.py',
]
# Medvetet UTESLUTNA (ändra bara med god anledning):
#   public/data.js, public/flats.js  — genererad kartdata, tiotusentals siffror
#   public/three.module.js           — vendorerat bibliotek (MIT), ~2 300 symboler
#   public/*.png, *.jpg, tools/*     — bilder och cache
DOC_FILES = [
    '.github/workflows/deploy.yml', 'ARKITEKTUR.md', 'CLAUDE.md', 'DEPLOY.md',
    'GRAFEN.md', 'KRAVSPEC.md', 'README.md', 'TODO.md', 'public/index.html',
    'tools/DEPLOY.md', 'tools/overpass_query.txt', 'tools/poi_query.txt',
]

# Community-namn (svenska). Nya kluster får platshållare tills någon döper dem.
LABELS = {
    0: 'Speltillstånd & runtime-globaler',
    1: 'Arkitekturbeslut & motiv',
    2: 'Rendering, kollision & soldater',
    3: 'Spelloop, HUD & zonlogik',
    4: 'Markklassning & markshader',
    5: 'Kartdatagenerering & landmärken',
    6: 'Höjd, siktlinjer & spawns',
    7: 'Äldre datapipeline (v1)',
    8: 'Texturer & geometrisammanslagning',
    9: 'Tile-hämtning (äldre)',
    10: 'Vägband & kartgränser',
    11: 'Koordinatmappning',
    12: 'Höjdhämtning (äldre)',
    13: 'Ortofotohämtning (äldre)',
}


def main():
    try:
        from graphify.extract import extract
        from graphify.cache import check_semantic_cache
        from graphify.build import build_from_json
        from graphify.cluster import cluster, score_all
        from graphify.analyze import god_nodes, surprising_connections, suggest_questions
        from graphify.report import generate
        from graphify.export import to_json
    except ImportError:
        sys.exit('graphify saknas. Installera med: uv tool install graphifyy')

    code_paths = [ROOT / f for f in CODE_FILES if (ROOT / f).exists()]
    ast = extract(code_paths, cache_root=ROOT)
    print(f'AST: {len(ast["nodes"])} noder, {len(ast["edges"])} kanter (gratis)')

    # semantiskt lager ur cachen — kostar inga tokens så länge filerna är oförändrade
    all_files = [str(ROOT / f) for f in CODE_FILES + DOC_FILES if (ROOT / f).exists()]
    sem_nodes, sem_edges, sem_hyper, uncached = check_semantic_cache(all_files)
    print(f'Semantiskt (cache): {len(sem_nodes)} noder, {len(sem_edges)} kanter')
    if uncached:
        print(f'  OBS: {len(uncached)} fil(er) saknar semantisk extraktion:')
        for u in uncached[:10]:
            print('   -', Path(u).relative_to(ROOT))
        print('  Kör /graphify . --update i Claude Code för att fylla på (kostar tokens).')

    seen = {n['id'] for n in ast['nodes']}
    merged_nodes = ast['nodes'] + [n for n in sem_nodes if n['id'] not in seen]
    extraction = {
        'nodes': merged_nodes,
        'edges': ast['edges'] + sem_edges,
        'hyperedges': sem_hyper,
        'input_tokens': 0,
        'output_tokens': 0,
    }

    G = build_from_json(extraction)
    communities = cluster(G)
    cohesion = score_all(G, communities)
    labels = {cid: LABELS.get(cid, f'Community {cid}') for cid in communities}
    gods = god_nodes(G)
    surprises = surprising_connections(G, communities)
    questions = suggest_questions(G, communities, labels)

    total_words = 0
    for f in all_files:
        try:
            total_words += len(Path(f).read_text(encoding='utf-8', errors='ignore').split())
        except OSError:
            pass
    detection = {'total_files': len(all_files), 'total_words': total_words,
                 'files': {'code': [str(p) for p in code_paths]}}
    report = generate(G, communities, cohesion, labels, gods, surprises, detection,
                      {'input': 0, 'output': 0}, str(ROOT), suggested_questions=questions)
    (OUT / 'GRAPH_REPORT.md').write_text(report, encoding='utf-8')
    to_json(G, communities, str(OUT / ('gr' + 'aph.json')))
    (OUT / '.graphify_labels.json').write_text(
        json.dumps({str(k): v for k, v in labels.items()}, ensure_ascii=False), encoding='utf-8')

    print(f'\nGraf: {G.number_of_nodes()} noder, {G.number_of_edges()} kanter, '
          f'{len(communities)} communities')
    if G.number_of_nodes() > 600:
        print('VARNING: ovanligt många noder — kom vendorerad/genererad kod in i urvalet?')
    print('Kör `graphify export html` för att uppdatera graph.html.')


if __name__ == '__main__':
    main()

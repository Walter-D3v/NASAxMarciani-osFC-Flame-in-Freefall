"""Package cleaned data + model outputs as {rows, meta} JSON for the dashboard. Usage: python export.py <psi_dir>"""
import sys, json, os
import pandas as pd, numpy as np

P = sys.argv[1]
code = lambda f: open(os.path.join(P, 'scripts', f)).read()
clean_meta = [{'label': 'clean.py', 'value': code('clean.py'), 'type': 'code', 'lang': 'python'},
              {'label': 'Input', 'value': 'NASA PSI experimental tables (PSI-69 FLEX, PSI-159 CFI-G), downloaded 2026-11-14'}]
model_meta = clean_meta[:1] + [{'label': 'models.py', 'value': code('models.py'), 'type': 'code', 'lang': 'python'},
              {'label': 'Input', 'value': 'clean/flex_droplets.csv, clean/cfig_gas_flames.csv'}]

def rows(df):
    df = df.replace({np.nan: None})
    return json.loads(df.to_json(orient='records', date_format='iso'))

def dump(name, df, meta):
    json.dump({'rows': rows(df), 'meta': meta}, open(os.path.join(P, 'dash', name + '.json'), 'w'))

os.makedirs(os.path.join(P, 'dash'), exist_ok=True)
f = pd.read_csv(os.path.join(P, 'clean/flex_droplets.csv'))
f['diluent'] = np.select([f.x_he > 0, f.x_co2 > 0], ['He', 'CO2'], 'N2')
dump('flex', f, clean_meta)
dump('cfig', pd.read_csv(os.path.join(P, 'out/cfig_with_pred.csv')), model_meta)
dump('pred_dext', pd.read_csv(os.path.join(P, 'out/pred_dext.csv')), model_meta)
dump('d2law', pd.read_csv(os.path.join(P, 'out/d2law_check.csv')), model_meta)

s = json.load(open(os.path.join(P, 'out/model_summary.json')))
m = [
    {'key': 'dext_r2', 'model': 'Extinction diameter', 'metric': 'R²', 'value': s['dext']['r2'], 'baseline': 0.0, 'n': s['dext']['n']},
    {'key': 'dext_mae', 'model': 'Extinction diameter', 'metric': 'MAE (mm)', 'value': s['dext']['mae'], 'baseline': s['dext']['mae_baseline'], 'n': s['dext']['n']},
    {'key': 'k_r2', 'model': 'Burning-rate constant K', 'metric': 'R²', 'value': s['K']['r2'], 'baseline': 0.0, 'n': s['K']['n']},
    {'key': 'k_mae', 'model': 'Burning-rate constant K', 'metric': 'MAE (mm²/s)', 'value': s['K']['mae'], 'baseline': s['K']['mae_baseline'], 'n': s['K']['n']},
    {'key': 'out_acc', 'model': 'FLEX outcome (3 classes)', 'metric': 'Accuracy', 'value': s['outcome']['accuracy'], 'baseline': s['outcome']['majority_baseline'], 'n': s['outcome']['n']},
    {'key': 'hot_auc', 'model': 'CFI-G hot ignition', 'metric': 'ROC AUC', 'value': s['hot']['auc'], 'baseline': 0.5, 'n': s['hot']['n']},
    {'key': 'hot_acc', 'model': 'CFI-G hot ignition', 'metric': 'Accuracy', 'value': s['hot']['accuracy'], 'baseline': s['hot']['majority_baseline'], 'n': s['hot']['n']},
    {'key': 'd2_ratio', 'model': 'd²-law check (extinction runs)', 'metric': 'Median K·t / (d0²−dext²)', 'value': s['d2law']['median_ratio'], 'baseline': 1.0, 'n': s['d2law']['n']},
]
for r in m:
    for k in ('value', 'baseline'): r[k] = round(r[k], 3)
dump('metrics', pd.DataFrame(m), model_meta)
imp = [{'model': k, 'feature': i['feature'], 'importance': round(i['importance'], 4)} for k in ('dext', 'K', 'outcome', 'hot') for i in s[k]['importance']]
dump('importance', pd.DataFrame(imp), model_meta)
dump('confusion', pd.DataFrame(s['outcome']['confusion']), model_meta)
for n in os.listdir(os.path.join(P, 'dash')): print(n, os.path.getsize(os.path.join(P, 'dash', n)))

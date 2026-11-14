"""Baseline models on cleaned PSI tables. Usage: python models.py <clean_dir> <out_dir>"""
import sys, json
import numpy as np, pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor, HistGradientBoostingClassifier
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.inspection import permutation_importance
from sklearn.metrics import mean_absolute_error, r2_score, accuracy_score, confusion_matrix, roc_auc_score

C, O = sys.argv[1], sys.argv[2]
rng = 0
f = pd.read_csv(f'{C}/flex_droplets.csv', parse_dates=['date'])
g = pd.read_csv(f'{C}/cfig_gas_flames.csv')

# ---------- FLEX features ----------
f['fuel_heptane'] = (f.fuel == 'heptane').astype(int)
f['diluent'] = np.select([f.x_he > 0, f.x_co2 > 0], ['He', 'CO2'], 'N2')
# groups = test day (or test-id prefix when date missing) -> no same-day leakage
f['group'] = f.date.dt.strftime('%Y-%m-%d').fillna(f.test_id.str[:3])
FX = ['fuel_heptane', 'pressure_atm', 'x_o2', 'x_co2', 'x_he', 'd0_mm']
names = {'fuel_heptane': 'Fuel (heptane vs methanol)', 'pressure_atm': 'Pressure', 'x_o2': 'O2 fraction',
         'x_co2': 'CO2 fraction', 'x_he': 'He fraction', 'd0_mm': 'Initial diameter'}
gkf = GroupKFold(n_splits=5)
out = {}

def importance(model, X, y, scoring):
    model.fit(X, y)
    pi = permutation_importance(model, X, y, n_repeats=20, random_state=rng, scoring=scoring)
    return sorted([{'feature': names.get(c, c), 'importance': round(float(m), 4)} for c, m in zip(X.columns, pi.importances_mean)],
                  key=lambda d: -d['importance'])

# 1) extinction diameter (only runs with a measured extinction diameter)
d = f.dropna(subset=FX + ['d_ext_mm']).copy()
m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=3, random_state=rng)
d['pred_d_ext_mm'] = cross_val_predict(m, d[FX], d.d_ext_mm, groups=d.group, cv=gkf)
base = np.full(len(d), d.d_ext_mm.mean())
out['dext'] = {'n': len(d), 'mae': mean_absolute_error(d.d_ext_mm, d.pred_d_ext_mm), 'r2': r2_score(d.d_ext_mm, d.pred_d_ext_mm),
               'mae_baseline': mean_absolute_error(d.d_ext_mm, base),
               'importance': importance(m, d[FX], d.d_ext_mm, 'neg_mean_absolute_error')}
d[['test_id', 'fuel', 'diluent', 'x_o2', 'pressure_atm', 'd0_mm', 'd_ext_mm', 'pred_d_ext_mm']].round(3).to_csv(f'{O}/pred_dext.csv', index=False)

# 2) burning rate K
d2 = f.dropna(subset=FX + ['burning_rate_K_mm2_s']).copy()
m = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, max_depth=3, random_state=rng)
d2['pred_K'] = cross_val_predict(m, d2[FX], d2.burning_rate_K_mm2_s, groups=d2.group, cv=gkf)
out['K'] = {'n': len(d2), 'mae': mean_absolute_error(d2.burning_rate_K_mm2_s, d2.pred_K), 'r2': r2_score(d2.burning_rate_K_mm2_s, d2.pred_K),
            'mae_baseline': mean_absolute_error(d2.burning_rate_K_mm2_s, np.full(len(d2), d2.burning_rate_K_mm2_s.mean())),
            'importance': importance(m, d2[FX], d2.burning_rate_K_mm2_s, 'neg_mean_absolute_error')}

# 3) outcome classifier
d3 = f.dropna(subset=FX + ['outcome']).copy()
m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3, random_state=rng, class_weight='balanced')
d3['pred_outcome'] = cross_val_predict(m, d3[FX], d3.outcome, groups=d3.group, cv=gkf)
labels = ['extinction', 'disruption', 'completion']
cm = confusion_matrix(d3.outcome, d3.pred_outcome, labels=labels)
out['outcome'] = {'n': len(d3), 'accuracy': accuracy_score(d3.outcome, d3.pred_outcome),
                  'majority_baseline': float((d3.outcome == d3.outcome.mode()[0]).mean()),
                  'confusion': [{'actual': a, 'predicted': p, 'count': int(cm[i, j])} for i, a in enumerate(labels) for j, p in enumerate(labels)],
                  'importance': importance(m, d3[FX], d3.outcome, 'accuracy')}

# 4) d^2-law consistency for extinction runs: K * t vs d0^2 - dext^2
e = f[(f.outcome == 'extinction')].dropna(subset=['d0_mm', 'd_ext_mm', 'burning_rate_K_mm2_s', 'burn_time_s']).copy()
e['lhs_mm2'] = e.burning_rate_K_mm2_s * e.burn_time_s
e['rhs_mm2'] = e.d0_mm ** 2 - e.d_ext_mm ** 2
e['ratio'] = e.lhs_mm2 / e.rhs_mm2
q1, q3 = e.ratio.quantile([.25, .75]); iqr = q3 - q1
e['anomaly'] = (e.ratio < q1 - 1.5 * iqr) | (e.ratio > q3 + 1.5 * iqr)
out['d2law'] = {'n': len(e), 'median_ratio': float(e.ratio.median()), 'n_anomalies': int(e.anomaly.sum())}
e[['test_id', 'fuel', 'diluent', 'x_o2', 'pressure_atm', 'd0_mm', 'd_ext_mm', 'burning_rate_K_mm2_s', 'burn_time_s', 'lhs_mm2', 'rhs_mm2', 'ratio', 'anomaly']] \
    .round(3).to_csv(f'{O}/d2law_check.csv', index=False)

# ---------- CFI-G hot ignition ----------
g['fuel_base'] = g.fuel.str.extract(r'(ethane|propane|butane)')[0]
g['fuel_dilution'] = g.fuel.str.extract(r'(\d+)%')[0].astype(float).fillna(100) / 100
gg = g.dropna(subset=['pressure_bar', 'tad_K', 'zst', 'hot_ignition']).copy()
GX = pd.get_dummies(gg[['flame_type', 'fuel_base']]).astype(int).join(gg[['pressure_bar', 'tad_K', 'zst', 'fuel_dilution']])
names.update({'pressure_bar': 'Pressure', 'tad_K': 'Adiabatic flame T', 'zst': 'Stoich. mixture fraction Zst',
              'fuel_dilution': 'Fuel dilution', 'flame_type_inverse': 'Inverse flame', 'flame_type_normal': 'Normal flame',
              'fuel_base_butane': 'Butane', 'fuel_base_ethane': 'Ethane', 'fuel_base_propane': 'Propane'})
grp = gg.test_id.str[:5]  # test day
m = HistGradientBoostingClassifier(max_iter=200, learning_rate=0.05, max_depth=3, random_state=rng)
proba = cross_val_predict(m, GX, gg.hot_ignition, groups=grp, cv=gkf, method='predict_proba')[:, 1]
gg['p_hot'] = proba
out['hot'] = {'n': len(gg), 'auc': roc_auc_score(gg.hot_ignition, proba), 'accuracy': accuracy_score(gg.hot_ignition, proba > .5),
              'majority_baseline': float(max(gg.hot_ignition.mean(), 1 - gg.hot_ignition.mean())),
              'importance': importance(m, GX, gg.hot_ignition, 'roc_auc')}
gg[['flame_type', 'test_id', 'fuel', 'fuel_base', 'pressure_bar', 'tad_K', 'zst', 'hot_ignition', 'p_hot', 'burn_time_s', 'end']].round(3) \
    .to_csv(f'{O}/cfig_with_pred.csv', index=False)

json.dump(out, open(f'{O}/model_summary.json', 'w'), indent=1, default=float)
for k, v in out.items():
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items() if a not in ('importance', 'confusion')})
    if 'importance' in v: print('   ', [(i['feature'], i['importance']) for i in v['importance'][:4]])

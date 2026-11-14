import pandas as pd, numpy as np, sys
R, C = sys.argv[1], sys.argv[2]
num = lambda s: pd.to_numeric(s.astype(str).str.strip().replace({'�': np.nan, '-': np.nan, '': np.nan}), errors='coerce')

# FLEX (PSI-69): one row per droplet test, with outcomes
f = pd.read_csv(f'{R}/PSI-69_Experimental table_FLEX.csv').dropna(how='all')
flex = pd.DataFrame({
    'test_id': f['FLEX Identifier'].str.strip(), 'date': pd.to_datetime(f['Test Date'], errors='coerce'),
    'fuel': f['Fuel'].str.strip().str.lower(),
    'pressure_atm': num(f['Ambient pressure; mmHg']) / 760,
    'x_o2': num(f['O initial ambient composition; mole fraction']), 'x_n2': num(f['N initial ambient composition; mole fraction']),
    'x_co2': num(f['CO initial ambient composition; mole fraction']), 'x_he': num(f['He initial ambient composition; mole fraction']),
    'd0_mm': num(f['Droplet initial diameter; mm']), 'd_ext_mm': num(f['Visible flame extinction diameter; mm']),
    'burning_rate_K_mm2_s': num(f['Burning rate; mm']), 'burn_time_s': num(f['Burn time; s']),
    'outcome': f['Test end'].str.strip().str.lower()})
flex.loc[flex.pressure_atm <= 0, 'pressure_atm'] = np.nan  # 0 mmHg is a logging error
flex['dext_over_d0'] = flex.d_ext_mm / flex.d0_mm
flex.to_csv(f'{C}/flex_droplets.csv', index=False)

# CFI-G (PSI-159): normal + inverse gaseous flames, unified
def cfig(fn, kind):
    g = pd.read_csv(f'{R}/{fn}').dropna(how='all'); g.columns = g.columns.str.strip().str.replace(r'\s+', ' ', regex=True)
    se = [c for c in g.columns if c.lower().startswith('self')][0]
    return pd.DataFrame({'flame_type': kind, 'test_id': g['Test'].astype(str).str.replace(' ', ''), 'fuel': g['Fuel'].str.strip().str.lower(),
        'pressure_bar': num(g['approx p (bar)']), 'tad_K': num(g['Tad (K)']), 'zst': num(g['Zst']),
        'hot_ignition': g['Hot ignition'].astype(str).str.strip().str.lower().map({'yes': 1, 'no': 0, 'flash': 0}),
        'cool_flame': g['Cool flame?'].astype(str).str.lower().str.startswith('yes').astype(int) if 'Cool flame?' in g else 0,
        'burn_time_s': num(g['burn time (sec)']), 'end': g[se].str.strip().replace({'SE': 'self_extinction', 'FT': 'flow_terminated', '-': 'no_flame'}),
        'thin_filament_pyrometry': g['TFP'].str.strip().str.lower().eq('yes').astype(int), 'comments': g.get('Comments')})
cfg = pd.concat([cfig('PSI-159_Experimental table_CFI-G_Normal Flames.csv', 'normal'),
                 cfig('PSI-159_Experimental table_CFI-G_Inverse Flames.csv', 'inverse')], ignore_index=True)
cfg.to_csv(f'{C}/cfig_gas_flames.csv', index=False)
print(flex.describe().T.round(3)); print(flex.isna().sum()[lambda s: s > 0]); print(cfg.groupby(['flame_type','end']).size())

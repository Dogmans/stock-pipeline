import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from universe import get_country_universe

if __name__ == '__main__':
    print('Calling get_country_universe(japan) ...')
    df = get_country_universe('japan', force_refresh=True)
    print('Returned rows:', len(df))
    print(df.head().to_string())

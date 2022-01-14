# Statistical Analysis of Computer Activity for Identifying Insider Threats

## Setup
### Data
Obtain the data yourself, or run the included script:
```bash
chmod +x ./download_raw_data.sh
./download_raw_data.sh
```

Then move or symlink the csv files to the root of this repo.

### Create python environment
```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
```

## Usage
```bash
python weeklydata.py
```

```bash
python dim_reduction.py
```

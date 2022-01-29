# Statistical Analysis of Computer Activity for Identifying Insider Threats
Anomaly detection methods using the [CMU SEI Insider Threat dataset](https://resources.sei.cmu.edu/library/asset-view.cfm?assetid=508099)

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

# League Results Export

This Python script compiles orienteering race results from **IOF XML V3** files and generates a unified league-style summary table in CSV format.


## Dependencies
- [pandas](https://github.com/pandas-dev/pandas)

## Set up

1. place the **IOF XML V3** files you want to analyze into the ./result_files directory
2. install requirements (ideally in virtual environment)
```bash
pip install pandas
```
3. run the script in the root directory
```bash
python ./results_creator.py
```
4. Open the final csv file in Excel or similar spreadsheet software

## TODOs
- check if the file uses correct format
- remove the competition name row and keep only the competition's order
- maybe use the v2 format instead?
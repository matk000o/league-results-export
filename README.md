# Results Creator

Simple python script that reads the competition result data from multiple files in the IOF XML V3 version, then compiles the data into one csv file divided into separate tables for each category, showing the overall position of competitors in the league.

## Dependencies
- [pandas](https://github.com/pandas-dev/pandas)

## Set up

1. move all the **IOF XML V3** files you want to analyze into the ./result_files directory
2. install necessary modules (ideally in virtual environment)
3. run the script in the root directory (```python ./results_creator.py```)
4. output csv file should be located in the root dir

## TODOs
- check if the file uses correct format
- remove the competition name row and keep only the competition's order
- maybe use the v2 format instead?
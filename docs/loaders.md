# Introduction

Load files with similar structure into a database or HDF5 file.

## Requirements

- All files should be in a single directory.
- The directory should not have any sub directories
- All files must be of similar structure; by similar structure, they must have the same columns and datatypes. This is usually the case if you download files from the internet.

See the corresponding **Loaders** notebook in the examples folder for complete set of options

## Quickstart

Load all files in data directory into a in-memory sqlite database

```python
from sqlalchemy import create_engine
from fasbt.loaders import DataLoader
engine = create_engine('sqlite://')
directory = 'data'
# Initialize loader
dl = DataLoader(directory, mode='SQL', engine=engine, tablename='table')
dl.load_data()
```

- Create an sqlalchemy connection
- Initialize the data loader class with the directory name, engine, tablename and mode
- Use the `load_data` function to load all files into the database

If you have added new files to your directory, just run the above code again, the database would be updated with information from the new files.

If you prefer HDF5, then

```python
engine = 'data.h5'
directory = 'data'
tablename = 'table'
# Initialize loader
dl = DataLoader(directory=directory, mode='HDF', engine=engine, tablename=tablename)
dl.load_data()
```

Just change the engine argument to the HDF5 filename and mode as HDF

If you just want to load data only without loading it into a database then use the 'collate_data` function

```python
from fastbt.loaders import collate_data
directory = 'data'
df = collate_data(directory=directory)
```

Now all your data is loaded into a dataframe

See the **Loaders** notebook in the examples folder for more options and usage

## How it works

### How files are identified

DataLoader iterates over each of the file in the directory and checks if the file is already loaded in the database. If the file is already loaded, then it's skipped, but if the file is new, then its added and marked as loaded. So irrespective of how many times you run the code, your files are loaded only once. Even if you move your directory, files are not reloaded. **Files are identified by their filenames.**

Internally, in case of SQL, a new table with the prefix **\_updated\_** is created that maintains a list of all the filenames loaded so far. So if your tablename is table, then you would have an another table \_updated*table* that stores the filename data. During iteration, if the file is already in the updated_data table, then it is skipped. If it is not in the table, it is added to the database and the filename is then added to the updated_table.

In case of HDF5, the data is stored in the path **data** and the filename data in the **updated** path. In the example above, your data would be stored in _data/table_ while filenames would be stored in _updated/table_.

So to read your data back, you need to **prefix data to your tablename**.

```python
import pandas as pd
pd.read_hdf('data.h5', key='data/table')
```

### How data is converted

DataLoader uses pandas for both SQL and HDF. They are just calls to the `to_sql` and `to_hdf`. And the `load_data` function is a wrapper to the pandas `read_csv` function. So you can pass any arguments to the read_csv function to the load_data function as keyword arguments. So to skip the first 10 rows and to load only columns 2,3,4 and to parse_dates for the date column

```python
dl.load_data(usecols=[1,2,3], skiprows=10, parse_dates=['date'])
```

You can rename columns before loading into the database. This is particularly useful if your columns have spaces and other special characters.

```python
dl.load_data(rename={'Daily Volume': 'volume'})
```

See the **Loaders** notebook for more examples.

## preprocessing using postfunc

Before loading data into the database, you would need to transform the data or perform some preprocessing. You could use the postfunc argument to perform preprocessing. It works in the following way

- The file is read using the `read_csv` function and converted into a dataframe
- The preprocessing function is then run on this dataframe
- The result is stored in the database

A preprocessing function should have three mandatory arguments

1.  first argument is the dataframe after reading the file
2.  second argument is the filename of the file being read
3.  third argument is the directory

These three arguments are automatically provided when you use the `load_data` function; you need to write the preprocessing code inside the function

```python
def postfunc(df, filename, root):
    df['filename'] = filename
    return df

dl.load_data(postfunc=postfunc)
```

## other formats

Though only csv format is supported, you could load any file that looks like a csv file including dat and tab delimited text files. Use the appropriate arguments to treat them as csv files (all arguments to pandas `read_csv` function is supported)

If you just need a convenient way to load data into memory by iterating through the files use the `collate_data` function. Use the function argument to do whatever you need to do with the file, but the function should return a dataframe to collate the data.

## Caveats

- DataLoader depends on filenames to check for new files. So renaming files would load the data again.
- arguments provided to the `load_data` live throughout its lifetime. So if you need to change them, delete your database and create it again
- All field/column names are converted to lower case to make them case insensitive.
- Columns with names date,time,datetime,timestamp are automatically converted into dates
- To rename columns before loading, use the columns argument.

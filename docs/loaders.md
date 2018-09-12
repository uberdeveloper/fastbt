# Introduction

Load files with similar structure into a database or HDF5 file.

## Requirements

- All files should be in a single directory.
- The directory should not have any sub directories
- All files must be of similar structure; by similar structure, they must have the same columns and datatypes. This is usually the case if you download files from the internet

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

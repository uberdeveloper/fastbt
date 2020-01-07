"""
This is an experimental module.
Everything in this module is untested and probably incorrect.
Don't use them.

This is intended to be a place to develop new functions instead of
having an entirely new branch
"""
import pandas as pd 
import numpy as np
from numba import jit, njit
from intake.source.base import DataSource, Schema
import os

@jit
def v_cusum(array):
    """
    Calcuate cusum - numba version
    array
        numpy array
    returns
        pos and neg arrays
    """ 
    L = len(array)
    pos = [0]
    neg = [0]
    pos_val = 0
    neg_val = 0
    d = np.diff(array)[1:]
    for i in d:
        if i >= 0:
            pos_val += i
        else:
            neg_val += i
        pos.append(pos_val)
        neg.append(neg_val)
    return (pos, neg)

@jit
def sign_change(array):
    """
    Calcuate the sign change in an array
    If the current value is positive and previous value negative, mark as 1.
    If the current value is negative and previous value positive, mark as -1.
    In case of no change in sign, mark as 0
    """
    L = len(array)
    arr = np.empty(L)
    arr[0] = 0
    for i in range(1, L):
        # TO DO: Condition not handling edge case
        if (array[i] >= 0) & (array[i-1] < 0):
            arr[i] = 1
        elif (array[i] <= 0) & (array[i-1] > 0):
            arr[i] = -1
        else:
            arr[i] = 0
    return arr


def cusum(array):
    """
    Calcuate cusum
    array
        a pandas series with a timestamp or datetime index
    The cusum is just an aggregate of positive and negative differences
    returns
        pandas dataframe with positive and negative cumulatives,
        ratio, differences, regime change along with the original index
    """
    pos = [0]
    neg = [0]
    pos_val = 0
    neg_val = 0
    d = array.diff()[1:]
    for i in d:
        if i >= 0:
            pos_val += i
        else:
            neg_val += i
        pos.append(pos_val)
        neg.append(neg_val)
    df = pd.DataFrame({'pos': pos, 'neg': neg}, index=array.index)
    df['neg'] = df['neg'].abs()
    df['d'] = df['pos'] - df['neg']
    df['reg'] = sign_change(df.d.values)
    df['ratio'] = df['pos'] / df['neg']
    return df

def percentage_bar(data, step):
    """
    Generate the number of timesteps taken for each
    equivalent step in price
    data
        numpy 1d array
    step
        step size
    """
    start = data[0]
    nextStep = start + step
    counter = 0
    steps = [start]
    period = [0]
    for d in data:
        if step >= 0:
            if d > nextStep:
                steps.append(nextStep)
                period.append(counter)
                nextStep += step
                counter = 0
            else:
                counter+=1
        elif step < 0:
            if d < nextStep:
                steps.append(nextStep)
                period.append(counter)
                nextStep += step
                counter = 0
            else:
                counter+=1

    # Final loop exit           
    steps.append(nextStep)
    period.append(counter)
    return (steps, period)      

def high_breach(s):
    """
    Given a series of values, returns a series
    with consecutive highs as values and timestamp as index
    s
        series with timestamp as index
    """
    highs = []
    ts = []
    max_val = 0
    index = s.index.values
    for i,v in enumerate(s.values):
        if v > max_val:
            highs.append(v)
            ts.append(index[i])
            max_val = v
    return pd.Series(highs, index=ts)


def low_breach(s):
    """
    Given a series of values, returns a series
    with consecutive lows as values and timestamp as index
    s
        series with timestamp as index
    """
    lows = []
    ts = []
    min_val = 1e+9 # Just setting an extreme value
    index = s.index.values
    for i,v in enumerate(s.values):
        if v < min_val:
            lows.append(v)
            ts.append(index[i])
            min_val = v
    return pd.Series(lows, index=ts)



class ExcelSource(DataSource):

    container = 'dataframe'
    name = 'excel_loader'
    version = '0.0.1'
    partition_access = True

    def __init__(self, datapath, metadata=None):
        """
        Initialize with datapath and metadata
        datapath
            filename with entire path
        """
        self.filename = datapath
        self._source = pd.ExcelFile(self.filename)
        super(ExcelSource, self).__init__(metadata=metadata)

    def _get_schema(self):
        sheets = self._source.sheet_names
        return Schema(
            datashape=None,
            dtype=None,
            shape=None,
            npartitions= len(sheets),
            extra_metadata = {'sheets': sheets}
            )

    def read_partition(self, sheet, **kwargs):
        """
        Read a specific sheet from the list of sheets
        sheet
            sheet to read
        kwargs
            kwargs to the excel parse function
        """
        self._load_metadata()
        if sheet in self.metadata.get('sheets', []):
            return self._source.parse(sheet, **kwargs)
        else:
            return 'No such sheet in the Excel File'

    def read(self, **kwargs):
        """
        Read all sheets into a single dataframe.
        Sheetname is added as a column
        kwargs
            kwargs to the excel parse function
        """
        self._load_metadata()
        sheets = self.metadata.get('sheets')
        collect = []
        if len(sheets) > 1:
            for sheet in sheets:
                temp = self.read_partition(sheet, **kwargs)
                temp['sheetname'] = sheet
                collect.append(temp)
        return pd.concat(collect, sort=False)

    def _close(self):
        self._source.close()


class HDFSource(DataSource):
    """
    A simple intake container to load data from
    HDF5 fixed formats
    """

    container = 'dataframe'
    name = 'HDF5_fixed_loader'
    version = '0.0.1'
    partition_access = True

    def __init__(self, datapath, metadata=None, extension='h5'):
        """
        Initialize with datapath and metadata
        datapath
            filename or directory
            If the filename ends in any of the extensions given in the
            extension argument, then it is treated as a HDF5 file
        """
        self.source = datapath
        self._ext = extension
        # Check whether the given path is a directory or file
        if os.path.exists(datapath):
            if os.path.isfile(datapath):
                self._source_type = 'file'
            else:
                self._source_type = 'directory'
        else:
            print('Not a valid file or directory')
            return
        self._get_schema()
        super(HDFSource, self).__init__(metadata=metadata)

    def _get_schema(self):
        metadata = {
            'ext': self._ext,
            'src': self.source,
            'type': self._source_type
        }
        file_dict = {}
        if self._source_type == 'directory':
            for root,directory,files in os.walk(self.source):
                for file in files:
                    filename = os.path.join(root, file)
                    if filename.endswith(self._ext):
                        file_dict[file] = filename
            metadata.update({'files': file_dict})

        return Schema(
            datashape=None,
            dtype=None,
            shape=None,
            npartitions=len(file_dict),
            extra_metadata = metadata
            )

    def read_partition(self, file, **kwargs):
        """
        Read a specific sheet from the list of sheets
        file
            filename without extension
        kwargs
            kwargs to the excel parse function
        """
        self._load_metadata()
        ext = self.metadata.get('ext', self._ext)
        srctype = self.metadata.get('type')
        if srctype == 'file':
            return pd.read_hdf(self.metadata.get('src'))
        filename = '{file}.{ext}'.format(file=file, ext=ext)
        if filename in self.metadata.get('files', []):
            filepath = self.metadata['files'][filename]
            return pd.read_hdf(filepath)
        else:
            return 'No such HDF file'

    def read(self, **kwargs):
        """
        Read all sheets into a single dataframe.
        Sheetname is added as a column
        kwargs
            kwargs to the excel parse function
        """
        self._load_metadata()
        if self.metadata.get('type') == 'file':
            return pd.read_hdf(self.metadata.get('src'))
        else:
            return 'The datasource is a directory.Use the read_partition method to read a specific file.'


    def _close(self):
        print('Not implemented')


def twin_plot(data, y_axis, x_axis='timestamp'):
    """
    Create a bokeh plot with twin axes
    """
    from bokeh.plotting import figure
    from bokeh.models import LinearAxis, Range1d

    TOOLTIPS = [
    ('datetime', '@x{%F %H:%M}'),
    ('value', '$y{0.00}')
    ]

    y1,y2 = y_axis[0], y_axis[1]
    h0 = data[y1].max()
    l0 = data[y1].min()
    h1 = data[y2].max()
    l1 = data[y2].min()
    p = figure(x_axis_type='datetime', y_range=(l0, h0),
        tooltips=TOOLTIPS, height=240, width=600)
    p.line(data[x_axis].values, data[y1].values, 
        color="red", legend=y1)
    p.extra_y_ranges = {"foo": Range1d(l1,h1)}
    p.line(data[x_axis], data[y2].values, color="blue", 
        y_range_name="foo", legend=y2)
    p.add_layout(LinearAxis(y_range_name="foo", axis_label=y2), 'left')
    p.hover.formatters= {'x': 'datetime'}
    p.legend.location = 'top_center'
    p.legend.click_policy = 'hide'
    return p


class OptionPayoff:
    """
    A simple class for calculating option payoffs
    given spot prices and options
    1) Add your options with the add method
    2) Provide a spot price
    3) Call calculate to get the payoff for this spot price
    Note
    -----
    This class only does a simple arithmetic for the option and
    doesn't include any calculations for volatility or duration.
    It's assumed that the option is exercised at expiry and it
    doesn't have any time value
    """
    def __init__(self):
        self._spot = 0
        self._options = []

    def _payoff(self, strike, option, position, **kwargs):
        """
        calculate the payoff for the option
        """
        comb = (option, position)
        spot = self._spot
        if comb == ('C', 'B'):
            return max(spot-strike, 0)
        elif comb == ('P', 'B'):
            return max(strike-spot, 0)
        elif comb == ('C', 'S'):
            return min(0, strike-spot)
        elif comb == ('P', 'S'):
            return min(0, spot-strike)

    def add(self, strike, opt_type='C', position='B', premium=0, qty=1):
        """
        Add an option
        strike
            strike price of the options
        opt_type
            option type - C for call and P for put
        position
            whether you are Buying or Selling the option
            B for buy and S for sell
        premium
            option premium
        qty
            quantity of options contract
        """
        if position == 'B':
            premium = 0-abs(premium)
        elif position == 'S':
            qty = 0-abs(qty)
        self._options.append({
            'strike': strike,
            'option': opt_type,
            'position': position,
            'premium': premium,
            'qty': qty
            })

    @property
    def options(self):
        """
        return the list of options
        """
        return self._options

    def clear(self):
        """
        Clear all options
        """
        self._options = []

    def spot(self, price):
        """
        Set the spot price
        """
        self._spot = price

    def calc(self):
        """
        Calculate the payoff
        """
        if self._spot <= 0:
            print('Spot price incorrect.\nSet the price with the spot method')
            return
        else:
            payoffs = []
            for p in self.options:
                profit = (self._payoff(**p) * abs(p['qty'])) + (p['premium'])
                payoffs.append(profit)
            return payoffs

def conditional(data, c1, c2, out=None):
    """
    Create a conditional probability table with counts
    data
        dataframe
    c1
        condition as string
    c2
        list of conditions as strings
    out
        output format. If None, counts are returned.
        If a function is passed, it is applied to 
        each of the conditions and the return value
        of the function is stored for each condition.
        The function should have a single argument that
        takes a dataframe as an input.

    returns a dictionary with the conditions and
    the counts or the return value of each of the conditions
    Note
    ----
    1. The dataframe is queried with c1 and each of the conditions
    in c2 are evaluated based on this result.
    2. All conditions are evaluated using `df.query`
    3. The condition strings should be valid columns in the dataframe
    4. The function passed should have a single argument, the dataframe.
    """
    dct = {}
    if out is None:
        out = len
    df = data.query(c1)
    dct[c1] = out(df)
    for c in c2:
        dct[c] = out(df.query(c))
    return dct


class Catalog:
    """
    A intake catalog creator
    The catalog is created in the following manner
        1. All files in the root directory are considered to
        be separate files and loaded as such.
        2. All directories and subdirectories inside the root 
        directory are considered to be separate data sources
        3. Each of the files are matched against the extension
        name and the corresponding mapper
        4. Files inside a directory are randomly selected and the
        file type is determined for the entire directory.
        **It's assumed that all files inside any sub-directories
        are of the same file type**
    """
    def __init__(self, directory):
        """
        directory
            directory to search for files
        """
        self._directory = directory
        """
        All files in the below directories are added
        individually as a data source
        """
        self._file_dirs = ['files']
        """
        **filetypes** is a dictionary with the file type as
        key and a sub-dictionary with driver and extensions
        as keys and the corresponding driver and extensions
        as values. 
        It is a logical structure that maps a file type to
        its intake driver since each file type can have more 
        than one extension. This dictionary is looped to get
        the self._mappers for each extension.
        **Assumed each filetype has a single driver but more than
        one extension**
        """
        filetypes = {
            'excel': {
                'driver': 'fastbt.experimental.ExcelSource',
                'extensions': ['xls', 'xlsx']
            },
            'csv': {
                'driver': 'intake.source.csv.CSVSource',
                'extensions': ['csv', 'txt']
            },
            'hdf': {
                'driver': 'fastbt.experimental.HDFSource',
                'extensions': ['h5', 'hdf5']
            }
        }
        self._mappers =  {}
        for k,v in filetypes.items():
            for ext in v['extensions']:
                self._mappers[ext] = v['driver']
    

    def generate_catalog(self):
        """
        Generate catalog
        #TO DO#
        1. Replace multiple dots with underscores in filenames
        """
        dct = {}
        dct['sources'] = {}
        src = dct['sources']
        def metadata():
            """
            metadata generation for the file; has access to
            all variables inside the parent function
            """
            return {
                'args': {
                    first_arg: os.path.join(dirpath, file)                  
                },
                'driver': self._mappers[ext],
                'description': '',
                'metadata': {
                    'extension': ext,
                    'mode': mode
                }
            }

        for dirpath,dirnames,filenames in os.walk(self._directory):
            dirname = dirpath.split('/')[-1] #
            if dirname in self._file_dirs:
                mode = 'file'
                for file in filenames:
                    ext = file.split('.')[-1]
                    if 'csv' in ext:
                        first_arg = 'urlpath'
                    else:
                        first_arg = 'datapath'
                    if ext in self._mappers:
                        src[file.split('.')[0]] = metadata()
            else:
                mode = 'dir'
                # If the directory has any files                
                if len(filenames) > 0:
                    # Check the extension of the first file in directory
                    ext = filenames[0].split('.')[-1]
                    file = '*'
                    if 'csv' in ext:
                        first_arg = 'urlpath'
                        file = '*'
                    else:
                        first_arg = 'datapath'
                        file = ''
                    if ext in self._mappers:
                        src[dirname] = metadata()
        return dct

def candlestick_plot(data):
    """
    return a bokeh candlestick plot
    data
        dataframe with open,high,low and close columns
    Note
    -----
    Prototype copied from the below link
    https://bokeh.pydata.org/en/latest/docs/gallery/candlestick.html
    """
    from math import pi
    from bokeh.plotting import figure, show, output_file
    from bokeh.models import ColumnDataSource
    df = data.copy()
    df["date"] = pd.to_datetime(df["date"])
    df['color'] = ['green' if x > y else 'red' for (x,y) in 
    zip(df.close, df.open)]
    source = ColumnDataSource()
    source.data = source.from_df(df)
    w = 10*60*1000 # half day in ms
    TOOLS = "pan,wheel_zoom,box_zoom,reset,save"
    p = figure(x_axis_type="datetime", tools=TOOLS, 
        title = "Candlestick", plot_width=800,
        tooltips=[
            ('date', '@date{%F}'),
            ('open', '@open{0}'),
            ('high', '@high{0}'),
            ('low', '@low{0}'),
            ('close', '@close{0}')
        ])
    p.hover.formatters= {'date': 'datetime'}
    p.xaxis.major_label_orientation = pi/4
    p.grid.grid_line_alpha=0.3
    p.segment('date', 'high', 'date', 'low', 
        color="black", source=source)
    p.vbar('date', w, 'open', 'close', 
        fill_color='color', line_color="black", source=source)
    return p, source


def calendar_plot(data, field='ret'):
    """
    return a calendar plot
    data
        dataframe with year and month columns
    field
        field to plot values
    Note
    -----
    Prototype copied from bokeh gallery
    https://bokeh.pydata.org/en/latest/docs/gallery/unemployment.html
    """
    from math import pi
    from bokeh.models import LinearColorMapper, BasicTicker, PrintfTickFormatter, ColorBar
    from bokeh.plotting import figure
    from bokeh.palettes import Spectral
    df = data.copy()
    # Type conversion
    df['year'] = df.year.astype('str')
    df['month'] = df.month.astype('str')
    years = list(df.year.unique())
    months = [str(x) for x in range(12,0,-1)]
    colors = list(reversed(Spectral[6]))
    mapper = LinearColorMapper(palette=colors, 
                           low=df[field].min(), high=df[field].max())
    TOOLS = "hover,save,pan,box_zoom,reset,wheel_zoom"
    p = figure(title="Calendar Plot",
           x_range=years, y_range=list(reversed(months)),
           x_axis_location="above", plot_width=1000, plot_height=600,
           tools=TOOLS, toolbar_location='below',
           tooltips=[('date', '@year-@month'), ('return', '@{}'.format(field))])
    # Axis settings
    p.grid.grid_line_color = None
    p.axis.axis_line_color = None
    p.axis.major_tick_line_color = None
    p.axis.major_label_text_font_size = "10pt"
    p.axis.major_label_standoff = 0
    p.xaxis.major_label_orientation = pi / 3

    p.rect(x="year", y="month", width=1, height=1,
       source=df, fill_color={'field': field, 'transform': mapper},
       line_color='black', line_width=0.5, line_alpha=0.3)

    color_bar = ColorBar(color_mapper=mapper, major_label_text_font_size="8pt",
                     ticker=BasicTicker(desired_num_ticks=len(colors)),
                     formatter=PrintfTickFormatter(format="%d%%"),
                     label_standoff=6, border_line_color=None, location=(0, 0))
    p.add_layout(color_bar, 'right')
    return p

def summary_plot(data):
    """
    Given a dataframe, create a widget with condition and list
    of columns to provide summary data
    data
        dataframe
    Note
    -----
     * Condition is a valid eval string supported by pandas
     * Multiple columns can be selected
     * Summary statistics provided by the describe method

    """
    from bokeh.models import (
        TextInput, Button, Select, MultiSelect,
        ColumnDataSource, PreText,Paragraph
        )
    from bokeh.plotting import figure
    from bokeh.layouts import row, column, layout

    df = data.copy()

    def document(doc):
        condition = TextInput(title='Enter your condition')
        col = MultiSelect(title='Select the columns', options=list(df.columns))
        button = Button(label='Update')
        pre = PreText()
        pre.text = condition.value

        def update():
            cond = condition.value
            cols = col.value
            text = df.query(cond)[cols].describe()
            pre.text = str(text)

        button.on_click(update)

        l = layout([
                [[condition,button], col],
                pre
            ])
        doc.add_root(l)

    return document

def slider_plot(data, cols):
    """
    Given a dataframe, create a widget with range slider
    data
        dataframe
    cols
        columns for which sliders are to be created
    """
    from bokeh.models import (
        TextInput, Button, RangeSlider, MultiSelect,
        ColumnDataSource, PreText
        )
    from bokeh.plotting import figure
    from bokeh.layouts import row, column, layout, gridplot

    df = data.copy()

    def document(doc):
        sliders = []
        pre = PreText(text='something')
        select = MultiSelect(title='Select the columns', options=list(df.columns))
        button = Button(label='Update')
        for col in cols:
            MIN,MAX = df[col].min(), df[col].max()
            STEP = (MAX-MIN)/100
            slider = RangeSlider(start=MIN, end=MAX, step=STEP,
                value=(MIN,MAX),title=col)
            sliders.append(slider)

        def update():
            values = []
            txt = '({col} > {low}) & ({col} < {high})'
            for slider in sliders:
                low,high = slider.value
                low,high = float(low), float(high)
                formula = txt.format(col=slider.title,low=low,high=high)
                values.append(formula)
            q = '&'.join(values)
            summary_cols = select.value
            text = df.query(q)[summary_cols].describe()
            pre.text = str(text)

        button.on_click(update)

        l = layout(
            [column(sliders), [select,button]],
            pre)
        doc.add_root(l)

    return document


def run_simulation(data, size=0.3, num=1000, column=None, function=np.mean):
    """
    run a simulation on the given data by drawing repeated samples
    and evaluating a metric
    data
        a pandas dataframe
    size
        size of the sample - float/int
        if size is a float and less than , it is considered a percentage
        in case of a num it is considered as the number of samples to take
    num
        number of simulations to be run
    column
        column for which sample is to be taken.
        If None, the entire dataframe is sampled and this is considerably slow
    function
        function to be run on the column - string/function
        default mean

    returns a pandas Series with the result for each sample taken
    """
    choice = np.random.choice
    if size < 1:
        N = int(len(data) * size)
    else:
        N = size
    collect = []
    if column is None:
        # Take sample on the whole dataframe
        for i in range(num):
            sample = function(data.sample(N))
            collect.append(sample)
    else:
        # Take sample on a particular column
        # considerably faster since this is a numpy version
        col = data[column].values
        for i in range(num):
            sample = function(choice(col, N))
            collect.append(sample)
    return pd.Series(collect)

def generate_parameters(dict_of_parameters):
    """
    Generate a list of parameters for backtest function
    dict_of_parameters
        dictionary of parameters in the given format
    Note
    -----
    Only one level of nested dictionary is parsed
    """
    from itertools import product
    d = dict_of_parameters.copy()
    lst = []
    def simple(dictionary, updt):
        # An inner function for ugly lookup
        # TO DO: Think of better way -> recursion
        listed = []
        for k,v in dictionary.items():
            if isinstance(v, list):
                listed.append([{k:val} for val in v])
            elif isinstance(v, str):
                listed.append([{k:v}])
        temp = list(product(*listed))
        lstk = []
        for tp in temp:
            temp_dict = updt.copy()
            for t in tp:
                temp_dict.update(t)        
            lstk.append(temp_dict)
        return lstk

    for k,v in d.items():
        if isinstance(v, list):
            lst.append([{k:val} for val in v])
        elif isinstance(v, str):
            lst.append([{k:v}])
        elif isinstance(v, dict):
            dict_lst = []
            for k1,v1 in v.items():
                lst2 = simple(d[k][k1], {k:k1})
                dict_lst.extend(lst2)    
            lst.append(dict_lst)
    return lst

@njit
def traverse(high, low, points):
    """
    See whether the price points are hit in the given order
    high
        high values as numpy array
    low
        low values as numpy array
    points
        list or numpy array of values to check
    returns a 4-tuple with
      1. an array indicating whether the values in 
      the points list is hit; 1 indicates the value is hit
      2. an array of timesteps indicating when the
      value is hit; this is just the iteration cycle
      3. high value when the last point is hit or the 
      end of the iteration cycle if the point is not hit
      4. low value when the last point is hit or the 
      end of the iteration cycle if the point is not hit
    Note
    ----
    1. This function checks whether the points are hit
    in the given order. 
    2. A point is considered hit if it is between high and
    low value
    3. high and low values are considered to be array of equal
    size with the value of high always greater than or equal
    to the value of low at every timestep
    """
    j = 0
    price = points[j]
    hit = np.zeros(len(points))
    timesteps = np.zeros(len(points))
    for i in range(len(high)):
        if low[i] < price < high[i]:
            hit[j] = 1
            timesteps[j] = i
            j+=1
            if j == len(points):
                break
            else:
                price = points[j]
    return (hit, timesteps, high[i], low[i])
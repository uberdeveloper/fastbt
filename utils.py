import pandas as pd
import itertools as it

def multi_args(function, constants, variables, isProduct=False):
    """
    Run a function on different parameters and
    aggregate results
    function
        function to be parametrized
    constants
        arguments that would remain constant
        throughtout all the scenarios
        dictionary with key being argument name
        and value being the argument value
    variables
        arguments that need to be varied
        dictionary with key being argument name
        and value being list of argument values
        to substitute
    isProduct
        list of variables for which all combinations
        are to be tried out.

    By default, this function zips through each of the
    variables but if you need to have the Cartesian
    product, specify those variables in isProduct

    returns a Series with different variables and
    the results
    """
    from functools import partial
    import concurrent.futures

    MAX_LIMIT = 1000
    func = partial(function, **constants)
    arg_list = []
    if isProduct:
        args = it.product(*variables.values())
    else:
        args = zip(*variables.values())
    keys = variables.keys()
    with concurrent.futures.ProcessPoolExecutor() as executor:
        tasks = []
        for i, arg in enumerate(args):
            kwds = {a:b for a,b in zip(keys, arg)}
            tasks.append(executor.submit(func, **kwds))
            arg_list.append(arg)
            i += 1
            if i >= 1000:
                print('MAX LIMIT reached')
                break
    result = [task.result() for task in tasks] 
    print(arg_list)
    s = pd.Series(result)
    s.name = 'values'
    s.index = pd.MultiIndex.from_tuples(arg_list, names=keys)
    return s
    
if __name__ == "__main__":
    pass


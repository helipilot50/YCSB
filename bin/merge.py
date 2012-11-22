#!/usr/bin/python

import os
import re
import string
from ordereddict import OrderedDict

# special wrapper over dict to get rid of
# silly defensive ifs like
#    oc = ... # operation code
#    if not(oc in stats):
#        stats[oc] = {}
#    if not(mt in stats[oc]):
#        stats[oc][mt] = {}
#    # now it is safe to access
#    stats[oc][mt][cn] = float(m1.group(3))

class NestedDict(dict):
    def __getitem__(self, key):
        if key in self: return self.get(key)
        return self.setdefault(key, NestedDict())

def avg(seq):
    return sum(seq) / float(len(seq))

def tab_str(seq):
    return '\t'.join(map(str, seq))

def merge():
    """grab all *.out, extract statistics from there and merge into TSV file """
    fold_functions = OrderedDict()
    # each string is inherently a regex, and those regexes should be mutually
    # exclusive. The order of putting items in fold_functions defines the order
    # of columns
    fold_functions['RunTime']               = max
    fold_functions['Throughput']            = sum
    fold_functions['Operations']            = sum
    fold_functions['AverageLatency']        = avg
    fold_functions['MinLatency']            = min
    fold_functions['MaxLatency']            = max
    fold_functions['95thPercentileLatency'] = max
    fold_functions['99thPercentileLatency'] = max
    fold_functions['Return=0']              = sum
    fold_functions['Return=[^0].*']         = sum
    metrics = fold_functions.keys()
    regexps = map(re.compile, metrics)
    cns = []
    # trying each regexp for each line is TERRIBLY slow, therefore
    # we need to obtain searchable prefix to make preprocessing
    prefixes = map(lambda mt: str(re.search('\w+', mt).group(0)), metrics)
    # other stuff
    stats = NestedDict()
    items = filter(lambda x: str(x).endswith('.out'), os.listdir('.'))
    pcn = re.compile(r'.*?-c(\d)\.out')
    pln = re.compile(r'\[(\w+)\], (.*?), (\d+(\.\d+)?)')
    # gather stats from all files=items
    for item in items:
        with open(item) as file:
            m0 = pcn.search(item)
            if m0:
                cn = m0.group(1)
                cns.append(cn)
                for line in file:
                    for i in range(len(prefixes)):
                        pr = prefixes[i]
                        if pr in line:
                            m1 = (regexps[i]).search(line)
                            m2 = pln.search(line)
                            if m1 and m2:
                                oc = m2.group(1) # operation code
                                # cl = m2.group(2) # column
                                mt = metrics[i]
                                if stats[oc][mt][cn]:
                                    stats[oc][mt][cn] += float(m2.group(3))
                                else:
                                    stats[oc][mt][cn] = float(m2.group(3))
    cns.sort()
    # stats is the dictionary like this:
    #OVERALL RunTime {'1': 1500.0, '3': 2295.0, '2': 1558.0, '4': 2279.0}
    # ...
    #UPDATE Return=1 {'1': 477.0, '3': 488.0, '2': 514.0, '4': 522.0}
    headers1 = ['']
    headers2 = ['']
    # operations are sorted in the [OVERALL, READ, UPDATE] order
    for oc, ostats in sorted(stats.items()):
        keys = sorted(ostats.keys(), key=metrics.index)
        for mt in keys:
            headers1.append(oc) # operation code like OVERALL, READ, UPDATE
            headers2.append(mt) # metric name like RunTime, AverageLatency etc
    print(tab_str(headers1))
    print(tab_str(headers2))
    # write the values for each client
    for cn in cns:
        row = [str(cn)]
        for oc, ostats in sorted(stats.items()):
            # oc is the operation code oc = 'OVERALL'
            keys = sorted(ostats.keys(), key=metrics.index)
            for mt in keys:
                row.append(ostats[mt][str(cn)])
        print(tab_str(row))
        # now write the totals
    row = ['Total']
    for oc, ostats in sorted(stats.items()):
        # oc is the operation code oc = 'OVERALL'
        keys = sorted(ostats.keys(), key=metrics.index)
        for mt in keys:
            row.append(fold_functions[mt](ostats[mt].values()))
    print(tab_str(row))

if __name__=='__main__':
    merge()

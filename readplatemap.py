import time, copy, pickle
import os, os.path
import sys
import numpy


def myeval(c):
    if c == "None":
        c = None
    elif c == "nan" or c == "NaN":
        c = numpy.nan
    else:
        temp = c.lstrip("0")
        if (temp == "" or temp == ".") and "0" in c:
            c = 0
        else:
            c = eval(temp)
    return c


def readsingleplatemaptxt(p, returnfiducials=False):
    f = open(p, mode="r")
    ls = f.readlines()
    f.close()
    if returnfiducials:
        s = ls[0].partition("=")[2].partition("mm")[0].strip()
        if (
            not "," in s[s.find("(") : s.find(")")]
        ):  # needed because sometimes x,y in fiducials is comma delim and sometimes not
            print("WARNING: commas inserted into fiducials line to adhere to format.")
            print(s)
            s = (
                s.replace("(   ", "(  ")
                .replace("(  ", "( ")
                .replace("( ", "(")
                .replace("   )", "  )")
                .replace(",  ", ",")
                .replace(", ", ",")
                .replace("  )", " )")
                .replace(" )", ")")
                .replace("   ", ",")
                .replace("  ", ",")
                .replace(" ", ",")
            )
            print(s)
        fid = eval("[%s]" % s)
        fid = numpy.array(fid)
    for count, l in enumerate(ls):
        if not l.startswith("%"):
            break
    keys = ls[count - 1][1:].split(",")
    keys = [(k.partition("(")[0]).strip() for k in keys]
    dlist = []
    for l in ls[count:]:
        sl = l.split(",")
        d = dict([(k, myeval(s.strip())) for k, s in zip(keys, sl)])
        dlist += [d]
    if returnfiducials:
        return dlist, fid
    return dlist


def readplatemaptxt(
    folder="C:/Users/gregoire/Documents/CaltechWork/platemaps/V5.2",
    searchstr="%dmap",
    platenumlist=[1, 2, 3],
    codes=[0],
    createcomps=True,
):
    dlist = []
    for fn in os.listdir(folder):
        for i in platenumlist:
            if (searchstr % i) in fn:
                dlisttemp = readsingleplatemaptxt(os.path.join(folder, fn))
                for d in dlisttemp:
                    d["plateind"] = i - 1
                dlist += dlisttemp
    dlist = [d for d in dlist if d["code"] in codes]
    if createcomps:
        for d in dlist:
            c = numpy.array([d[el] for el in ["A", "B", "C", "D"]])
            if c.sum() > 0:
                c /= c.sum()
            d["compositions"] = c
    return dlist


# dlist=readplatemaptxt()

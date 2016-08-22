import numpy
import os

def readrcp(rcpfile):
    # tab depth used for dictionary nesting
    def getKeyDepth(key):
        counter = (len(key)-len(key.lstrip()))/4
        return counter

    f = open(rcpfile, 'rU')
    rcp = f.readlines()
    f.close()

    # make d[k, v] from lines of 'k: v', recurse function call if v is empty
    def readKeys(rcplines, depth=0):
        d = {}
        for i, cline in enumerate(rcplines):
            cdepth = getKeyDepth(cline)
            if cdepth != depth:
                next
            else:
                k = cline.split(':')[0].rstrip('\r\n')
                try:
                    v = cline.split(': ')[1].lstrip().rstrip('\r\n')
                except:
                    remaining_cdepths=[l for l, v in enumerate([getKeyDepth(line) \
                        for line in rcplines[i+1:]]) if v==cdepth]
                    if len(remaining_cdepths)==0:
                        v = readKeys(rcplines[i+1:], depth=cdepth+1)
                    else:
                        v = readKeys(rcplines[i+1:i+remaining_cdepths[0]+1], depth=cdepth+1)
                    pass
                d[k.lstrip()] = v
                if i == len(rcplines) | cdepth > getKeyDepth(rcplines[i+1]):
                    return d
        return d

    return readKeys(rcp)

def myeval(c):
    if c=='None':
        c=None
    elif c=='nan' or c=='NaN':
        c=numpy.nan
    else:
        temp=c.lstrip('0')
        if (temp=='' or temp=='.') and '0' in c:
            c=0
        else:
            c=eval(temp)
    return c

def readsingleplatemaptxt(p, returnfiducials=False,  erroruifcn=None, lines=None):
    if lines is None:
        try:
            f=open(p, mode='r')
        except:
            if erroruifcn is None:
                return []
            p=erroruifcn('bad platemap path')
            if len(p)==0:
                return []
            f=open(p, mode='r')

        ls=f.readlines()
        f.close()
    else:
        ls=lines
    if returnfiducials:
        s=ls[0].partition('=')[2].partition('mm')[0].strip()
        if not ',' in s[s.find('('):s.find(')')]: #needed because sometimes x,y in fiducials is comma delim and sometimes not
            print 'WARNING: commas inserted into fiducials line to adhere to format.'
            print s
            s=s.replace('(   ', '(  ',).replace('(  ', '( ',).replace('( ', '(',).replace('   )', '  )',).replace(',  ', ',',).replace(', ', ',',).replace('  )', ' )',).replace(' )', ')',).replace('   ', ',',).replace('  ', ',',).replace(' ', ',',)
            print s
        fid=eval('[%s]' %s)
        fid=numpy.array(fid)
    for count, l in enumerate(ls):
        if not l.startswith('%'):
            break
    keys=ls[count-1][1:].split(',')
    keys=[(k.partition('(')[0]).strip() for k in keys]
    dlist=[]
    for l in ls[count:]:
        sl=l.split(',')
        d=dict([(k, myeval(s.strip())) for k, s in zip(keys, sl)])
        dlist+=[d]
    if not 'sample_no' in keys:
        dlist=[dict(d, sample_no=d['Sample']) for d in dlist]
    if returnfiducials:
        return dlist, fid
    return dlist

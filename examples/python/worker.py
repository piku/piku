import os, sys, time

for x in xrange(0,int(os.environ['RANGE'])):
    print x
    sys.stdout.flush()
    time.sleep(int(os.environ['INTERVAL']))

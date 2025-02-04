"""test_rdesigneur.py: 
"""
    
__author__           = "Dilawar Singh"
__copyright__        = "Copyright 2017-, Dilawar Singh"
__version__          = "1.0.0"
__maintainer__       = "Dilawar Singh"
__email__            = "dilawars@ncbs.res.in"
__status__           = "Development"

import sys
import os
import numpy as np
try:
    import rdesigneur as rd 
except RuntimeError as e:
    print( "[WARN ] Could not import rdesigneur. Most likely due to DISPLAY issue." )
    quit()
import moose
import rdesigneur as rd 

def test_rdes2():
    if moose.exists( '/model' ):
        moose.delete( '/model' )

    rdes = rd.rdesigneur(
        stimList = [['soma', '1', '.', 'inject', '(t>0.1 && t<0.2) * 2e-8' ]],
        plotList = [['soma', '1', '.', 'Vm', 'Soma membrane potential']]
    )
    rdes.buildModel()
    moose.reinit()
    moose.start( 0.3 )

def test_rdes1():
    rdes = rd.rdesigneur()
    rdes.buildModel()
    moose.showfields( rdes.soma )

def main( ):
    test_rdes1()
    test_rdes2()

if __name__ == '__main__':
    main()

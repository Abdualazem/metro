#!/usr/bin/env python


"""
Hybrid Metrology for ATLAS ITk

Reference Craig's Code just remove python ROOT, 
and it has more demand of Metrology

"""

__author__ = "Liejian Chen <chenlj@ihep.ac.cn>"
import sys
import matplotlib.pyplot as plt
import numpy as np
import math
from scipy import optimize
import argparse


parser = argparse.ArgumentParser(description='Hybrid Metrology for ATLAS ITk')
parser.add_argument('--offset', 
                    action='store', 
                    dest='offset',
                    default=30, 
                    type=int, 
                    help='offset of bridge tool in [um]')

parser.add_argument('--glue_target', 
                    action='store', 
                    dest='glue_target',
                    default=80,
                    type=int, 
                    help='target of glue height in [um]')


parser.add_argument('--asic_thickness', 
                    action='store', 
                    dest='asic_thickness',
                    default=300,
                    type=int, 
                    help='ASIC thickness in [um]')



parser.add_argument('files', nargs='+',
                    help='input files list')

ARGS = parser.parse_args()


MICRONS_PER_TURN = 254   # thread of screw in terms of microns per full turn


def main():
    args = sys.argv[1:]
    

    if len(args) < 1:
        return usage()

    if len(ARGS.files) == 1:
        inputfile = ARGS.files[0]
        sys.stdout.write('ASCI_THICKNESS: %s um\n' % ARGS.asic_thickness)
        return plot_hybrid_glue_thickness(inputfile)

        
    if len(ARGS.files) ==2:
        inputfileHybrid = ARGS.files[0]
        inputfileBridge = ARGS.files[1]

        hybrid_heights = calculate_hybrid_heights(inputfileHybrid, "ZD")
        # calculate bridgetool value
        if len(hybrid_heights) == 0:
            hybrid_heights = calculate_hybrid_heights(inputfileHybrid, "Z")

        bridgetool_pin_points,bridgetool_pad_points,zd= bridgetool_value(inputfileBridge)
        glueb,gluef,bridgeb,bridgef = run_correction(
            bridgetool_pin_points, bridgetool_pad_points, hybrid_heights)
        plot_hybrid_glue_thickness(glueb,gluef,bridgeb,bridgef)
        return 


    if len(ARGS.files) == 3:
        inputfileHybrid = ARGS.files[0]
        inputfileHybrid_withASICs = ARGS.files[1]
        inputfileBridge = ARGS.files[2]
        hybrid_heights = calculate_hybrid_heights(inputfileHybrid, "ZD")
        if len(hybrid_heights) == 0:
            hybrid_heights = calculate_hybrid_heights(inputfileHybrid, "Z")

        hybrid_heights_withASICs = calculate_hybrid_heights(inputfileHybrid_withASICs, "ZD")
        if len(hybrid_heights_withASICs) == 0:
            hybrid_heights_withASICs = calculate_hybrid_heights(inputfileHybrid_withASICs, "Z")

        measured_glue_thickness = calculate_measured_glue_thickness(
            hybrid_heights, hybrid_heights_withASICs)

        bridgetool_pin_points,bridgetool_pad_points,zd= bridgetool_value(inputfileBridge)
        glueb,gluef,bridgeb,bridgef = run_correction(
            bridgetool_pin_points, bridgetool_pad_points, hybrid_heights)

        plot_glue_thickness(measured_glue_thickness, gluef)


def usage():
    sys.stdout.write('''
please type -h for help:  
    metroHybrid.py -h 
\n''')


def csv_reader(filename):
    with open(filename) as f:
        data = f.readlines()
        f.close()

    x = []
    y = []
    z = []
    zd = []
    nlines = len(data)
    for line in range(nlines):
        value = data[line].split()
        if value[0]=='X':
            x.append(1e3*float(value[3]))  # x position
        elif value[0]=='Y':
            y.append(1e3*float(value[3]))  # y position
        elif value[0]=='Z':
            z.append(1e3*float(value[3]))  # z position
        elif value[0]=='ZD':
            zd.append(1e3*float(value[3])) # z distance

    return x,y,z,zd

def hybrid_value(filename):
    x,y,z,zd=csv_reader(filename)
    print("hybrid value zd:"+str(zd))
    print("hybrid value z: "+str(z))
    return z,zd

def bridgetool_value(filename):
    x,y,z,zd=csv_reader(filename)
    bridgetool_pin_points=[x[0:4], y[0:4], z[0:4]]
    bridgetool_pad_points=[x[4:], y[4:], z[4:]]
    return bridgetool_pin_points,bridgetool_pad_points,zd

def fitPlaneToPoints(points):
    fitFun = lambda par, xydata: par[0]*xydata[0]+par[1]*xydata[1]+par[2]
    errorFun = lambda par, xydata, z: fitFun(par, xydata)-z
    parInit = np.array([0.1,0.1,0.1])
    xydata_pos = np.array([points[0],points[1]])
    z_pos = np.array(points[2])
    fitRes = optimize.leastsq(errorFun, parInit[:], args=(xydata_pos,z_pos))
    parFit = fitRes[0]
    parCov = fitRes[1]
    return [parFit[0],parFit[1],parFit[2]]


def derive_plane_correction(points,param):
    # use first point as pivot and correct plane definition
    points=np.array(points).T
    pivot = points[0]
    corrections=[0.0,0.0,0.0,0.0]
    param[2] -= (param[0]*pivot[0] + param[1]*pivot[1] + param[2]) - pivot[2]

    # derive corrections based on this
    for i in range(1,4):
        p = points[i]
        corrections[i] += (param[0]*p[0]+param[1]*p[1]+param[2]) - p[2]
        return corrections

def hybrid_corrections(glue_thickness):
    target = ARGS.glue_target + ARGS.offset 
    sys.stdout.write('Target = %s, Offset = %s\n' %(ARGS.glue_target, ARGS.offset))
    thickness_corrections = np.mean(target-glue_thickness)
    return thickness_corrections

def calculate_hybrid_heights(file_name, zoption):
    h_thickness=[]
    z_pos,z_d=hybrid_value(file_name)
    #print('Read Z pos: '+str(np.abs(z_pos)))
    #print('Read ZD pos: '+str(np.abs(z_d)))
    #It depends on the hybrid metrology
    if zoption == "Z":
        #print('Read Z pos: '+str(np.abs(z_pos)))
        h_thickness.append(np.abs(z_pos))
    elif zoption == "ZD":
        h_thickness.append(z_d)

    hybrid_heights = np.mean(h_thickness,axis=0)
    print_hybrid_heights(hybrid_heights, "before")

    return hybrid_heights

def calculate_measured_glue_thickness(hybrid_heights, hybrid_heights_withASIC):
    glue_thickness = hybrid_heights + hybrid_heights_withASIC - ARGS.asic_thickness
    return glue_thickness

def calculate_glue_thickness(bridge_heights, hybrid_heights, name):
    glue_thickness = bridge_heights + hybrid_heights - ARGS.asic_thickness
    print_glue_thickness(glue_thickness, name)
    return glue_thickness

def print_calibration(corrections,name):
    print("==============="+name+"=============")
    for i in range(0,4):
        if corrections[i] < 0.0:
            instructions = "PIN "+str(i)+"  =  "+"{:05.1f}".format(corrections[i]) + " um  =  "
            instructions += "ANTI-CLOCKWISE "
        else:
            instructions = "PIN "+str(i)+"  =   "+"{:04.1f}".format(corrections[i]) + " um  =  "
            instructions += "  CLOCKWISE    "

        instructions += "{:.2f}".format(math.fabs(corrections[i]/MICRONS_PER_TURN))+" turns"
        instructions += " = {:.0f} degrees".format(math.fabs(corrections[i]/MICRONS_PER_TURN)*360)
        print(instructions)
        print("")

def makeResidualsHist(points, param, name):
    points=np.array(points)
    param=np.array(param)
    residual=((param[0]*points[0]+param[1]*points[1]-points[2]+param[2]) / \
              np.sqrt( param[0]*param[0] + param[1]*param[1] + 1 ))
    print_residual(residual, name)
    return residual

def print_residual(residual, name):
    print("-----------  Residuals of " + str(name) + "---------------")
    residual = np.reshape(residual, (4, int(len(residual)/4)))
    print("Residual at PINS 0: " + np.array2string(residual[0],
                                                   formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("Residual at PINS 1: " + np.array2string(residual[1],
                                                   formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("Residual at PINS 2: " + np.array2string(residual[2],
                                                   formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("Residual at PINS 3: " + np.array2string(residual[3],
                                                   formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("")

def print_hybrid_heights(hybrid_heights, name):
    print("-----------  Hybrid heights of " + str(name) + "---------------")
    print("Hybrid heights: " + np.array2string(hybrid_heights,\
                                               formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("")


def print_bridge_heights(bridge_heights, name):
    print("-----------  Bridge heights of " + str(name) + "---------------")
    print("Bridge heights: " + np.array2string(bridge_heights,\
                                               formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("")


def print_glue_thickness(glue_thickness, name):
    print("-----------  Glue thickness of " + str(name) + "---------------")
    print("Glue thickness: " + np.array2string(glue_thickness,\
                                               formatter={'float_kind':lambda x: "%3.2f" % x}) + " um")
    print("")


def calculateBridgeHeights(points,param,name):
    points=np.array(points)
    param=np.array(param)
    zmean = (param[0]*points[0]+param[1]*points[1]-points[2]+param[2]) \
            / np.sqrt(param[0]*param[0]+param[1]*param[1]+1)
    zmean=np.reshape(zmean,(4,10))
    zmean=np.mean(zmean,axis=0)
    print_bridge_heights(zmean,name)
    return zmean


def run_correction(bridgetool_pin_points, bridgetool_pad_points, hybrid_heights):
    # fit plane to touchdown and get residuals
    parameters_pins = fitPlaneToPoints(bridgetool_pin_points)
    residuals_pins = makeResidualsHist(bridgetool_pin_points,parameters_pins,"pins")

    # fit plane to ASIC pads and get residuals
    parameters_pads=fitPlaneToPoints(bridgetool_pad_points)
    residuals_pads = makeResidualsHist(bridgetool_pad_points,parameters_pads,"pads")

    # make histogram of the bridge heights before any correction
    bridge_heights_before = calculateBridgeHeights(bridgetool_pad_points, \
                                                   parameters_pins,"before")

    # calculate the predicted glue thicknesses with current setting
    glue_thickness_predicted_before = calculate_glue_thickness(bridge_heights_before, \
                                                               hybrid_heights, "before")

    # work out what change we need to make to get the pins in a plane parallel to the pads
    corrections=derive_plane_correction(bridgetool_pin_points,parameters_pads)
    print_calibration(corrections, "Mid corrections")
    bridge_pins_mid_corrected=np.array([bridgetool_pin_points[0], \
                                        bridgetool_pin_points[1], \
                                        np.add(bridgetool_pin_points[2],corrections)])
    parameters_pins_mid_corrected = fitPlaneToPoints(bridge_pins_mid_corrected)

    # bridge heights at this mid-point
    bridge_heights_mid = calculateBridgeHeights(bridgetool_pad_points, \
                                                parameters_pins_mid_corrected,"mid-point")

    glue_thickness_predicted_mid = calculate_glue_thickness(bridge_heights_mid, \
                                                            hybrid_heights, "mid-point")

    corrections += hybrid_corrections(glue_thickness_predicted_mid)
    print_calibration(corrections, "Final corrections")
    bridge_pins_corrected=np.array([bridgetool_pin_points[0], \
                                    bridgetool_pin_points[1], \
                                    np.add(bridgetool_pin_points[2],corrections)])
    parameters_pins_corrected = fitPlaneToPoints(bridge_pins_corrected)

    # test the corrected plane residuals (should be consistent with zero)
    residuals_pins = makeResidualsHist(bridge_pins_corrected, \
                                       parameters_pins_corrected, "pins_after")

    bridge_heights_after = calculateBridgeHeights(bridgetool_pad_points, \
                                                  parameters_pins_corrected,"after")

    # calculate the predicted glue thicknesses with current setting
    glue_thickness_predicted_after = calculate_glue_thickness(bridge_heights_after, \
                                                              hybrid_heights, "after")
    return glue_thickness_predicted_before, glue_thickness_predicted_after, \
        bridge_heights_before, bridge_heights_after


def plot_hybrid_glue_thickness(glueb,gluef,bridgeb,bridgef):
    fig=plt.figure(1,(10,7.5))
    plt.subplot(221)
    plt.plot(glueb,label='glue thickness before')
    plt.ylim((50,150))
    plt.legend()

    plt.subplot(222)
    plt.plot(gluef,label='glue thickness after')
    plt.ylim((50,150))
    plt.legend()

    plt.subplot(223)
    plt.plot(bridgeb,label='bridge tool before')
    plt.ylim((280,380))
    plt.legend()

    plt.subplot(224)
    plt.plot(bridgef,label='bridge tool after')
    plt.ylim((280,380))
    plt.legend()

    fig.show()
    raw_input('Please press enter here to close:')

def plot_glue_thickness(glue_thickness_measured,glue_thickness_predicted):
    fig=plt.figure(2,(10,7.5))
    plt.plot(glue_thickness_measured,'-*r',label='measured glue thickness')
    plt.plot(glue_thickness_predicted,'--ob',label='predicted glue thickness')
    plt.ylim((0,150))
    plt.legend()

    fig.show()
    raw_input('Please press enter here to close:')


def plot_hybrid_glue_thickness(filename): 
    zd = readHybridWithASICs(filename)
    glue_thickness = [h*1000-ARGS.asic_thickness for h in zd ]#
    print(glue_thickness)
    fig=plt.figure()
    plt.plot(glue_thickness)
    plt.ylabel('glue thickness [um]')
    fig.show()
    raw_input('Please press enter here to close:')

    
def readHybridWithASICs(filename):
    with open(filename) as f:
        data = f.readlines()
    f.close()

    z_pos = []
    z_d = []
    z_d.append(0) # Datum plane, no distance
    nlines = len(data)
    for line in range(nlines):
        value = data[line].split()
        if value[0]=='Z':
            #print(value[3])
            z_pos.append(float(value[3]))  # z position
        elif value[0]=='ZD':
            #print(value[3])
            z_d.append(float(value[3])) # z distance

    results = zip(z_pos,z_d)
    results = zip(*results)

    zd = z_d[1:11]
    return zd

    
if __name__ == '__main__':
    main()


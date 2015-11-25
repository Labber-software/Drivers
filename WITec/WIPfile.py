import struct
import numpy as np

def readTag(f, pos):
    f.seek(pos)
    d = f.read(4)
    tagNameLength = struct.unpack("<i", d)[0]
    tagName = f.read(tagNameLength)
    tagType = struct.unpack("<i", f.read(4))[0]
    tagDataStart = struct.unpack("<q", f.read(8))[0]
    tagDataEnd = struct.unpack("<q", f.read(8))[0]
    return [tagName, tagType, tagDataStart, tagDataEnd]

def readInt(f, pos):
    f.seek(pos)
    return struct.unpack("<i", f.read(4))[0]

def readDouble(f, pos):
    f.seek(pos)
    return struct.unpack("<d", f.read(8))[0]

def readIntFromTag(f, rootStart, rootEnd, node, descend):
    tag = findTag(f, rootStart, rootEnd, node, descend)
    if tag == None:
        return None
    else:
        return readInt(f, tag[2])

def readDoubleFromTag(f, rootStart, rootEnd, node, descend):
    tag = findTag(f, rootStart, rootEnd, node, descend)
    if tag == None:
        return None
    else:
        return readDouble(f, tag[2])

def readAllTags(f, start, end, depth, indices, parentName):
    if indices == None:
        indices = {}
    newIndex = -1
    pos = start
    while pos < end:
        tName, tType, tStart, tEnd = readTag(f, pos)            
        print "  " * depth + "[" + str(tType) + "] " + tName,
        if tType == 0:
            print " -> " + str(tStart) + ".." + str(tEnd)
            indices, newIndexRet = readAllTags(f, tStart, tEnd, depth+1, indices, tName)
            if newIndexRet >= 0:
                if parentName != "TData" and tName != "TData":
                    indices[newIndexRet] = [tName, tType, tStart, tEnd]
                else:
                    newIndex = newIndexRet
        elif tType == 2:
            f.seek(tStart)
            v = struct.unpack("<d", f.read(8))[0]
            print " -> " + str(v)
        elif tType == 5:
            f.seek(tStart)
            v = struct.unpack("<i", f.read(4))[0]
            print " -> " + str(v)
            if tName == "ID":
                newIndex = v
        elif tType == 9:
            f.seek(tStart)
            strLength = struct.unpack("<i", f.read(4))[0]
            print " -> " + f.read(strLength)
        else:
            print ""
        pos = tEnd
    return [indices, newIndex]

def findTag(f, start, end, search, descend):
    pos = start
    while pos < end:
        tName, tType, tStart, tEnd = readTag(f, pos)
        if tName == search:
            return [tName, tType, tStart, tEnd]
        if descend and tType == 0:
            subTag = findTag(f, tStart, tEnd, search)
            if subTag != None:
                return subTag
        pos = tEnd
    return None

def lastTagOfDataClass(f, start, end, type):
    pos = start
    retTag = None
    nextHasCorrectType = False
    while pos < end:
        tag = readTag(f, pos)
        if tag[1] == 9:
            f.seek(tag[2])
            strLength = struct.unpack("<i", f.read(4))[0]
            if f.read(strLength) == type:
                nextHasCorrectType = True
        elif tag[1] == 0:
            if nextHasCorrectType:
                retTag = tag
                nextHasCorrectType = False
        pos = tag[3]
    return retTag

def loadWIP(file):
    f = open(file, "rb")
    magicHeader = f.read(8)
    if not magicHeader:
        return "Error: EOF reached during magic header."

    #Read first tag
    rootName, rootType, rootStart, rootEnd = readTag(f, 8)
    if rootType > 0:
        return "Error: First tag not a tag list"

    #Read tags within first tag
    dataDict = readAllTags(f, rootStart, rootEnd, 1, None, None)[0]
    print ""
    print "Data-Dictionary:"
    print dataDict

    dataName, dataType, dataStart, dataEnd = findTag(f, rootStart, rootEnd, "Data", False) #Tag containing all datasets
    dsName, dsType, dsStart, dsEnd = lastTagOfDataClass(f, dataStart, dataEnd, "TDGraph") #last dataset of type "TDGraph"

    tdgName, tdgType, tdgStart, tdgEnd = findTag(f, dsStart, dsEnd, "TDGraph", False) #TDGraph node within the dataset


    #Load calibration
    xtID = readIntFromTag(f, tdgStart, tdgEnd, "XTransformationID", False) #XTransformationID node
    calibration = None
    if xtID > 0:
        transf = findTag(f, dataDict[xtID][2], dataDict[xtID][3], "TDSpectralTransformation", False)
        if transf != None:
            calibration = {}
            calibration["type"] = readIntFromTag(f, transf[2], transf[3], "SpectralTransformationType", False)
            poly = findTag(f, transf[2], transf[3], "Polynom", False)
            if poly != None:
                calibration["polynom"] = {}
                calibration["polynom"][0] = readDouble(f, poly[2])
                calibration["polynom"][1] = readDouble(f, poly[2]+8)
                calibration["polynom"][2] = readDouble(f, poly[2]+16)
            calibration["nC"] = readDoubleFromTag(f, transf[2], transf[3], "nC", False)
            calibration["LambdaC"] = readDoubleFromTag(f, transf[2], transf[3], "LambdaC", False)
            calibration["Gamma"] = readDoubleFromTag(f, transf[2], transf[3], "Gamma", False)
            calibration["Delta"] = readDoubleFromTag(f, transf[2], transf[3], "Delta", False)
            calibration["m"] = readDoubleFromTag(f, transf[2], transf[3], "m", False)
            calibration["d"] = readDoubleFromTag(f, transf[2], transf[3], "d", False)
            calibration["x"] = readDoubleFromTag(f, transf[2], transf[3], "x", False)
            calibration["f"] = readDoubleFromTag(f, transf[2], transf[3], "f", False)
            #Sanity check from gwyddion
            if calibration["type"] != 1 or calibration["m"] < 0.01 or calibration["f"] < 0.01 or calibration["nC"] < 0:
                calibration = None
                print "Warning: Calibration found but dismissed as unreasonable."
            

    print ""
    print "Calibration Data:"
    if calibration == None:
        print "No valid calbiration found."
    else:
        print calibration

    #Check if image data
    sizeX = readIntFromTag(f, tdgStart, tdgEnd, "SizeX", False)
    sizeY = readIntFromTag(f, tdgStart, tdgEnd, "SizeY", False)
    if sizeX != 1 or sizeY != 1:
        return "Error: Image data found."

    #GraphData node within the TDGraph tag
    gdName, gdType, gdStart, gdEnd = findTag(f, tdgStart, tdgEnd, "GraphData", False)

    #Check if datatype is ok
    dataType = readIntFromTag(f, gdStart, gdEnd, "DataType", False)
    if dataType != 9:
        return "Error: Unknown data type."

    #Read ranges
    rName, rType, rStart, rEnd = findTag(f, gdStart, gdEnd, "Ranges", False)
    f.seek(rStart)
    rangeX = struct.unpack("<i", f.read(4))[0]
    rangeY = struct.unpack("<i", f.read(4))[0]

    #Read the actual data
    dataY = []
    dName, dType, dStart, dEnd = findTag(f, gdStart, gdEnd, "Data", False)
    f.seek(dStart)
    for i in range(rangeY):
        dataY.append(struct.unpack("<f", f.read(4))[0])
    npdataY = np.array(dataY)

    #Create x-axis
    dataX = range(rangeY)
    if calibration != None:
        for i in range(rangeY):
            alpha = np.arcsin(calibration["LambdaC"] * calibration["m"] / calibration["d"] / 2.0 / np.cos(calibration["Gamma"] / 2.0)) - calibration["Gamma"] / 2.0
            betac = calibration["Gamma"] + alpha
            hc = calibration["f"] * np.sin(calibration["Delta"])
            lh = calibration["f"] * np.cos(calibration["Delta"])
            hi = calibration["x"] * (calibration["nC"] - i) + hc
            betah = betac + calibration["Delta"]
            if lh != 0.0:
                betai = betah - np.arctan(hi / lh)
                dataX[i] = calibration["d"] / calibration["m"] * (np.sin(alpha) + np.sin(betai))
    npdataX = np.array(dataX)

    #Approximate linear axis
    dx = (dataX[rangeY-1]-dataX[0])/(rangeY-1)
    x0 = dataX[0]
    maxDev = 0
    #check deviation
    for i in range(rangeY):
        d = abs(dataX[i]-(dx*i+x0))
        if d > maxDev:
            maxDev = d

    print ""
    print "Linearization results:"
    print "dx=" + str(dx) + "   x0=" + str(x0) + "   maxDev=" + str(maxDev)

    print ""
    return [npdataY, x0, dx]
    
if __name__ == "__main__":
    import sys
    print loadWIP(sys.argv[1])


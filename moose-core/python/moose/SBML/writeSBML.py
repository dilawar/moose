# -*- coding: utf-8 -*-
r'''
*******************************************************************
 * File:            writeSBML.py
 * Description:
 * Author:          HarshaRani
 * E-mail:          hrani@ncbs.res.in
 ********************************************************************/
/**********************************************************************
** This program is part of 'MOOSE', the
** Messaging Object Oriented Simulation Environment,
** also known as GENESIS 3 base code.
**           copyright (C) 2003-2017 Upinder S. Bhalla. and NCBS
Created : Friday May 27 12:19:00 2016(+0530)
Version
Last-Updated: Wed 8 Jan 14:15:10 2020(+0530)
          By: HarshaRani
**********************************************************************/
/****************************
2020
Jan 08: added function to write Concchannel in form of MMenz
        Km in the kinetic law for MMenz is written to the power based on the number of substrate
2019
July 18: added a call for autolayout, this was required for cspace model while trying to write from cmd line
         while writting file, the filepath is checked
         now even for cplxpool's x and y co-ordinates,diff and motor constant are added
Jan 29: getColor are taken from chemConnectUtil, group's width and height are written
2018
Dec 07: using fixXreac's restoreXreacs function to remove xfer
Dec 03: add diff and motor constants to pool
Nov 30: group id is changed from name to moose_id and group.name is added along with annotation for group listing
Nov 22: searched for _xfer_ instead of xfer
Nov 12: xfer cross compartment molecules are not written to SBML instead written the original molecule also for connecting Reaction and Enzyme 
Nov 06: All the Mesh Cyl,Cube,Neuro,Endo Mesh's can be written into SBML format with annotation field where Meshtype
        numDiffCompts,isMembraneBound and surround are written out.
        For EndoMesh check made to see surround is specified
Oct 20: EndoMesh added to SBML
Oct 16: CylMesh's comparment volume is written, but zeroth volex details are populated 
Oct 13: CylMesh are written to SBML with annotation field and only zeroth element/voxel (incase of cylMesh) of moose object is written
Oct 1 : corrected the spell of CyclMesh-->CylMesh, negating the yaxis for kkit is removed 
Apr 30: indentation corrected while writting annotation for enzymecomplex
Jan 6 : for Product_formation_, k3 units depends on noofSub, prd was passed which is fixed
2017
Dec 15: If model path exists is checked
        Enz cplx is written only if enz,cplx,sub, prd exist, a clean check is made
        Checked if function exist inputs and also if expr is exist, then written.
Aug 8 : removed "findCompartment" function to chemConnectUtil and imported the function from the same file
        convertSpecialChar for setId and convertSpecialCharshot for setName.
        specialChar like /,\,[,],space are not allowed as moose doesn't take
Aug 3 : Added recalculatecoordinates,cleanup in groupName
'''

import sys
import re
import os
import moose
from moose.SBML.validation import validateModel
from moose.chemUtil.chemConnectUtil import xyPosition,mooseIsInstance,findCompartment,getColor,setupItem,setupMeshObj
from moose.chemUtil.graphUtils import *
from moose.fixXreacs import restoreXreacs
import numpy as np

foundLibSBML_ = False
try:
    from libsbml import *
    foundLibSBML_ = True
except Exception as e:
    pass

def checkPath( dirName):
    path = dirName
    if (dirName == "~" or not dirName ):
        if dirName:
            dirName = os.path.expanduser(dirName)
        else:
            dirName = os.getcwd()
    
    if os.access(dirName, os.W_OK) is not True:
        dirName = os.getcwd()
        print(path +" not writable, writting to "+dirName+ " directory")
        return dirName
    else:
        return dirName

def mooseWriteSBML(modelpath, filename, sceneitems={}):
    global foundLibSBML_
    msg = " "
    if not foundLibSBML_:
        print('No python-libsbml found.'
            '\nThis module can be installed by following command in terminal:'
            '\n\t easy_install python-libsbml or'
            '\n\t apt-get install python-libsbml'
            )
        return -2, "Could not save the model in to SBML file. \nThis module can be installed by following command in terminal: \n\t easy_install python-libsbml or \n\t apt-get install python-libsbml",''

    #sbmlDoc = SBMLDocument(3, 1)
    filepath, filenameExt = os.path.split(filename)
    filepath = checkPath(filepath)
    if filenameExt.find('.') != -1:
        filename = filenameExt[:filenameExt.find('.')]
    else:
        filename = filenameExt
    
    # validatemodel
    sbmlOk = False
    global spe_constTrue
    spe_constTrue = []
    global nameList_
    nameList_ = []

    xcord,ycord = [],[]
    if not moose.exists(modelpath):
        return False, "Path doesn't exist"
    elif moose.exists(modelpath):
        moose.fixXreacs.restoreXreacs(modelpath)
        checkCompt = moose.wildcardFind(modelpath+'/##[0][ISA=ChemCompt]')
        
        mObj = moose.wildcardFind(moose.element(modelpath).path+'/##[0][ISA=PoolBase]'+','+
                                  moose.element(modelpath).path+'/##[0][ISA=ReacBase]'+','+
                                  moose.element(modelpath).path+'/##[0][ISA=EnzBase]'+','+
                                  moose.element(modelpath).path+'/##[0][ISA=StimulusTable]')
        for p in mObj:
            if not isinstance(moose.element(p.parent),moose.CplxEnzBase):
                if moose.exists(p.path+'/info'):
                    xcord.append(moose.element(p.path+'/info').x)
                    ycord.append(moose.element(p.path+'/info').y)
                    getColor(moose.element(p.path+'/info').path)
        recalculatecoordinates(modelpath,mObj,xcord,ycord)
    positionInfoexist = False

    xmlns = SBMLNamespaces(3, 1)
    xmlns.addNamespace("http://www.w3.org/1999/xhtml", "xhtml")
    xmlns.addNamespace("http://www.moose.ncbs.res.in", "moose")
    xmlns.addNamespace("http://www.sbml.org/sbml/level3/version1/groups/version1", "groups")
    sbmlDoc = SBMLDocument(xmlns)
    sbmlDoc.setPackageRequired("groups",bool(0))

    cremodel_ = sbmlDoc.createModel()
    cremodel_.setId(filename)
    cremodel_.setTimeUnits("time")
    cremodel_.setExtentUnits("substance")
    cremodel_.setSubstanceUnits("substance")
    cremodel_.setVolumeUnits("volume")
    cremodel_.setAreaUnits("area")
    cremodel_.setLengthUnits("length")
    neutralNotes = ""

    specieslist = moose.wildcardFind(modelpath + '/##[0][ISA=PoolBase]')
    
    if specieslist:
        neutralPath = getGroupinfo(specieslist[0])
        if moose.exists(neutralPath.path + '/info'):
            neutralInfo = moose.element(neutralPath.path + '/info')
            neutralNotes = neutralInfo.notes
        if neutralNotes != "":
            cleanNotes = convertNotesSpecialChar(neutralNotes)
            notesString = "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n \t \t" + \
                neutralNotes + "\n\t </body>"
            cremodel_.setNotes(notesString)

    srcdesConnection = {}

    writeUnits(cremodel_)
    
    modelAnno = writeSimulationAnnotation(modelpath)
    
    if modelAnno:
        cremodel_.setAnnotation(modelAnno)
    groupInfo = {}
    reacGroup = {}
    compterrors =""
    compartexist, groupInfo,compterrors = writeCompt(modelpath, cremodel_)
    
    if compartexist == True:
        species = writeSpecies( modelpath,cremodel_,sbmlDoc,sceneitems,groupInfo)
        if species:
            writeFunc(modelpath, cremodel_)
        
        writeChannel(modelpath,cremodel_,sceneitems,groupInfo)

        writeReac(modelpath, cremodel_, sceneitems,groupInfo)
        
        writeEnz(modelpath, cremodel_, sceneitems,groupInfo)
        
        if groupInfo:
            for key,value in groupInfo.items():
                mplugin = cremodel_.getPlugin("groups")
                group = mplugin.createGroup()
                name = str(idBeginWith(moose.element(key).name))
                moosegrpId = name +"_" + str(moose.element(key).getId().value) + "_" + str(moose.element(key).getDataIndex())+"_"
                group.setId(moosegrpId) 
                group.setName(name)

                group.setKind("collection")
                if moose.exists(key.path+'/info'):
                    ginfo = moose.element(key.path+'/info')
                else:
                    ginfo = moose.Annotator(key.path+'/info')
                
                groupCompartment = findCompartment(key)
                
                grpAnno = "<moose:GroupAnnotation>"
                grpAnno = grpAnno + "<moose:Compartment>" + groupCompartment.name +"_"+ str(moose.element(groupCompartment).getId().value) +"_"+ str(moose.element(groupCompartment).getDataIndex())+"_"+"</moose:Compartment>\n"
                #grpAnno = grpAnno + "<moose:Compartment>" + groupCompartment.name + "_" + str(moose.element(groupCompartment).getId().value) + "_" + str(moose.element(groupCompartment).getDataIndex()) + "_"+ "</moose:Compartment>\n"
                if moose.element(key.parent).className == "Neutral":

                    grpAnno = grpAnno + "<moose:Group>" + key.parent.name + "</moose:Group>\n"
                    grpparent = key.parent.name + "_" + str(moose.element(key.parent).getId().value) + "_" + str(moose.element(key.parent).getDataIndex()) + "_"
                    grpAnno = grpAnno + "<moose:Parent>" + grpparent + "</moose:Parent>\n"
                else:
                    grpparent = groupCompartment.name + "_" + str(moose.element(groupCompartment).getId().value) + "_" + str(moose.element(groupCompartment).getDataIndex()) + "_"
                    grpAnno = grpAnno + "<moose:Parent>" + grpparent + "</moose:Parent>\n"
                
                if moose.exists(key.path+'/info'):
                    ginfo = moose.element(key.path+'/info')
                    textColor,color = getColor(ginfo)
                    if ginfo.height and ginfo.width:
                        grpAnno = grpAnno + "<moose:x>" + str(ginfo.x) + "</moose:x>\n"
                        grpAnno = grpAnno + "<moose:y>" + str(ginfo.y) + "</moose:y>\n"
                        grpAnno = grpAnno + "<moose:width>" + str(ginfo.width) + "</moose:width>\n"
                        grpAnno = grpAnno + "<moose:height>" + str(ginfo.height) + "</moose:height>\n"
                    if ginfo.color:
                        grpAnno = grpAnno + "<moose:bgColor>" + color + "</moose:bgColor>\n"
                    if ginfo.notes:
                        grpAnno = grpAnno + "<moose:Notes>" + ginfo.notes + "</moose:Notes>\n"
                grpAnno = grpAnno + "</moose:GroupAnnotation>"
                group.setAnnotation(grpAnno)

                for values in value:
                    member = group.createMember()
                    member.setIdRef(values)
        
        consistencyMessages = ""
        SBMLok = validateModel(sbmlDoc)
        if (SBMLok):
            if filepath != [r" ", r"\/", r"/"]:
                writeTofile = filepath + "/" + filename + '.xml'
            else:
                writeTofile = filename+'.xml'
            #writeTofile = filepath + "/" + filename + '.xml'
            writeSBMLToFile(sbmlDoc, writeTofile)
            return True, consistencyMessages, writeTofile
        
        else:
            #cerr << "Errors encountered " << endl
            consistencyMessages = "Errors encountered"
            return -1, consistencyMessages
    else:
        if compterrors:
            return False, compterrors
        else:
            return False,"Atleast one compartment should exist to write SBML"

def writeChannel(modelpath, cremodel_, sceneitems,groupInfo):
    for chan in moose.wildcardFind(modelpath + '/##[0][ISA=ConcChan]'):
        chanannoexist = False
        chanGpnCorCol = " "
        cleanChanname = convertSpecialChar(chan.name)
        compt = ""
        notesE = ""
        groupName = moose.element("/")

        if moose.exists(chan.path + '/info'):
            Anno = moose.Annotator(chan.path + '/info')
            notesE = Anno.notes
            element = moose.element(chan)
            ele = getGroupinfo(element)
            ele = findGroup_compt(element)
            chanAnno = " "
            if ele.className == "Neutral" or sceneitems or Anno.x or Anno.y:
                    chanannoexist = True
            if chanannoexist:
                chanAnno = "<moose:ModelAnnotation>\n"
                if ele.className == "Neutral":
                    groupName = ele
                if sceneitems:
                    #Saved from GUI, then scene co-ordinates are passed
                    chanGpnCorCol = chanGpnCorCol + "<moose:xCord>" + \
                            str(sceneitems[chan]['x']) + "</moose:xCord>\n" + \
                            "<moose:yCord>" + \
                            str(sceneitems[chan]['y'])+ "</moose:yCord>\n"
                else:
                    #Saved from cmdline,genesis coordinates are kept as its
                    # SBML, cspace, python, then auto-coordinates are done
                    #and coordinates are updated in moose Annotation field
                    chanGpnCorCol = chanGpnCorCol + "<moose:xCord>" + \
                            str(Anno.x) + "</moose:xCord>\n" + \
                            "<moose:yCord>" + \
                            str(Anno.y)+ "</moose:yCord>\n"
                chanGpnCorCol = chanGpnCorCol+"<moose:Permeability>"+str(chan.permeability)+"</moose:Permeability>\n"
        chanSub = chan.neighbors["in"]
        chanPrd = chan.neighbors["out"]
        if (len(chanSub) != 0 and len(chanPrd) != 0):
            chanCompt = findCompartment(chan)
            if not isinstance(moose.element(chanCompt), moose.ChemCompt):
                return -2
            else:
                compt = chanCompt.name + "_" + \
                    str(chanCompt.getId().value) + "_" + \
                    str(chanCompt.getDataIndex()) + "_"
  
            channel = cremodel_.createReaction()
            if notesE != "":
                cleanNotesE = convertNotesSpecialChar(notesE)
                notesStringE = "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n \t \t" + \
                    cleanNotesE + "\n\t </body>"
                channel.setNotes(notesStringE)

            chansetId = str(idBeginWith(cleanChanname +
                                         "_" +
                                         str(chan.getId().value) +
                                         "_" +
                                         str(chan.getDataIndex()) +
                                         "_"))
            channel.setId(chansetId)
            
            if groupName != moose.element('/'):
                if groupName not in groupInfo:
                    groupInfo[groupName]=[chansetId]
                else:
                    groupInfo[groupName].append(chansetId)

            channel.setName(str(idBeginWith(convertSpecialCharshot(chan.name))))
            channel.setReversible(True)
            channel.setFast(False)        
            if chanannoexist:
                canAnno = chanAnno + chanGpnCorCol
                chanAnno = "<moose:ConcChannel>\n" + \
                    chanGpnCorCol + "</moose:ConcChannel>"
                channel.setAnnotation(chanAnno)
            noofSub, sRateLawS = getSubprd(cremodel_, False, "sub", chanSub)
            # Modifier
            chanMod = chan.neighbors["setNumChan"]
            noofMod, sRateLawM = getSubprd(cremodel_, False, "enz", chanMod)
            
            noofPrd, sRateLawP = getSubprd(cremodel_, False, "prd", chanPrd)
            
            kl = channel.createKineticLaw()
            
            fRate_law = compt + " * ( Permeability) * " + sRateLawM + " * (" + sRateLawS+ " - " + sRateLawP  +")"
            kl.setFormula(fRate_law)
            kl.setNotes(
                "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t" +
                fRate_law +
                "\n \t </body>")
            
            channelUnit = permeablUnit(cremodel_)
            printParameters(kl, "Permeability", chan.permeability, channelUnit)    
def writeEnz(modelpath, cremodel_, sceneitems,groupInfo):
    for enz in moose.wildcardFind(modelpath + '/##[0][ISA=EnzBase]'):
        enzannoexist = False
        enzGpnCorCol = " "
        cleanEnzname = convertSpecialChar(enz.name)
        enzSubt = ()
        compt = ""
        notesE = ""
        groupName = moose.element("/")

        if moose.exists(enz.path + '/info'):
            groupName = moose.element("/")
            Anno = moose.Annotator(enz.path + '/info')
            notesE = Anno.notes
            element = moose.element(enz)
            ele = getGroupinfo(element)
            ele = findGroup_compt(element)
            if ele.className == "Neutral" or sceneitems or Anno.x or Anno.y:
                    enzannoexist = True
            if enzannoexist:
                enzAnno = "<moose:ModelAnnotation>\n"
                if ele.className == "Neutral":
                    groupName = ele
                    #enzGpnCorCol =  "<moose:Group>" + ele.name + "</moose:Group>\n"
                    # if ele.name not in groupInfo:
                    #         groupInfo[ele.name]=[setId]
                    #     else:
                    #         groupInfo[ele.name].append(setId)
                if sceneitems:
                    #Saved from GUI, then scene co-ordinates are passed
                    enzGpnCorCol = enzGpnCorCol + "<moose:xCord>" + \
                            str(sceneitems[enz]['x']) + "</moose:xCord>\n" + \
                            "<moose:yCord>" + \
                            str(sceneitems[enz]['y'])+ "</moose:yCord>\n"
                else:
                    #Saved from cmdline,genesis coordinates are kept as its
                    # SBML, cspace, python, then auto-coordinates are done
                    #and coordinates are updated in moose Annotation field
                    enzGpnCorCol = enzGpnCorCol + "<moose:xCord>" + \
                            str(Anno.x) + "</moose:xCord>\n" + \
                            "<moose:yCord>" + \
                            str(Anno.y)+ "</moose:yCord>\n"
                if Anno.color:
                    enzGpnCorCol = enzGpnCorCol + "<moose:bgColor>" + Anno.color + "</moose:bgColor>\n"
                if Anno.textColor:
                    enzGpnCorCol = enzGpnCorCol + "<moose:textColor>" + \
                        Anno.textColor + "</moose:textColor>\n"
        if (enz.className == "Enz" or enz.className == "ZombieEnz"):
            # Enz cplx is written into 2 reaction S+E-> SE*, SE* -> E+P
            foundEnzymeComplex = False
            comptVec = findCompartment(moose.element(enz))
            if not isinstance(moose.element(comptVec), moose.ChemCompt):
                return -2
            else:
                compt = comptVec.name + "_" + \
                    str(comptVec.getId().value) + "_" + \
                    str(comptVec.getDataIndex()) + "_"
            #Writting out S+E -> SE*
            enzsetId = str(idBeginWith(cleanEnzname +
                                         "_" + str(enz.getId().value) +
                                         "_" + str(enz.getDataIndex()) +
                                         "_" + "Complex_formation_"))
            #Finding Enzyme parent (E), each enzyme should just have one parent, multiple parent not right!
            secplxerror = ""
            enzSubt = ()
            enzOut = enz.neighbors["enzOut"]
            if not enzOut:
                secplxerror = "enzyme parent missing "
            else:
                enzAnno = "<moose:EnzymaticReaction>\n"
                listofname(enzOut, True)
                enzSubt = enzOut
                if len(nameList_) != 1:
                    secplxerror = secplxerror +" multiple enzyme parent present"
                else:
                    for i in range(0, len(nameList_)):
                        enzAnno = enzAnno + "<moose:enzyme>" + \
                            (str(idBeginWith(convertSpecialChar(
                                nameList_[i])))) + "</moose:enzyme>\n"
                    #Finding Substrate, (S)
                    enzSub = enz.neighbors["sub"]
                    if not enzSub:
                        secplxerror = secplxerror + " substrate missing"
                    else:
                        listofname(enzSub, True)
                        enzSubt += enzSub
                        for i in range(0, len(nameList_)):
                            enzAnno = enzAnno + "<moose:substrates>" + \
                            nameList_[i] + "</moose:substrates>\n"

                        #Finding product, which in this case the cplx (SE*)
                        enzPrd = enz.neighbors["cplxDest"]
                        noofPrd = len(enzPrd)
                        if not enzPrd:
                            secplxerror = secplxerror + " enzymecplx missing which act as product "                            
                        else:
                            listofname(enzPrd, True)
                            for i in range(0, len(nameList_)):
                                enzAnno = enzAnno + "<moose:product>" + \
                                    nameList_[i] + "</moose:product>\n"
                            foundEnzymeComplex = True
            if foundEnzymeComplex:
                # Only if S+E->SE* found, reaction is created
                enzyme = cremodel_.createReaction()
                if notesE != "":
                    cleanNotesE = convertNotesSpecialChar(notesE)
                    notesStringE = "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n \t \t" + \
                                    cleanNotesE + "\n\t </body>"
                    enzyme.setNotes(notesStringE)
                
                enzyme.setId(enzsetId)
                enzyme.setName(str(idBeginWith(convertSpecialCharshot(enz.name))))
                enzyme.setFast(False)
                enzyme.setReversible(True)
                k1 = enz.concK1
                k2 = enz.k2
                k3 = enz.k3
                
                enzAnno = enzAnno + "<moose:groupName>" + cleanEnzname + "_" + \
                str(enz.getId().value) + "_" + \
                str(enz.getDataIndex()) + "_" + "</moose:groupName>\n"
                enzAnno = enzAnno + "<moose:stage>1</moose:stage>\n"
                if enzannoexist:
                    enzAnno = enzAnno + enzGpnCorCol
                enzAnno = enzAnno + "</moose:EnzymaticReaction>"
                enzyme.setAnnotation(enzAnno)
                if enzSubt:
                    rate_law = "k1"
                    noofSub, sRateLaw = getSubprd(cremodel_, True, "sub", enzSubt)
                    rate_law = compt + " * ( " + rate_law + " * " + sRateLaw
                if enzPrd:
                    noofPrd, sRateLaw = getSubprd(cremodel_, True, "prd", enzPrd)
                    rate_law = rate_law + " - " + " k2 " + ' * ' + sRateLaw +" )"
                kl = enzyme.createKineticLaw()
                kl.setFormula(rate_law)
                kl.setNotes("<body xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t" + \
                            rate_law + "\n \t </body>")
                unit = parmUnit(noofSub - 1, cremodel_)
                printParameters(kl, "k1", k1, unit)
                punit = parmUnit(noofPrd - 1, cremodel_)
                printParameters(kl, "k2", k2, punit)
                if groupName != moose.element('/'):
                    if groupName not in groupInfo:
                        #groupInfo[groupName]=[enzsetId]
                        groupInfo[groupName]=[nameList_[0]]
                    else:
                        #groupInfo[groupName].append(enzsetId)
                        groupInfo[groupName].append(nameList_[0])
            else:
                if secplxerror:
                    print ("\'"+enz.parent.name+ "/"+enz.name+"\' this enzyme is not written to file because,"+ secplxerror)
            
            #Here SE* -> E+ P
            foundEnzymeEP = False
            enzsetIdP = str(idBeginWith(cleanEnzname +
                                        "_" + str(enz.getId().value) +
                                        "_" + str(enz.getDataIndex()) +
                                        "_" + "Product_formation_"))
            cplxeperror = ""
            enzAnno2 = ""
            #enzSubt = ""
            enzOut = enz.neighbors["enzOut"]
            if not enzOut:
                cplxepeerror = "enzyme parent missing "
            else:
                enzAnno2 = "<moose:EnzymaticReaction>\n"
                listofname(enzOut, True)
                #enzSubt = enzOut
                if len(nameList_) != 1:
                    cplxeperror = cplxeperror +" multiple enzyme parent present"
                else:
                    # for i in range(0, len(nameList_)):
                    #     enzEnz = "<moose:enzyme>" + \
                    #             (str(idBeginWith(convertSpecialChar(
                    #             nameList_[i])))) + "</moose:enzyme>\n"
                    #Finding Substrate, which is (SE*)
                    enzSub = enz.neighbors["cplxDest"]
                    noofSub = len(enzSub)
                    listofname(enzSub, True)
                    if not enzSub:
                        cplxeperror = cplxeperror +"complex missing which act as substrate "
                    else:
                        for i in range(0, len(nameList_)):
                            enzAnno2 =enzAnno2 +"<moose:complex>" + \
                                    nameList_[i] + "</moose:complex>\n"
                        listofname(enzOut, True)
                        for i in range(0, len(nameList_)):
                            enzAnno2 = enzAnno2 +"<moose:enzyme>" + \
                                (str(idBeginWith(convertSpecialChar(
                                nameList_[i])))) + "</moose:enzyme>\n"

                        enzPrd = enz.neighbors["prd"]
                        noofPrd = len(enzPrd)
                        if not enzPrd:
                            cplxeperror = cplxeperror + "product missing "
                        else:
                            listofname(enzPrd,True)
                            for i in range(0, len(nameList_)):
                                enzAnno2 = enzAnno2 + "<moose:product>" + \
                                            nameList_[i] + "</moose:product>\n"
                        enzAnno2 += "<moose:groupName>" + cleanEnzname + "_" + \
                            str(enz.getId().value) + "_" + \
                            str(enz.getDataIndex()) + "_" + "</moose:groupName>\n"
                        enzAnno2 += "<moose:stage>2</moose:stage> \n"
                        if enzannoexist:
                            enzAnno2 = enzAnno2 + enzGpnCorCol
                        enzAnno2 += "</moose:EnzymaticReaction>"

                        foundEnzymeEP = True
            if foundEnzymeEP:
                enzyme = cremodel_.createReaction()
                enzyme.setId(enzsetIdP)
                enzyme.setName(str(idBeginWith(convertSpecialCharshot(enz.name))))
                enzyme.setFast(False)
                enzyme.setReversible(False)
                enzyme.setAnnotation(enzAnno2)
                noofSub, sRateLaw = getSubprd(cremodel_, True, "sub", enzSub)
                enzprdt = ()
                enzPrdt = enzPrd+enzOut
                noofprd, sRateLaw2 = getSubprd(cremodel_, True, "prd", enzPrdt)
                enzrate_law = compt + " * k3" + '*' + sRateLaw
                kl = enzyme.createKineticLaw()
                kl.setFormula(enzrate_law)
                kl.setNotes(
                        "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t" +
                        enzrate_law +
                        "\n \t </body>")
                unit = parmUnit(noofSub - 1, cremodel_)
                printParameters(kl, "k3", k3, unit)
                if groupName != moose.element('/'):
                    if groupName not in groupInfo:
                        #groupInfo[groupName]=[nameList_[0]]
                        pass
                    else:
                        #groupInfo[groupName].append(nameList_[0])
                        pass
            else:
                print (cplxeperror)
        elif(enz.className == "MMenz" or enz.className == "ZombieMMenz"):

            enzSub = enz.neighbors["sub"]
            enzPrd = enz.neighbors["prd"]
            if (len(enzSub) != 0 and len(enzPrd) != 0):
                enzCompt = findCompartment(enz)
                if not isinstance(moose.element(enzCompt), moose.ChemCompt):
                    return -2
                else:
                    compt = enzCompt.name + "_" + \
                        str(enzCompt.getId().value) + "_" + \
                        str(enzCompt.getDataIndex()) + "_"
                enzyme = cremodel_.createReaction()
                enzAnno = " "
                if notesE != "":
                    cleanNotesE = convertNotesSpecialChar(notesE)
                    notesStringE = "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n \t \t" + \
                        cleanNotesE + "\n\t </body>"
                    enzyme.setNotes(notesStringE)
                mmenzsetId = str(idBeginWith(cleanEnzname +
                                             "_" +
                                             str(enz.getId().value) +
                                             "_" +
                                             str(enz.getDataIndex()) +
                                             "_"))
                enzyme.setId(mmenzsetId)
                if groupName != moose.element('/'):
                    if groupName not in groupInfo:
                        groupInfo[groupName]=[mmenzsetId]
                    else:
                        groupInfo[groupName].append(mmenzsetId)
                enzyme.setName(str(idBeginWith(convertSpecialCharshot(enz.name))))
                #enzyme.setName(cleanEnzname)
                enzyme.setFast(False)
                enzyme.setReversible(True)
                if enzannoexist:
                    enzAnno = enzAnno + enzGpnCorCol
                    enzAnno = "<moose:EnzymaticReaction>\n" + \
                        enzGpnCorCol + "</moose:EnzymaticReaction>"
                    enzyme.setAnnotation(enzAnno)
                Km = enz.Km
                kcat = enz.kcat
                enzSub = enz.neighbors["sub"]
                noofSub, sRateLawS = getSubprd(cremodel_, False, "sub", enzSub)
                #sRate_law << rate_law.str();
                # Modifier
                enzMod = enz.neighbors["enzDest"]
                noofMod, sRateLawM = getSubprd(cremodel_, False, "enz", enzMod)
                enzPrd = enz.neighbors["prd"]
                noofPrd, sRateLawP = getSubprd(cremodel_, False, "prd", enzPrd)
                kl = enzyme.createKineticLaw()
                #rate_law = clean_name + "^" + str(count)
                fRate_law = compt + " * ( kcat * " + sRateLawS + " * " + sRateLawM + "/(Km"
                
                if len(enzSub) > 1:
                    fRate_law = fRate_law +"^" +str(len(enzSub))  
                    print("enzyme ",enzyme.name, "number of substrate is greater than 1, kinetics Law Km is written to the power of substrate assumed that km value is factored")
                fRate_law = fRate_law +" + " + sRateLawS + "))"

                kl.setFormula(fRate_law)
                kl.setNotes(
                    "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t" +
                    fRate_law +
                    "\n \t </body>")
                KmUnit(cremodel_)
                printParameters(kl, "Km", Km, "mmole_per_litre")
                kcatUnit = parmUnit(0, cremodel_)
                printParameters(kl, "kcat", kcat, kcatUnit)


def printParameters(kl, k, kvalue, unit):
    para = kl.createParameter()
    para.setId(str(idBeginWith(k)))
    para.setValue(kvalue)
    para.setUnits(unit)

def permeablUnit(cremodel_):
    unit_stream = "litre_per_mmole_per_second"
    lud = cremodel_.getListOfUnitDefinitions()
    flag = False
    for i in range(0, len(lud)):
        ud = lud.get(i)
        if (ud.getId() == unit_stream):
            flag = True
            break
    if (not flag):
        unitdef = cremodel_.createUnitDefinition()
        unitdef.setId(unit_stream)
        
        unit = unitdef.createUnit()
        unit.setKind(UNIT_KIND_LITRE)
        unit.setExponent(1)
        unit.setMultiplier(1)
        unit.setScale(0)

        unit = unitdef.createUnit()
        unit.setKind(UNIT_KIND_MOLE)
        unit.setExponent(-1)
        unit.setMultiplier(1)
        unit.setScale(-3)
        
        unit = unitdef.createUnit()
        unit.setKind(UNIT_KIND_SECOND)
        unit.setExponent(-1)
        unit.setMultiplier(1)
        unit.setScale(0)
    return unit_stream

def KmUnit(cremodel_):
    unit_stream = "mmole_per_litre"
    lud = cremodel_.getListOfUnitDefinitions()
    flag = False
    for i in range(0, len(lud)):
        ud = lud.get(i)
        if (ud.getId() == unit_stream):
            flag = True
            break
    if (not flag):
        unitdef = cremodel_.createUnitDefinition()
        unitdef.setId(unit_stream)
        unit = unitdef.createUnit()
        unit.setKind(UNIT_KIND_LITRE)
        unit.setExponent(-1)
        unit.setMultiplier(1)
        unit.setScale(0)
        unit = unitdef.createUnit()
        unit.setKind(UNIT_KIND_MOLE)
        unit.setExponent(1)
        unit.setMultiplier(1)
        unit.setScale(-3)
    return unit_stream

def parmUnit(rct_order, cremodel_):
    order = rct_order
    if order == 0:
        unit_stream = "per_second"
    elif order == 1:
        unit_stream = "litre_per_mmole_per_second"
    elif order == 2:
        unit_stream = "sq_litre_per_mmole_sq_per_second"
    else:
        unit_stream = "litre_per_mmole_" + str(rct_order) + "_per_second"

    lud = cremodel_.getListOfUnitDefinitions()
    flag = False
    for i in range(0, len(lud)):
        ud = lud.get(i)
        if (ud.getId() == unit_stream):
            flag = True
            break
    if (not flag):
        unitdef = cremodel_.createUnitDefinition()
        unitdef.setId(unit_stream)
        # Create individual unit objects that will be put inside the
        # UnitDefinition .
        if order != 0:
            unit = unitdef.createUnit()
            unit.setKind(UNIT_KIND_LITRE)
            unit.setExponent(order)
            unit.setMultiplier(1)
            unit.setScale(0)
            unit = unitdef.createUnit()
            unit.setKind(UNIT_KIND_MOLE)
            unit.setExponent(-order)
            unit.setMultiplier(1)
            unit.setScale(-3)

        unit = unitdef.createUnit()
        unit.setKind(UNIT_KIND_SECOND)
        unit.setExponent(-1)
        unit.setMultiplier(1)
        unit.setScale(0)
    return unit_stream

def Counter(items):
    return dict((i, items.count(i)) for i in items)

def getSubprd(cremodel_, mobjEnz, type, neighborslist):
    
    if type == "sub":
        reacSub = neighborslist
        reacSubCou = Counter(reacSub)

        # print " reacSubCou ",reacSubCou,"()",len(reacSubCou)
        noofSub = len(reacSubCou)
        rate_law = " "
        if reacSub:
            rate_law = processRateLaw(
                reacSubCou, cremodel_, noofSub, "sub", mobjEnz)
            return len(reacSub), rate_law
        else:
            return 0, rate_law
    elif type == "prd":
        reacPrd = neighborslist
        reacPrdCou = Counter(reacPrd)
        noofPrd = len(reacPrdCou)
        rate_law = " "
        if reacPrd:
            rate_law = processRateLaw(
                reacPrdCou, cremodel_, noofPrd, "prd", mobjEnz)
            return len(reacPrd), rate_law
    elif type == "enz"  or type == "chan":
        enzModifier = neighborslist
        enzModCou = Counter(enzModifier)
        noofMod = len(enzModCou)
        rate_law = " "
        if enzModifier:
            rate_law = processRateLaw(
                enzModCou, cremodel_, noofMod, "Modifier", mobjEnz)
            return len(enzModifier), rate_law


def processRateLaw(objectCount, cremodel, noofObj, type, mobjEnz):
    rate_law = ""
    nameList_[:] = []
    for value, count in objectCount.items():
        value = moose.element(value)
        '''
        if re.search("_xfer_",value.name):
            modelRoot = value.path[0:value.path.index('/',1)]
            xrefPool = value.name[:value.name.index("_xfer_")]
            xrefCompt = value.name[value.name.index("_xfer_") + len("_xfer_"):]
            orgCompt = moose.wildcardFind(modelRoot+'/##[FIELD(name)='+xrefCompt+']')[0]
            orgPool = moose.wildcardFind(orgCompt.path+'/##[FIELD(name)='+xrefPool+']')[0]
            value = orgPool
        '''
        nameIndex = value.name + "_" + \
            str(value.getId().value) + "_" + str(value.getDataIndex()) + "_"
        clean_name = (str(idBeginWith(convertSpecialChar(nameIndex))))
        if mobjEnz == True:
            nameList_.append(clean_name)

        if type == "sub":
            sbmlRef = cremodel.createReactant()
        elif type == "prd":
            sbmlRef = cremodel.createProduct()
        elif type == "Modifier":
            sbmlRef = cremodel.createModifier()
            sbmlRef.setSpecies(clean_name)

        if type == "sub" or type == "prd":
            sbmlRef.setSpecies(clean_name)
            sbmlRef.setStoichiometry(count)
            if clean_name in spe_constTrue:
                sbmlRef.setConstant(True)
            else:
                sbmlRef.setConstant(False)
        if (count == 1):
            if rate_law == "":
                rate_law = clean_name
            else:
                rate_law = rate_law + "*" + clean_name
        else:
            if rate_law == "":
                rate_law = clean_name + "^" + str(count)
            else:
                rate_law = rate_law + "*" + clean_name + "^" + str(count)
    return(rate_law)


def listofname(reacSub, mobjEnz):
    objectCount = Counter(reacSub)
    nameList_[:] = []
    for value, count in objectCount.items():
        value = moose.element(value)
        nameIndex = value.name + "_" + \
            str(value.getId().value) + "_" + str(value.getDataIndex()) + "_"
        clean_name = convertSpecialChar(nameIndex)
        if mobjEnz == True:
            nameList_.append(clean_name)


def writeReac(modelpath, cremodel_, sceneitems,reacGroup):
    for reac in moose.wildcardFind(modelpath + '/##[0][ISA=ReacBase]'):
        reacSub = reac.neighbors["sub"]
        reacPrd = reac.neighbors["prd"]
        if (len(reacSub) != 0 and len(reacPrd) != 0):

            reaction = cremodel_.createReaction()
            reacannoexist = False
            reacGpname = " "
            cleanReacname = convertSpecialChar(reac.name)
            setId = str(idBeginWith(cleanReacname +
                                           "_" +
                                           str(reac.getId().value) +
                                           "_" +
                                           str(reac.getDataIndex()) +
                                           "_"))
            reaction.setId(setId)
            reaction.setName(str(idBeginWith(convertSpecialCharshot(reac.name))))
            #reaction.setName(cleanReacname)
            #Kf = reac.numKf
            #Kb = reac.numKb
            Kf = reac.Kf
            Kb = reac.Kb
            if Kb == 0.0:
                reaction.setReversible(False)
            else:
                reaction.setReversible(True)

            reaction.setFast(False)
            if moose.exists(reac.path + '/info'):
                Anno = moose.Annotator(reac.path + '/info')
                if Anno.notes != "":
                    cleanNotesR = convertNotesSpecialChar(Anno.notes)
                    notesStringR = "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n \t \t" + \
                        cleanNotesR + "\n\t </body>"
                    reaction.setNotes(notesStringR)
                element = moose.element(reac)
                ele = getGroupinfo(element)
                if element.className == "Neutral" or sceneitems or Anno.x or Anno.y:
                    reacannoexist = True
                if reacannoexist:
                    reacAnno = "<moose:ModelAnnotation>\n"
                    if ele.className == "Neutral":
                        #reacAnno = reacAnno + "<moose:Group>" + ele.name + "</moose:Group>\n"
                        if ele not in reacGroup:
                            reacGroup[ele]=[setId]
                        else:
                            reacGroup[ele].append(setId)
                    if sceneitems:
                        #Saved from GUI, then scene co-ordinates are passed
                        reacAnno = reacAnno + "<moose:xCord>" + \
                                str(sceneitems[reac]['x']) + "</moose:xCord>\n" + \
                                "<moose:yCord>" + \
                                str(sceneitems[reac]['y'])+ "</moose:yCord>\n"
                    else:
                        #Saved from cmdline,genesis coordinates are kept as its
                        # SBML, cspace, python, then auto-coordinates are done
                        #and coordinates are updated in moose Annotation field
                        reacAnno = reacAnno + "<moose:xCord>" + \
                                str(Anno.x) + "</moose:xCord>\n" + \
                                "<moose:yCord>" + \
                                str(Anno.y)+ "</moose:yCord>\n"
                    if Anno.color:
                        reacAnno = reacAnno + "<moose:bgColor>" + Anno.color + "</moose:bgColor>\n"
                    if Anno.textColor:
                        reacAnno = reacAnno + "<moose:textColor>" + \
                            Anno.textColor + "</moose:textColor>\n"
                    reacAnno = reacAnno + "</moose:ModelAnnotation>"
                    reaction.setAnnotation(reacAnno)

            kl_s, sRL, pRL, compt = "", "", "", ""

            if not reacSub and not reacPrd:
                print(" Reaction ", reac.name, "missing substrate and product, this is not allowed in SBML which will not be written")
            else:
                kfl = reaction.createKineticLaw()
                if reacSub:
                    noofSub, sRateLaw = getSubprd(
                        cremodel_, False, "sub", reacSub)
                    if noofSub:
                        comptVec = findCompartment(moose.element(reacSub[0]))
                        if not isinstance(moose.element(
                                comptVec), moose.ChemCompt):
                            return -2
                        else:
                            compt = comptVec.name + "_" + \
                                str(comptVec.getId().value) + "_" + \
                                str(comptVec.getDataIndex()) + "_"
                        cleanReacname = cleanReacname + "_" + \
                            str(reac.getId().value) + "_" + \
                            str(reac.getDataIndex()) + "_"
                        kfparm = idBeginWith(cleanReacname) + "_" + "Kf"
                        sRL = compt + " * " + \
                            idBeginWith(cleanReacname) + "_Kf * " + sRateLaw
                        unit = parmUnit(noofSub - 1, cremodel_)
                        printParameters(kfl, kfparm, Kf, unit)
                        #kl_s = compt+"(" +sRL
                        kl_s = sRL
                    else:
                        print(reac.name + " has no substrate")
                        return -2
                else:
                    print(" Substrate missing for reaction ", reac.name)

                if reacPrd:
                    noofPrd, pRateLaw = getSubprd(
                        cremodel_, False, "prd", reacPrd)
                    if noofPrd:
                        if Kb:
                            kbparm = idBeginWith(cleanReacname) + "_" + "Kb"
                            pRL = compt + " * " + \
                                idBeginWith(cleanReacname) + \
                                "_Kb * " + pRateLaw
                            unit = parmUnit(noofPrd - 1, cremodel_)
                            printParameters(kfl, kbparm, Kb, unit)
                            #kl_s = kl_s+ "- "+pRL+")"
                            kl_s = kl_s + "-" + pRL
                    else:
                        print(reac.name + " has no product")
                        return -2
                else:
                    print(" Product missing for reaction ", reac.name)
            kfl.setFormula(kl_s)
            kfl.setNotes(
                "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n\t\t" +
                kl_s +
                "\n \t </body>")
            kfl.setFormula(kl_s)

        else:
            print(" Reaction ", reac.name, "missing substrate and product, this is not allowed in SBML which will not be written")


def writeFunc(modelpath, cremodel_):
    funcs = moose.wildcardFind(modelpath + '/##[0][ISA=Function]')
    # if func:
    foundFunc = False
    for func in funcs:
        if func:
            #not neccessary parent is compartment can be group also
            if func.parent.className == "CubeMesh" or func.parent.className == "CyclMesh":
                if len(moose.element(func).neighbors["valueOut"]) > 0:
                    funcEle = moose.element(
                        moose.element(func).neighbors["valueOut"][0])
                    funcEle1 = moose.element(funcEle)
                    fName = idBeginWith(convertSpecialChar(
                    funcEle.name + "_" + str(funcEle.getId().value) + "_" + str(funcEle.getDataIndex()) + "_"))
                    expr = " "
                    expr = str(moose.element(func).expr)
                    if expr:
                        foundFunc = True
                        item = func.path + '/x[0]'
                        sumtot = moose.element(item).neighbors["input"]
                        for i in range(0, len(sumtot)):
                            v = "x" + str(i)
                            if v in expr:
                                z = str(idBeginWith(str(convertSpecialChar(sumtot[i].name + "_" + str(moose.element(
                                    sumtot[i]).getId().value) + "_" + str(moose.element(sumtot[i]).getDataIndex())) + "_")))
                                expr = expr.replace(v, z)
            else:
                foundFunc = True
                fName = idBeginWith(convertSpecialChar(func.parent.name +
                                                       "_" + str(func.parent.getId().value) +
                                                       "_" + str(func.parent.getDataIndex()) +
                                                       "_"))
                item = func.path + '/x[0]'
                sumtot = moose.element(item).neighbors["input"]
                expr = moose.element(func).expr
                for i in range(0, len(sumtot)):
                    v = "x" + str(i)
                    if v in expr:
                        z = str(idBeginWith(str(convertSpecialChar(sumtot[i].name + "_" + str(moose.element(
                            sumtot[i]).getId().value) + "_" + str(moose.element(sumtot[i]).getDataIndex())) + "_")))
                        expr = expr.replace(v, z)
            if foundFunc:
                rule = cremodel_.createAssignmentRule()
                rule.setVariable(fName)
                rule.setFormula(expr)

def convertNotesSpecialChar(str1):
    d = {"&": "_and", "<": "_lessthan_", ">": "_greaterthan_", "BEL": "&#176"}
    for i, j in d.items():
        str1 = str1.replace(i, j)
    # stripping \t \n \r and space from begining and end of string
    str1 = str1.strip(' \t\n\r')
    return str1

def getGroupinfo(element):
    #   Note: At this time I am assuming that if group exist (incase of Genesis)
    #   1. for 'pool' its between compartment and pool, /modelpath/Compartment/Group/pool
    #   2. for 'enzComplx' in case of ExpilcityEnz its would be, /modelpath/Compartment/Group/Pool/Enz/Pool_cplx
    #   For these cases I have checked, but subgroup may exist then this bit of code need to cleanup further down
    #   if /modelpath/Compartment/Group/Group1/Pool, then I check and get Group1
    #   And /modelpath is also a NeutralObject,I stop till I find Compartment

    while not mooseIsInstance(element, ["Neutral", "CubeMesh", "CylMesh","EndoMesh","NeuroMesh"]):
        element = element.parent
    return element


def idBeginWith(name):
    changedName = name
    if name[0].isdigit():
        changedName = "_" + name
    return changedName

def findGroup_compt(melement):
    while not (mooseIsInstance(melement, ["Neutral","CubeMesh", "CylMesh","EndoMesh","NeuroMesh"])):
        melement = melement.parent
    return melement

def convertSpecialCharshot(str1):
    d = { "BEL"     : "&#176", 
            "'"     : "_prime_",
            "\\"    : "_slash_",
            "/"     : "_slash_", 
            "["     : "_sbo_", 
            "]"     : "_sbc_",
            ": "    : "_" , 
            " "     : "_" }
    for i, j in d.items():
        str1 = str1.replace(i, j)
    return str1

def convertSpecialChar(str1):
    d = {"&": "_and", "<": "_lessthan_", ">": "_greaterthan_", "BEL": "&#176", "-": "_minus_", "'": "_prime_",
         "+": "_plus_", "*": "_star_", "/": "_slash_", "(": "_bo_", ")": "_bc_",
         "[": "_sbo_", "]": "_sbc_", ".": "_dot_", " ": "_"
         }
    for i, j in d.items():
        str1 = str1.replace(i, j)
    return str1


def writeSpecies(modelpath, cremodel_, sbmlDoc, sceneitems,speGroup):
    # getting all the species
    for spe in moose.wildcardFind(modelpath + '/##[0][ISA=PoolBase]'):
        #Eliminating xfer molecules writting
        if not re.search("_xfer_",spe.name):
            
            sName = convertSpecialChar(spe.name)
            comptVec = findCompartment(spe)
            speciannoexist = False
            
            if not isinstance(moose.element(comptVec), moose.ChemCompt):
                return -2
            else:
                compt = comptVec.name + "_" + \
                    str(comptVec.getId().value) + "_" + \
                    str(comptVec.getDataIndex()) + "_"
                s1 = cremodel_.createSpecies()
                spename = sName + "_" + \
                    str(spe.getId().value) + "_" + str(spe.getDataIndex()) + "_"
                spename = str(idBeginWith(spename))
                s1.setId(spename)

                if spename.find(
                        "cplx") != -1 and isinstance(moose.element(spe.parent), moose.EnzBase):
                    enz = spe.parent
                    if not moose.exists(spe.path+'/info'):
                        cplxinfo = moose.Annotator(spe.path+'/info')
                        enzpath = moose.element(spe.parent.path+'/info')
                        
                        cplxinfo.x = moose.element(moose.element(spe.parent.path+'/info').x)
                        
                        cplxinfo.y = int((moose.element(spe.parent.path+'/info').y))+10
                 
                    if (moose.element(enz.parent), moose.PoolBase):
                        # print " found a cplx name ",spe.parent,
                        # moose.element(spe.parent).parent
                        enzname = enz.name
                        enzPool = (enz.parent).name
                        sName = convertSpecialChar(
                            enzPool + "_" + enzname + "_" + sName)

                #s1.setName(sName)
                s1.setName(str(idBeginWith(convertSpecialCharshot(spe.name))))
                # s1.setInitialAmount(spe.nInit)
                s1.setInitialConcentration(spe.concInit)
                s1.setCompartment(compt)
                #  Setting BoundaryCondition and constant as per this rule for BufPool
                #  -constanst  -boundaryCondition  -has assignment/rate Rule  -can be part of sub/prd
                #   false           true              yes                       yes
                #   true            true               no                       yes
                if spe.className == "BufPool" or spe.className == "ZombieBufPool":
                    # BoundaryCondition is made for buff pool
                    s1.setBoundaryCondition(True)

                    if moose.exists(spe.path + '/func'):
                        bpf = moose.element(spe.path)
                        for fp in bpf.children:
                            if fp.className == "Function" or fp.className == "ZombieFunction":
                                if len(moose.element(
                                        fp.path + '/x').neighbors["input"]) > 0:
                                    s1.setConstant(False)
                                else:
                                    # if function exist but sumtotal object doesn't
                                    # exist
                                    spe_constTrue.append(spename)
                                    s1.setConstant(True)
                    else:
                        spe_constTrue.append(spename)
                        s1.setConstant(True)
                else:
                    # if not bufpool then Pool, then
                    s1.setBoundaryCondition(False)
                    s1.setConstant(False)
                s1.setUnits("substance")
                s1.setHasOnlySubstanceUnits(False)

                if moose.exists(spe.path + '/info'):
                    Anno = moose.Annotator(spe.path + '/info')
                    if Anno.notes != "":
                        cleanNotesS = convertNotesSpecialChar(Anno.notes)
                        notesStringS = "<body xmlns=\"http://www.w3.org/1999/xhtml\">\n \t \t" + \
                            cleanNotesS + "\n\t </body>"
                        s1.setNotes(notesStringS)


                    element = moose.element(spe)
                    ele = getGroupinfo(element)
                    
                    speciAnno = "<moose:ModelAnnotation>\n"
                    if ele.className == "Neutral":
                        #speciAnno = speciAnno + "<moose:Group>" + ele.name + "</moose:Group>\n"
                        if ele not in speGroup:
                            speGroup[ele]=[spename]
                        else:
                            speGroup[ele].append(spename)


                    if sceneitems:
                        #Saved from GUI, then scene co-ordinates are passed
                        speciAnno = speciAnno + "<moose:xCord>" + \
                                str(sceneitems[spe]['x']) + "</moose:xCord>\n" + \
                                "<moose:yCord>" + \
                                str(sceneitems[spe]['y'])+ "</moose:yCord>\n"
                    else:
                        #Saved from cmdline,genesis coordinates are kept as its
                        # SBML, cspace, python, then auto-coordinates are done
                        #and coordinates are updated in moose Annotation field
                        speciAnno = speciAnno + "<moose:xCord>" + \
                                str(Anno.x) + "</moose:xCord>\n" + \
                                "<moose:yCord>" + \
                                str(Anno.y)+ "</moose:yCord>\n"
                    if Anno.color:
                        speciAnno = speciAnno + "<moose:bgColor>" + Anno.color + "</moose:bgColor>\n"
                    if Anno.textColor:
                        speciAnno = speciAnno + "<moose:textColor>" + \
                            Anno.textColor + "</moose:textColor>\n"
                    
                    speciAnno = speciAnno + "<moose:diffConstant>" + str(spe.diffConst) + "</moose:diffConstant>\n"
                    speciAnno = speciAnno + "<moose:motorConstant>" + str(spe.motorConst)+ "</moose:motorConstant>\n" 
                    speciAnno = speciAnno + "</moose:ModelAnnotation>"
                    s1.setAnnotation(speciAnno)
                else:
                    #E.g cplx doesn't have info field but findsim layout expecting diffConstant and motorConstant.
                    speciAnno = "<moose:ModelAnnotation>\n"
                    speciAnno = speciAnno + "<moose:diffConstant>" + str(0.0) + "</moose:diffConstant>\n"
                    speciAnno = speciAnno + "<moose:motorConstant>" + str(0.0)+ "</moose:motorConstant>\n" 
                    speciAnno = speciAnno + "</moose:ModelAnnotation>"
                    s1.setAnnotation(speciAnno)
    return True


def writeCompt(modelpath, cremodel_):
    # getting all the compartments
    compts = moose.wildcardFind(modelpath + '/##[0][ISA=ChemCompt]')
    groupInfo = {}
    comptID_sbml = {}
    for compt in compts:
        comptAnno = ""
        comptName = convertSpecialChar(compt.name)
        # converting m3 to litre
        createCompt = True
        size = compt.volume * pow(10, 3)
        ndim = compt.numDimensions
        csetId = (str(idBeginWith(comptName +
                                "_" +
                                str(compt.getId().value) +
                                "_" +
                                str(compt.getDataIndex()) +
                                "_")))
        comptID_sbml[compt] = csetId
        if isinstance(compt,moose.EndoMesh):
            if comptID_sbml.get(compt.surround) == None:
                createCompt = False
                return False,groupInfo,"Outer compartment need to be specified for EndoMesh "
                #return " EndoMesh need to outer compartment to be specified "
            else:
                comptAnno = "<moose:CompartmentAnnotation><moose:Mesh>" + \
                                    str(compt.className) + "</moose:Mesh>\n" + \
                                    "<moose:surround>" + \
                                    str(comptID_sbml[compt.surround])+ "</moose:surround>\n" + \
                                    "<moose:isMembraneBound>" + \
                                    str(compt.isMembraneBound)+ "</moose:isMembraneBound>\n" 
                if moose.exists(compt.path+'/info'):
                    if moose.element(compt.path+'/info').notes != "":
                        comptAnno = comptAnno + "<moose:Notes>" \
                        + moose.element(compt.path+'/info').notes + "</moose:Notes>"
                comptAnno = comptAnno+ "</moose:CompartmentAnnotation>"
        elif isinstance (compt,moose.CylMesh) :
            size = (compt.volume/compt.numDiffCompts)*pow(10,3)
            comptAnno = "<moose:CompartmentAnnotation><moose:Mesh>" + \
                                str(compt.className) + "</moose:Mesh>\n" + \
                                "<moose:totLength>" + \
                                str(compt.totLength)+ "</moose:totLength>\n" + \
                                "<moose:diffLength>" + \
                                str(compt.diffLength)+ "</moose:diffLength>\n" + \
                                "<moose:isMembraneBound>" + \
                                str(compt.isMembraneBound)+ "</moose:isMembraneBound>\n"
            if moose.exists(compt.path+'/info'):
                if moose.element(compt.path+'/info').notes != "":
                    comptAnno = comptAnno + "<moose:Notes>" \
                    + moose.element(compt.path+'/info').notes + "</moose:Notes>"
            comptAnno = comptAnno+ "</moose:CompartmentAnnotation>"
        else:
            comptAnno = "<moose:CompartmentAnnotation><moose:Mesh>" + \
                                str(compt.className) + "</moose:Mesh>\n" + \
                                "<moose:isMembraneBound>" + \
                                str(compt.isMembraneBound)+ "</moose:isMembraneBound>\n" 
            if moose.exists(compt.path+'/info'):
                if moose.element(compt.path+'/info').notes != "":
                    comptAnno = comptAnno + "<moose:Notes>" \
                    + moose.element(compt.path+'/info').notes + "</moose:Notes>"
            comptAnno = comptAnno+ "</moose:CompartmentAnnotation>"
        if createCompt:
            c1 = cremodel_.createCompartment()
            c1.setId(csetId)
            c1.setName(comptName)
            c1.setConstant(True)
            c1.setSize(compt.volume*pow(10,3))
            #c1.setSize(size)
            if isinstance(compts,moose.EndoMesh):
                c1.outside = comptID_sbml[compt.surround]
                
            if comptAnno:
                c1.setAnnotation(comptAnno)
            c1.setSpatialDimensions(ndim)
            if ndim == 3:
                c1.setUnits('volume')
            elif ndim == 2:
                c1.setUnits('area')
            elif ndim == 1:
                c1.setUnits('metre')
            
            #For each compartment get groups information along
            for grp in moose.wildcardFind(compt.path+'/##[0][TYPE=Neutral]'):
                grp_cmpt = findGroup_compt(grp.parent)
                try:
                    value = groupInfo[moose.element(grp)]
                except KeyError:
                    # Grp is not present
                    groupInfo[moose.element(grp)] = []
        

    if compts:
        return True,groupInfo,""
    else:
        return False,groupInfo,""
# write Simulation runtime,simdt,plotdt

def writeSimulationAnnotation(modelpath):
    modelAnno = ""
    plots = ""
    if moose.exists(modelpath + '/info'):
        mooseclock = moose.Clock('/clock')
        modelAnno = "<moose:ModelAnnotation>\n"
        modelAnnotation = moose.element(modelpath + '/info')
        modelAnno = modelAnno + "<moose:runTime> " + \
            str(modelAnnotation.runtime) + " </moose:runTime>\n"
        modelAnno = modelAnno + "<moose:solver> " + \
            modelAnnotation.solver + " </moose:solver>\n"
        modelAnno = modelAnno + "<moose:simdt>" + \
            str(mooseclock.dts[12]) + " </moose:simdt>\n"
        modelAnno = modelAnno + "<moose:plotdt> " + \
            str(mooseclock.dts[18]) + " </moose:plotdt>\n"
        plots = ""
        graphs = moose.wildcardFind(modelpath + "/##[0][TYPE=Table2]")
        
        for gphs in range(0, len(graphs)):
            gpath = graphs[gphs].neighbors['requestOut']
            if len(gpath) != 0:
                q = moose.element(gpath[0])
                ori = q.path
                name = convertSpecialChar(q.name)
                graphSpefound = False
                
                while not(isinstance(moose.element(q), moose.CubeMesh) or isinstance(moose.element(q),moose.CylMesh) \
                    or    isinstance(moose.element(q), moose.EndoMesh) or isinstance(moose.element(q),moose.NeuroMesh)):
                    q = q.parent
                    graphSpefound = True
                if graphSpefound:
                    if not plots:
                        plots = ori[ori.find(q.name)-1:len(ori)]
                        #plots = '/' + q.name + '/' + name

                    else:
                        plots = plots + "; "+ori[ori.find(q.name)-1:len(ori)]
                        #plots = plots + "; /" + q.name + '/' + name
                
        if plots != " ":
            modelAnno = modelAnno + "<moose:plots> " + plots + "</moose:plots>\n"
        modelAnno = modelAnno + "</moose:ModelAnnotation>"
        
    return modelAnno

def recalculatecoordinates(modelpath, mObjlist,xcord,ycord):
    positionInfoExist = not(len(np.nonzero(xcord)[0]) == 0 \
                        and len(np.nonzero(ycord)[0]) == 0)
    defaultsceneWidth =  1000
    defaultsceneHeight =  800
    if positionInfoExist:
        #Here all the object has been taken now recalculate and reassign back x and y co-ordinates
        xmin = min(xcord)
        xmax = max(xcord)
        ymin = min(ycord)
        ymax = max(ycord)
        for merts in mObjlist:
            objInfo = merts.path+'/info'
            if moose.exists(objInfo):
                Ix = defaultsceneWidth * ((xyPosition(objInfo,'x')-xmin)/(xmax-xmin))
                Iy = defaultsceneHeight * ((xyPosition(objInfo,'y')-ymin)/(ymax-ymin))
                moose.element(objInfo).x = Ix
                moose.element(objInfo).y = Iy
   
    else:
        srcdesConnection = {}
        setupItem(modelpath,srcdesConnection)
        meshEntry,xmin,xmax,ymin,ymax,positionInfoExist,sceneitems = setupMeshObj(modelpath)
        if not positionInfoExist:

            sceneitems = autoCoordinates(meshEntry,srcdesConnection)
        sceneitems = autoCoordinates(meshEntry,srcdesConnection)

        #print srcdesConnection
        '''
        #meshEntry,xmin,xmax,ymin,ymax,positionInfoExist,sceneitems = setupMeshObj(modelpath)
        #if not positionInfoExist:
            #cmin,cmax,sceneitems = autoCoordinates(meshEntry,srcdesConnection)
            sceneitems = autoCoordinates(meshEntry,srcdesConnection)
	'''        
def writeUnits(cremodel_):
    unitVol = cremodel_.createUnitDefinition()
    unitVol.setId("volume")
    unit = unitVol.createUnit()
    unit.setKind(UNIT_KIND_LITRE)
    unit.setMultiplier(1.0)
    unit.setExponent(1.0)
    unit.setScale(0)

    unitSub = cremodel_.createUnitDefinition()
    unitSub.setId("substance")
    unit = unitSub.createUnit()
    unit.setKind(UNIT_KIND_MOLE)
    unit.setMultiplier(1)
    unit.setExponent(1.0)
    unit.setScale(-3)

    unitLen = cremodel_.createUnitDefinition()
    unitLen.setId("length")
    unit = unitLen.createUnit()
    unit.setKind(UNIT_KIND_METRE)
    unit.setMultiplier(1.0)
    unit.setExponent(1.0)
    unit.setScale(0)

    unitArea = cremodel_.createUnitDefinition()
    unitArea.setId("area")
    unit = unitArea.createUnit()
    unit.setKind(UNIT_KIND_METRE)
    unit.setMultiplier(1.0)
    unit.setExponent(2.0)
    unit.setScale(0)

    unitTime = cremodel_.createUnitDefinition()
    unitTime.setId("time")
    unit = unitTime.createUnit()
    unit.setKind(UNIT_KIND_SECOND)
    unit.setExponent(1)
    unit.setMultiplier(1)
    unit.setScale(0)

if __name__ == "__main__":
    try:
        sys.argv[1]
    except IndexError:
        print("Filename or path not given")
        exit(0)
    else:
        filepath = sys.argv[1]
        if not os.path.exists(filepath):
            print("Filename or path does not exist",filepath)
        else:
            try:
                sys.argv[2]
            except :
                modelpath = filepath[filepath.rfind('/'):filepath.find('.')]
            else:
                modelpath = sys.argv[2]

            moose.loadModel(filepath, modelpath, "gsl")

            written, c, writtentofile = mooseWriteSBML(modelpath, filepath)
            if written:
                print(" File written to ", writtentofile)
            else:
                print(" could not write model to SBML file")

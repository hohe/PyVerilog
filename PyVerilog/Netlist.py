import Module
import PortIn
import PortOut
import PortClk
import ConfigParser
from ordereddict import OrderedDict
import os
import yaml
import pickle
import re
import verilogParse
import myutils
################################################################################
################################################################################
class Netlist:
    """
    This class is a Python datastructure for storing/querying Verilog
    netlists.
    
    The Netlist module is able to read both from Verilog files and special 
    YAML-formatted files. The YAML format is currently much faster. I have 
    a separate Verilog-->YAML converter that I've used to create YAML files up
    until now (based in Perl, booo). The Verilog support in Python is newly
    added.
    
    This example shows how to read and link netlists. It demonstrates both 
    reading from Verilog (n1) and YAML (n2), and then verifies that
    the a few of the netlist properties match.
    
    >>> nl1 = Netlist()
    >>> nl2 = Netlist()
    >>> nl1.readYAML("test/gates.yml")
    >>> nl2.readYAML("test/gates.yml")
    >>> nl1.readVerilog("test/Iface_test.gv")
    >>> nl2.readYAML("test/Iface_test.yml")
    >>> nl1.link("Iface_test")
    >>> nl2.link("Iface_test")
    >>> nl1.topMod
    'Iface_test'
    >>> nl2.topMod
    'Iface_test'
    >>> mod1 = nl1.mods[nl1.topMod]
    >>> mod2 = nl2.mods[nl2.topMod]
    >>> set(mod1.ports.keys()) == set(mod2.ports.keys())
    True
    >>> set(mod1.cells.keys()) == set(mod2.cells.keys())
    True
    >>> set(mod1.nets.keys()) == set(mod2.nets.keys())
    True
    """
    
    mods = property(lambda self: self.__mods)
    yaml = property(lambda self: self.__yaml)
    topMod = property(lambda self: self.__topMod)
    
    def __init__(self):
        self.__mods = dict()
        self.__topMod = None
        self.__yaml = dict()
    
    def link(self, topModule):
        " link the design together"
        if topModule not in self.__mods:
            raise Exception(str("link error, " + topModule + 
                                " has not been defined"))
        
        mod = self.__mods[topModule]
        
        missing = set()
        # check all cells
        for cell in mod.cells:
            if mod.cells[cell].submodname not in self.__mods:
                missing.add(mod.cells[cell].submodname)
        
        if len(missing) > 0:
            raise Exception(str("link error, " +  
                                str(missing) + 
                                " have not been defined"))
        
        for cell in mod.cells:
            submod = self.__mods[mod.cells[cell].submodname]
            mod.cells[cell].linkMod(submod)
            for pin in mod.cells[cell].pins:
                if pin not in submod.ports:
                    raise Exception(str("port " + pin + " not in " 
                                        + submod.name))
                mod.cells[cell].pins[pin].connectPort(submod.ports[pin])
                net =  mod.cells[cell].pins[pin].net
                if submod.ports[pin].direction == "in":
                    net.addFanout(mod.cells[cell].pins[pin])
                else:
                    net.setFanin(mod.cells[cell].pins[pin])
                
        self.__topMod = topModule
    
    def checkDesign(self):
        "verify the design has legal connections (post-linking)"
        
        # make sure input ports ONLY connect to input ports
        
        
        # make sure the output ports ONLY connect to output ports
        
        
        # make sure all connections have 1 and only 1 driver
        
        
        # sanity check all connection widths
        pass
    
    def addModule(self, mod):
        modname = mod.name
        if modname in self.__mods:
            print "Warning: " + modname + " has been multiply defined"
        self.__mods[modname] = mod
    
    def readVerilog(self, verilogFile):
        """ Parse a Gate-level Verilog file using Python"""
        mod = verilogParse.parseFile(verilogFile)
        self.__mods[mod.name] = mod
    
    def writeVerilog(self, vFileName):
        """ Write a gate-level verilog file """
        
        tm = self.mods[ self.topMod ]
        lines = []
        
        # -- ?? -- "busMember":False, "bitIdx":None,   "busName":None    })
        
        # declare the module
        ports = set()
        minBit = {}
        maxBit = {}
        for p in tm.ports.values():
            if p.busMember:
                ports.add( ( p.busName, p.direction ) )
                if p.busName in minBit:
                    l = minBit[ p.busName ]
                    r = maxBit[ p.busName ]
                    assert p.bitIdx != l
                    assert p.bitIdx != r
                    if p.bitIdx < l: minBit[ p.busName ] = p.bitIdx
                    if p.bitIdx > r: maxBit[ p.busName ] = p.bitIdx
                else:
                    minBit[ p.busName ] = p.bitIdx
                    maxBit[ p.busName ] = p.bitIdx
            else:
                ports.add( ( p.name, p.direction ) )
        portsCsv = ', '.join( [ x[0] for x in list( ports ) ] )
        lines.append( 'module %s( %s );' % ( self.topMod, portsCsv ) )
        lines.append( '' )
        
        # declare i/o ports
        for ( portName, dirxn ) in ports:
            if portName in minBit:
                assert minBit[ portName ] == 0
                l = minBit[ portName ]
                r = maxBit[ portName ]
                if   dirxn == 'in':  lines.append( '    input  [ %2d:%2d ] %s;' % ( r, l, portName ))
                elif dirxn == 'out': lines.append( '    output [ %2d:%2d ] %s;' % ( r, l, portName ))
            else:
                if   dirxn == 'in':  lines.append( '    input  %s;' % ( portName ))
                elif dirxn == 'out': lines.append( '    output %s;' % ( portName ))
                else: assert False
        lines.append( '' )
        
        # declare the wires
        minBit = {}
        maxBit = {}
        nets = set()
        for n in tm.nets.values():
              if n.busMember:
                  nets.add( n.busName )
                  if n.busName in minBit:
                      l = minBit[ n.busName ]
                      r = maxBit[ n.busName ]
                      assert int( n.bitIdx ) != l
                      assert int( n.bitIdx ) != r
                      if int( n.bitIdx ) < l: minBit[ n.busName ] = int ( n.bitIdx )
                      if int( n.bitIdx ) > r: maxBit[ n.busName ] = int ( n.bitIdx )
                  else:
                      minBit[ n.busName ] = int( n.bitIdx )
                      maxBit[ n.busName ] = int( n.bitIdx )
              else:
                  nets.add( n.name )
        
        for netName in nets:
            if netName in minBit:
                #assert minBit[ netName ] == 0
                l = minBit[ netName ]
                r = maxBit[ netName ]
                lines.append( '    wire [ %2d:%2d ] %s;' % ( r, l, netName ) )
            else:
                lines.append( '    wire %s;' % ( netName ))
        lines.append( '' )
        
        # instantiate the cells        
        for c in tm.cells.values():
            ports = []
            for p in c.pins.values():
                ports.append( '.%s( %s )' % ( p.name, p.net.name ))
            ports = ', '.join( ports )
            lines.append( '    %s %s( %s );' % ( c.submodname, c.name, ports ))
        lines.append( 'endmodule' )
        VFH = open( vFileName, 'w' )
        for line in lines:
            VFH.write( line + '\n' )
        VFH.close()
    
    def dumpPickle(self, piklFile):
        " Dump self to a pickle file"
        
        FH = open( piklFile, 'w' )
        pickle.dump( self, FH )
        FH.close()
    
    def readYAML(self, yamlFile):
        " Read a YAML config file, build a netlist"
        
        file = open(yamlFile)
        nl = yaml.safe_load(file)
        file.close()
        
        # save the config info in case we need it later
        self.__yaml.update(nl)
        
        for modname in nl.keys():
            mod = Module.Module({"name":modname})
            
            inputs = myutils.cleanget(nl.get(modname), "inputs")
            for name in inputs:
                #todo: add parsing code to determine width msb/lsb here
                width = int(inputs.get(name))
                tuples = self.__makePortTupleList__(name, width)
                for ( name, width, isBusMember, bitIdx, busName ) in tuples:
                    mod.add_port(PortIn.PortIn({ "name":name, "width":width, "module":mod, "busMember":isBusMember, "bitIdx":bitIdx, "busName":busName }))
        
            outputs = myutils.cleanget(nl.get(modname), "outputs")
            for name in outputs:
                #todo: add parsing code to determine width msb/lsb here
                width = int(outputs.get(name))
                tuples = self.__makePortTupleList__(name, width)
                for ( name, width, isBusMember, bitIdx, busName ) in tuples:
                    mod.add_port(PortOut.PortOut({ "name":name, "width":width, "module":mod, "busMember":isBusMember, "bitIdx":bitIdx, "busName":busName } ))
            
            clocks = myutils.cleanget(nl.get(modname), "clocks")
            for name in clocks:
                mod.add_port(PortClk.PortClk({"name":name, "module":mod, "busMember":False, "bitIdx":None, "busName":None }))
            
            cells = myutils.cleanget(nl.get(modname), "cells")
            for name in cells:
                submodname = cells.get(name)
                mod.new_cell({"name":name, "submodname":submodname})
            
            conns = myutils.cleanget(nl.get(modname), "connections")
            for name in conns:
                ports = conns.get(name)
                if name in mod.ports:
                    net = mod.ports.get(name)
                else:
                    #todo: add parsing code to determine width msb/lsb here
                    net = mod.new_net({"name":name, "width":1, 
                                       "busMember": False,
                                       "bitIdx": None,
                                       "busName": None})
                for conn in ports.split():
                    cellport = conn.split('.')
                    if len(cellport) != 2:
                        raise Exception("Bad port: " + conn)
                    cell  = mod.cells.get(cellport[0])
                    pname = cellport[1]                
                    pin = cell.new_pin({"name":pname, "portname":pname})
                    pin.connectNet(net)
            
            if modname in self.__mods:
                print "Warning: " + modname + " has been multiply defined"
            
            self.__mods[mod.name] = mod
    
    def __makePortTupleList__(self, name, width):
        tuples = []
        
        if width == 1:
            tuples.append((name, width, False, None, None ))
        elif width > 1:
            for i in range(0,width):
                tuples.append((name + "[" + str(i) + "]", 1, True, i, name ))
        else:
            raise Exception("Bad width parameter: " + width)
        
        return tuples
    

################################################################################
################################################################################
if __name__ == "__main__":
    import doctest
    doctest.testmod()

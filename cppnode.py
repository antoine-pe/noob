import os , subprocess , sys ,  hashlib , shlex , inspect, datetime
import noob.compiler
import noob.node
import noob.filetools
import concurrent.futures
import asyncio
import re
from functools import partial
import threading 

        
modifiedLock     = threading.Lock()
modifiedLockDict = {} 
modifiedCache    = {} 
mtimeLock        = threading.Lock()
mtimeLockDict    = {}
mtimeCache       = {} 


# examples of custom display functions
# 
#def objDisplay( command , sourcePath , oFilePath , ccFlags , incsList , progress ) :
#   message  = "["+str(progress)+"%] Compiling '" + sourcePath + "' --> '" + oFilePath + "\n"
#   message +=  "\n   Includes: " + "\n   Includes: ".join( incsList ) + "\n"
#   message +=  "\n   cc_flag : " + "\n   cc_flag : ".join( ccFlags  ) + "\n"
#   print( message ) 
#
#
#def linkDisplay( commandList , targetPath , ldFlags , libs ) :
#   message  = "Linking '" + targetPath + "'" 
#   message +=  "\n   ldFlags: " + "\n   ldFlags: ".join( ldFlags ) + "\n"
#   message +=  "\n   libs   : " + "\n   lib    : ".join( libs    ) + "\n"
#   print( message ) 
#    
#def swigDisplay( commandList , swigIPath , wrapPath , swigFlags , incsList ) :
#   print("Swiging '" + swigIPath + "' --> '" + wrapPath  )
#   for inc in incsList : print("   Includes   :" , inc    )
#   print()
#   for f in swigFlags  : print("   Swig flags :" , f    )
#   print()


def checkCmd( cmd , *keywords ):
    for k in keywords : 
        if k not in cmd : return False
    return True
    

# Base class for ExeNode, DynamicLibNode and StaticLibNode
class _CppNode( noob.node.Node ) :
    
    def __init__( self ) : 
        
        noob.node.Node.__init__( self ) 
        
        # properties of this node
        self._compiler     = None
        self.incs          = [] # ex : [ "/my/path/to/inc/dir1" , "/my/path/to/inc/dir2" ]
        self.incs_system   = [] # ex : [ "/my/path/to/inc/dir1" , "/my/path/to/inc/dir2" ]
        self.srcs          = [] # ex : [ "/my/path/to/file.cc"  , "/my/path/to/file2.cc" ]
        self.cc_flags      = [] # ex : [ "-DDEBUG" , "-g" , "-O3" , ... ]
        self.ld_flags      = [] # ex : [ "-nostdlib" , "-s" , ... ]
        self.dest_dir      = "." 
        self.tmp_dir       = "."
        self.extern_libs   = [] # internal property . ex : [ {'lib_name' :'jpeg' , 'incs':'/dir/to/jpeg' , 'libs' : ['/path/to/jpeg.a'] } , {... other lib ... } ]" ,
        self.num_thread    = 8
        self.stop_on_error = True
        self.diff_method   = "mtime" # or "md5"
        self.display_mode  = 'normal'
        
        # functions to format output messages
        self.obj_display_func  = None
        self.link_display_func = None
        
        # dict of parameters allowed 
        self.parms_allowed.update( { 
            "incs"              : "Include directory paths. ex : [ '/my/path/to/inc/dir1 , '/my/path/to/inc/dir2' ]. default : [ '.' ] " ,
            "incs_system"       : "Include directory paths. ex : [ '/my/path/to/inc/dir1 , '/my/path/to/inc/dir2' ]. default : [ '.' ] " ,
            "srcs"              : "Sources file paths ( mandatory ) . ex : [ '/my/path/to/file.cc'  , '/my/path/to/file2.cpp' ]"         ,
            "cc_flags"          : "Compiler options. ex : [ '-DDEBUG' , '-g' , '-O3' , '-std=c++11' ]"                                   , 
            "ld_flags"          : "Linker options. ex : [ '-nostdlib' , '-s' ]"                                                          , 
            "dest_dir"          : "Destination directory, where the executable/library will be built. ex : '/my/dest/dir'"               , 
            "tmp_dir"           : "Temporary directory, where temporary objects (.o) will be built. ex : '/my/tmp/dir' "                 , 
            "obj_display_func"  : "Format function for compiling output messages , ex : def objDisplay( commandList , sourcePath , oFilePath , ccFlags , includes , progress ) " ,
            "link_display_func" : "Format function for linking output messages   , ex : def linkDisplay( commandList , targetPath , ldFlags , libs )",
            "num_thread"        : "Number of thread to use for compilation, equivalent to -j make option ( default : 8 )"                ,
            "stop_on_error"     : "Stop immediately if an error is found during compilation ( default : True )"                          ,
            "diff_method"       : "Method to check if a file has been modified : 'mtime' (=fast) or 'md5' (=slow) ( default : 'mtime' )" , 
            "display_mode"      : "Format of the output messages 'normal' or 'concise' ( default : 'normal' )"  
        } )
        
        
        self.cancelAll   = False # shared between coroutines to stop compilation if needed
    
    def name( self )  :
        return str( self.targets()[0] ) 
    
    def help( self ) :
        self.displayAllowedParameters()
        
    def info( self ) :
        print("--- Infos for node ", self )
        for k,v in sorted( self.parms_allowed.items() ) : 
            print( '  {:<20}'.format(k) , ":" , str( getattr( self , k ) )  ) 
        print()
    
    
    def _getCompiler( self ) :
        if not self._compiler :
            self._compiler = noob.compiler.DETECTED_COMPILER 
            if self._compiler == None :
                displayMsg  = "[ERROR] " + self.nodeType + " : \"" + self.name() +"\" build failed"
                displayMsg += " : Compiler not set"
                return self._onError( displayMsg )
                
        return self._compiler
        
        
    def build( self ) :
        noob.node.Node.execute( self )
    
    def cleanObjects( self ) :
        
        # remove object files 
        for src in self.srcs :
            objPath = self.getObjectPath( src )
            noob.filetools.rmFile( objPath )
            
        # remove temporary directory if it's empty
        noob.filetools.rmDir( self.tmp_dir )

    def cleanObjectAndTargets( self ):

        # remove temporary files and directory
        self.cleanObjects()

        # remove targets files
        for target in self.targets() :
            noob.filetools.rmFile( target )
            
        # remove temporary directory if it's empty
        noob.filetools.rmDir( self.dest_dir )

    def clean( self )  :
        self.cleanObjectAndTargets()
        
    def cleanAll( self ) :
        for node in self.getDependentList() :
            node.clean()
        self.clean()
        
        
    def setDisplayModeToConcise( self ) :
        self.display_mode = "concise"
    
    
    ## =========================
    ##  Path and commands
    ## =========================
    
    def _setParameters( self , params ) :
        
        # check if all parameters are valid
        for k,v in params.items() :
            if k not in list( self.parms_allowed.keys()) + ["calling_path"] + ["nodeType"] :
                self.displayAllowedParameters()
                raise AssertionError( "\"" + k + "\" parameter is not defined for "+ self.name() ) 
        
        # setting of parameters
        for k,v in params.items() :
            # always make paths absolute, based on the current calling path
            if k in [ "srcs" , "incs" , "libs" , "dest_dir" , "tmp_dir" ] : 
                setattr( self , k , noob.filetools.makeAbsolutePath( params["calling_path"] , params[k] ) )
            else : 
                setattr( self , k , v )
        
    
    def displayAllowedParameters( self )  :
        print("\n--- Allowed parameters for node '" + self.name() + "'" ) 
        for k,v in sorted( self.parms_allowed.items() ) : 
            print( '  {:<11}'.format(k) , ":" , v ) 
        print("\n")
        
    
    def checkExternalLibPaths( self , externalLib ) :
        
        # define what to check
        fileToCheckDict = {
            "libs"        : "library"                 , 
            "srcs"        : "source file"             , 
            "incs"        : "include directory"       ,
            "incs_system" : "include system directory"
        }
        
        # check if all file and directory paths exist on filesystem
        isEverythingFound = True
        for fileType in fileToCheckDict.keys() :
            if fileType in externalLib.keys() :
                for fileOrDirPath in externalLib[fileType] :
                    if not os.path.exists( fileOrDirPath ) : 
                        sys.stderr.write( "ERROR : '" + fileOrDirPath + "' in external " + fileToCheckDict[fileType] + " not found\n" )
                        isEverythingFound = False
                        
        return isEverythingFound
        
        
    def addExternLib( self , params ):
        
        # list of allowed params when defining external library
        extern_parms_allowed = {
            "lib_name"    : "name of the external library"                                              ,
            "incs"        : "list of include directory of the library"                                  ,
            "incs_system" : "list of include directory of the library"                                  ,
            "cc_flags"    : "list of compiler flags of the library"                                     ,  
            "ld_flags"    : "list of linker flags of the library"                                       ,
            "srcs"        : "list of sources of the library to compile along those of this node"        ,
            "libs"        : "list of static or dynamic library paths, this node has to to link against" 
        }
        
        # automatic settings
        externLib = dict.fromkeys( extern_parms_allowed.keys() , "" )
        for k,v in params.items():
            if k in extern_parms_allowed.keys() :
                externLib[k] = v
                if k == "srcs": self.srcs += v # add the external sources directly to self.srcs
            else :
                raise AssertionError(  "\"" + k + "\" parameter is not defined for an external library definition" )
        
        # add to externLibs
        self.extern_libs.append( externLib )
        

    def getObjectPath( self , sourcePath ) :
        oFileName  = os.path.basename( sourcePath )
        oFileName  = oFileName.split(".")[0]
        oFileName += noob.compiler.DETECTED_PLATFORM["obj_suffix"] 
        oFilePath  = os.path.join( self.tmp_dir , oFileName )
        return oFilePath
    

    def getAutomaticIncludes( self , dependentNodeList , incs_prefix = None ):
        
        # retrieve all include files of this node and inherited from the others as well 
        
        # list of include files to return in an list formatted as so : [ "-I/my/include/path" , "-I/other/inc" , ... ]
        automatic_includes = []
        
        # get the include prefix ( compiler dependant )
        incPrefix        = incs_prefix if incs_prefix else self._getCompiler()["incs_prefix"       ]  
        incPrefix_system = incs_prefix if incs_prefix else self._getCompiler()["incs_system_prefix"]  
        
        # add include files inherited from the other library nodes
        for node in dependentNodeList :
            if node.nodeType in [ "Dynamic Library" , "Static Library" , "Swig Library" ]:
                
                # include files from the other library nodes
                automatic_includes += [ incPrefix        + i for i in node.incs        ]
                automatic_includes += [ incPrefix_system + i for i in node.incs_system ]
                
                # include files from external libraries of the other nodes
                for extLib in node.extern_libs :
                    automatic_includes += [ incPrefix        + i for i in extLib["incs"       ] ]
                    automatic_includes += [ incPrefix_system + i for i in extLib["incs_system"] ]
        
        # add this node's extern libraries 
        for extLib in self.extern_libs :
            automatic_includes += [ incPrefix + i for i in extLib["incs"] ]
            automatic_includes += [ incPrefix_system + i for i in extLib["incs_system"] ]
          
        return list( set( automatic_includes ) )
    
       
    def getAutomaticCcFlags( self , dependentNodeList ):
        
        # compiler flags to return in a list formatted as so : [ "-DDEBUG" , "-g" , "-O3" , ... ]
        automatic_ccflags = []
        
        # add compiler flags inherited from the other nodes : 
        for node in dependentNodeList :
            if node.nodeType in [ "Dynamic Library" , "Static Library" ]:
                automatic_ccflags += node.cc_flags
                
        # add compiler flags from this node's external libraries 
        for extLib in self.extern_libs :
            automatic_ccflags += extLib["cc_flags"] 
        
        return list( set( automatic_ccflags ) )
        
        
    def getAutomaticLdFlags( self , dependentNodeList ) :
        
        # retrieve all linker flags of this node and inherited from the others as well  
        # and return a list of linker flags of the form : [ "-nostdlib" , "-s" , ... ]
        automatic_ldflags = []
        
        # add linker flags inherited from the other nodes
        for node in dependentNodeList:
            
            if node.nodeType in [ "Dynamic Library" , "Static Library" ]:
                # flags from the other library nodes to inherit
                automatic_ldflags += node.ld_flags 
            
                # flags from external libraries of the other nodes to inherit
                for extLib in node.extern_libs :
                    automatic_ldflags += extLib[ "ld_flags" ]
                            
        # add linker flags of this node's external libraries 
        for extLib in self.extern_libs :
            automatic_ldflags += extLib["ld_flags"] 
        
        return list( set( automatic_ldflags ) )
    
        
    def getAutomaticLibs( self , dependentNodeList ):
        # retrieve all linker flags of library of this node and inherited from the others as well  
        # and return a list of linker flags of the form : [ "-lmylib" , "-L/my/path" , "/path/to/static.a" , ... ]
        # used to simplify the definition of dependent libraries
        
        automatic_libs = []
        for node in dependentNodeList :
            
            # add inherited libraries and their external libraries
            if node.nodeType in [ "Dynamic Library" , "Static Library" ]:
                
                # add inherited libraries
                #automatic_libs += node.libs
                
                # add this library dependency
                automatic_libs += node.targets()
                
                # add inherited external libraries of this inherited node
                for extLib in node.extern_libs :
                    automatic_libs += extLib["libs"]
        
        # add external libraries of this node's external libraries 
        for extLib in self.extern_libs :
            automatic_libs += extLib["libs"]
        
        return list( set( automatic_libs ) )
   
   
    def getObjCommand( self, sourcePath , oFilePath , dependentNodeList ):
        
        # get include files of this node
        incs  = [ self._getCompiler()["incs_prefix"       ] + i for i in self.incs        ]
        incs += [ self._getCompiler()["incs_system_prefix"] + i for i in self.incs_system ]
         
        # retrieve inherited include file from the other nodes
        auto_includes = self.getAutomaticIncludes( dependentNodeList )
         
        # retrieve inherited compiler flags from the other nodes
        auto_ccflags = self.getAutomaticCcFlags( dependentNodeList )
         
        # format those flags in a list
        allFlags  = incs[:]
        allFlags += self.cc_flags
        allFlags += auto_ccflags
        allFlags += auto_includes
        allFlags  = list( set( allFlags ) ) # remove duplicates
        # object command generation
        cmd = ""
        if sourcePath.endswith(".cc") or sourcePath.endswith(".cpp") : cmd  = self._getCompiler()["c++_obj_cmd"]
        else                                                         : cmd  = self._getCompiler()["c_obj_cmd"  ]
        
        # check the command format correctness
        if not checkCmd( cmd , "$(IN)" , "$(OUT)" , "$(FLAGS)" ) : 
            raise AssertionError( "Misformed obj_cmd : missing either $(IN) , $(OUT) or $(FLAGS)")
        
        # split the command string to convert it in a list of options
        # substitute all keywords in the command with the proper values
        cmd_res = []
        for tok in shlex.split( cmd ):
            if   "$(IN)"    in tok : cmd_res.append( tok.replace( "$(IN)"  , sourcePath ) )
            elif "$(OUT)"   in tok : cmd_res.append( tok.replace( "$(OUT)" , oFilePath  ) )
            elif "$(FLAGS)" in tok : cmd_res.extend( allFlags )
            else                   : cmd_res.append( tok )
        
        return cmd_res , list( set( self.cc_flags + auto_ccflags ) )  , list( set( incs + auto_includes ) )
        
        
    
    def getLinkCommand( self , objs , targetPath , dependentNodeList ) :
        
        # generate the link command
        cmd = ""
        if   self.nodeType == "Executable"      : cmd = self._getCompiler()["exe_link_cmd"    ]
        elif self.nodeType == "Dynamic Library" : cmd = self._getCompiler()["dynamic_link_cmd"]
        elif self.nodeType == "Static Library"  : cmd = self._getCompiler()["static_link_cmd" ]
        elif self.nodeType == "Swig Library"    : cmd = self._getCompiler()["dynamic_link_cmd"]
            
        # inherited libs and flags. Static libraries don't inherit from node they depends on
        auto_libs    = []
        auto_ldflags = []
        
        # libs must be included on linux even for static libs
        if sys.platform == "linux" or self.nodeType != "Static Library" :
            # retreive all libraries
            auto_libs    = self.getAutomaticLibs( dependentNodeList )
            
            # retreive all linker flags
            auto_ldflags = self.getAutomaticLdFlags( dependentNodeList )
        
        
        # on windows if we want to link to a .dll , we must link to it's corresponding .lib
        cleanLibs = auto_libs[:]
        if self._getCompiler()["config_name"] in [ "msvc2008" , "msvc2012" , "msvc2013" , "msvc2015" ] :
            cleanLibs = [ l if not l.endswith(".dll") else l[:-4] + ".lib" for l in auto_libs  ]
#           for l in auto_libs[:] : 
#               if l.endswith(".dll") :
#                   l= l[:-4] + ".lib"
#               cleanLibs.append( l ) 
        
        auto_libs = cleanLibs[:]
        
        
        # final flags
        allFlags  = self.ld_flags[:]  # be sure to copy, otherwise self.ld_flags will be modified
#       allFlags += self.libs  
        allFlags += auto_libs + auto_ldflags
        allFlags  = list(set(allFlags))
        objs = list( set( objs ) ) 
        
        # check the command format correctness
        if not checkCmd( cmd , "$(IN)" , "$(OUT)" , "$(FLAGS)" ) : 
            raise AssertionError( "Misformed link command : missing either $(IN) , $(OUT) or $(FLAGS)\n" + cmd)
        
        # split the command string to convert it in a list of options
        # substitute all keywords in the command with the proper values
        cmd     = shlex.split(cmd)
        cmd_res = []
        for tok in cmd:
            if   "$(IN)"    in tok : cmd_res.extend( objs     ) 
            elif "$(OUT)"   in tok : cmd_res.append( tok.replace( "$(OUT)" , targetPath ) )
            elif "$(FLAGS)" in tok : cmd_res.extend( allFlags ) 
            else                   : cmd_res.append( tok      )
        
        return cmd_res , list( set( self.ld_flags + auto_ldflags ) ) , list( set( auto_libs ) )
        
    
    def getCapturedEnvironment( self ) :
        
        # launch the initialisation script to capture the environment variables
        # in a separate subprocess to reapply it into futur compilation subprocesses
        capturedEnvironment = {}
        
        if "init_script" in self._getCompiler().keys() :
            command = self._getCompiler()["init_script"]
            if sys.platform in ["darwin" , "linux" ] : command += ["&&" , "env" ]
            else                                     : command += ["&&" , "SET" ]
            process = subprocess.Popen( command , shell = True , stdout = subprocess.PIPE , stderr = subprocess.PIPE ) 
            ( stdout , stderr ) = process.communicate() 
            
            # parse stdout
            if stderr : 
                raise RuntimeError( stderr )
            
            if stdout : 
                res = stdout.decode( sys.getdefaultencoding() )
                for l in res.splitlines() :
                    if l != "" :
                        s = l.split("=")
                        if len(s) == 2 : capturedEnvironment[s[0]] = s[1]
                        if len(s) == 1 : capturedEnvironment[s[0]] = ""
        else :
            capturedEnvironment = os.environ
            
            
        return capturedEnvironment
        
        
        
    ## =============================
    ##  Display formatting functions
    ## =============================
    def displayObjCommand( self , commandList , sourcePath , oFilePath , ccFlags , includes , progress ) :
        if   self.obj_display_func != None  : self.obj_display_func( commandList , sourcePath , oFilePath , ccFlags , includes , progress )
        elif self.display_mode == "normal"  : print( "[" + str(progress) + "%] " + " ".join(commandList) )
        elif self.display_mode == "concise" : print( "[" + str(progress) + "%] " + oFilePath ) 
    
    
    def displayLinkCommand( self , commandList , targetPath , ldFlags , libs ) :
        if   self.link_display_func != None : self.link_display_func( commandList , targetPath , ldFlags , libs )
        elif self.display_mode == "normal"  : print( " ".join(commandList) )
        elif self.display_mode == "concise" : print( "Linking '" + targetPath + "'" ) 
        
        
    ## =========================
    ##  Compilation
    ## =========================
        
    def _onError( self , errMsg ) :
        
        sys.stderr.write( errMsg + "\n" )
        sys.stderr.flush()
        
        displayMsg  = "[ERROR] " + self.nodeType + " : \"" + self.name() +"\" build failed"
        displayMsg += " : \n   --> " + errMsg
        sys.stderr.write( displayMsg + "\n\n" )
        sys.stderr.flush()
        
        self.status  = "Error"
        self.message = displayMsg + " : " + errMsg
        
        return self
    
    def _onBuilt( self , startTime ):
        hours, remainder = divmod( (datetime.datetime.now() - startTime).seconds , 3600)
        minutes, seconds = divmod(remainder, 60)
        
        msg = "[SUCCESS] " + self.nodeType + " : \"" + self.name() +"\" built successfully"
        msg += " in " + "%.2dh:%.2dm:%.2ds"%(hours, minutes,seconds)
        print( msg + "\n" )
        self.status  = "Built"
        self.message = msg
        return self
                
    def _onUpToDate( self , startTime ):
        hours, remainder = divmod( (datetime.datetime.now() - startTime).seconds , 3600)
        minutes, seconds = divmod(remainder, 60)
        
        msg = self.nodeType + " : \"" + self.name() +"\" is up to date " 
        msg += "("+ "%.2dh:%.2dm:%.2ds"%(hours, minutes,seconds) + ")"
        print( msg + "\n" )
        self.status  = "Up-To-Date"
        self.message = msg
        return self

        
    def hasChanged( self , headerPath , cacheDict , writeCacheDictValue ) :
        # calculer les md5 ici
        with mtimeLock :
            if headerPath not in mtimeLockDict.keys() :
                mtimeLockDict[headerPath] = threading.Lock()
                
        with mtimeLockDict[headerPath] :
            if headerPath in mtimeCache.keys() :
                return mtimeCache[headerPath]
            else :
                objValue   = self.hash_method( headerPath ) 
                isModified = cacheDict.get( headerPath , "" ) != objValue
                
                if isModified :
                    writeCacheDictValue[headerPath] = objValue
                
                mtimeCache[headerPath] = isModified
                    
                return isModified 
                
                
    def hasDirectOrIndirectBeenModified( self , sourcePath , cacheDict , writeCacheDictValue ) : 
        
        # returns True if this source file includes a direct or indirect header that  
        # has been modified since the last compilation
        
        # we have a dependency DAG where roots are file source ( .cpp ) and children
        # are headers ( .h ) they depend on. The goal is to traverse all node of this
        # DAG and process each of them their corresponding MD5 or MTime.
        
        # we want to visit each nodes only once for performance reason and 
        # avoid re-traversing sub-paths already visited. Therefore we're using a 
        # global cache 'modifiedCache' that stores visited nodes, and their
        # value corresponding to the result of the sub-path from this node.
        
        # to avoid race conditions, we have to use mutex on each node and on 
        # the global cache variable. we can also avoid that by using coroutines
        # but we didn't noticed a significant performance gain.
        
        with modifiedLock :
            if sourcePath not in modifiedLockDict.keys() :
                modifiedLockDict[sourcePath] = threading.Lock()
            
        with modifiedLockDict[sourcePath] :
            if sourcePath in modifiedCache.keys():
                return modifiedCache[sourcePath]
        
            headerListModified = []
            
            includePattern = re.compile( r'^\s*#\s*include "(.+)"' )
            
            # parse sourcePath file to look for "#include" directives
            
            # open and parse sourcePath file
            with open( sourcePath ,'r' , encoding = "latin1" ) as sourceFile:   
                
                # search for #include directives
                incFileNames = []
                for line in sourceFile.readlines() :
                    m = includePattern.findall(line)
                    if len(m) ==1 :
                        incFileNames += [ m[0] ]
            
            # for each '#include' found, locate the header in the filesystem
            for inc in incFileNames :
                
                localHeaderFound = None
                isDependent      = False
                
                # search in the include directories specified by the user
                for p in self.incs :
                    testPath = os.path.join( p , inc )
                    if os.path.exists( testPath ) :
                        localHeaderFound = testPath
                        break
                
                
                # look for headers included by parent nodes of this node
                if not localHeaderFound:
                    for dependNode in self.parentNodeList :
                        if dependNode.nodeType in [ "Dynamic Library" , "Static Library" , "Swig Library" ]:
                            for p in dependNode.incs:
                                testPath = os.path.join(p,inc)
                                if os.path.exists(testPath) :
                                    localHeaderFound = testPath
                                    isDependent = True
                                    break
                                    
                                    
#                 # test external libraries
#                 if not localHeaderFound:
#                     for externLib in self._externLibs :
#                         for p in externLib["incs"]:
#                             testPath = os.path.join(p,inc)
#                             if os.path.exists(testPath) :
#                                 localHeaderFound = testPath
#                                 break
                
                # if the header was found , execute recursively if not already done for this path in the DAG
                if localHeaderFound :
                    
                    localModified = self.hasChanged( localHeaderFound , cacheDict , writeCacheDictValue )
                    
                    # keep going traversing the DAG recursively
                    # don't forget to put hasDirectOrIndirectBeenModified() in the lhs of the 'or' 
                    # as it might no be evaluated if it were on the rhs of the 'or'
                    localOrDependentModified = self.hasDirectOrIndirectBeenModified( localHeaderFound , cacheDict , writeCacheDictValue ) or localModified
                    headerListModified.append( localOrDependentModified )
                    
                else:
                    # this file is not meant to be tracked ( system file for ex )
                    pass 
            
            isSourcePathToReeval = False
            for m in headerListModified:
                isSourcePathToReeval = isSourcePathToReeval or m
                
            modifiedCache[sourcePath] = isSourcePathToReeval
                
            return isSourcePathToReeval
            
            
    
    def processObj( self , dependentNodeList , environment , sourcePath , cacheDict , progress ) : 
        
        if self.cancelAll : return "" , False , {}
        
        force_reeval = False
        
        # generate the absolute path and the name of the object
        oFilePath = self.getObjectPath( sourcePath )
        if not os.path.isabs( oFilePath ):
            oFilePath = os.path.realpath( os.path.join( os.getcwd() , oFilePath ) ) 
        
        # generate the object compilation command in a list 
        # ex : [ '-c' , '-pipe' , '-g' , '-gdwarf-2' , '-arch x86_64' , '-w' , '-fPIC' ,'-o' , 'build/hello.o src/hello.cc' ]
        command , ccFlags , includes = self.getObjCommand( sourcePath , oFilePath , dependentNodeList )
        command = [ c.strip() for c in command ] # remove harmful spaces
        
        # (re)compile the object if :
        #  - the object file has been deleted or doesn't exist
        #  - the file has been modified
        #  - one of the command's flag has changed 
        #  - one of the include path has been deleted/modified ( adding a new include path does nothing ) 
        #  - one of the header included in this file has been modified ( from this node or from a dependency )
        
        # don't skip any test to cache the useful values along the way. 
        
        # check if the object doesn't exist 
        if not os.path.exists( oFilePath ) :
            if self.display_mode != "concise" : print( oFilePath + " doesn't exist : eval" )
            force_reeval = True
        
        # this dict will store the new key/values we'll have to write at the end of this obj processing
        writeCacheDictValue = {}
        
        # check if the file has been modified. 
        srcKey   = sourcePath # + "_src" 
        srcValue  = self.hash_method( sourcePath )
        srcCached = cacheDict.get( srcKey , "" )
        if srcCached != srcValue :
            if not force_reeval : 
                if( srcCached ) : print( sourcePath + " has been modified : reeval" )
                else            : print( sourcePath + " has not been cached : eval" )
            writeCacheDictValue[srcKey] = srcValue
            force_reeval = True
        
        # check if the object command has been modified ( without include paths ) 
        cmdKey            = oFilePath + "_cmd" # sourcePath + 
        cmdCachedValueStr = cacheDict.get( cmdKey  , "" )
        cmdCachedValue    = set( s.strip() for s in cmdCachedValueStr[1:-1].split(",") )
        cmdValue          = set( v.strip() for v in command if not v.startswith( ( "-I" , "-iquote" , "-isystem" ) ) ) #v[0:2] not in [ "-I" , "-iquote" , "-isystem" ]  ) 
        if cmdCachedValue != cmdValue :
            addOpts = cmdValue      .difference( cmdCachedValue )
            subOpts = cmdCachedValue.difference( cmdValue       )
            msg     = ""
            if len( addOpts )!=0 : msg += "+['" + "','".join(addOpts) + "]"
            if len( subOpts )!=0 : msg += "-['" + "','".join(subOpts) + "]" 
                
            if not force_reeval : print( sourcePath + " command has changed " + msg + ": reeval" )
            
            # record the full command string as value to be able to display 
            # the changes to the user later if needed ( as above )
            writeCacheDictValue[cmdKey] = "[" + ",".join(cmdValue)  + "]"
            force_reeval = True
         
        
        # check if an include path has been deleted or modified
        # TODO : check if the modified include path has an impact on this obj
        # ie if this obj includes those include paths
        incsKey            = sourcePath + "_incs_paths"
        incsValue          = set( v.strip() for v in command if v.startswith( ("-I" , "-iquote" , "-isystem" ) ) )
        incsCachedValueStr = cacheDict.get( incsKey  , "" )
        incsCachedValue    = set( s.strip() for s in incsCachedValueStr[1:-1].split(",") )
        if incsCachedValueStr[1:-1].split(",") == [''] : incsCachedValue = set()
        if incsCachedValue != incsValue :
            if not force_reeval : 
                print( sourcePath + " has one include path that has been deleted or modified : reeval" ) 
                addOpts = incsValue      .difference( incsCachedValue )
                subOpts = incsCachedValue.difference( incsValue       )
                msg  = ""
                if len( addOpts )!=0 : msg += "+['" + "','".join(addOpts) + "]"
                if len( subOpts )!=0 : msg += "-['" + "','".join(subOpts) + "]" 
                print( msg )
            
            # record the full command string as value to be able to display 
            # the changes to the user later if needed ( as above )
            writeCacheDictValue[incsKey] = "[" + ",".join(incsValue) + "]"
            force_reeval = True
        
        # check 
        if self.hasDirectOrIndirectBeenModified( sourcePath , cacheDict , writeCacheDictValue ) : 
            force_reeval = True
            
        # check if a dependent header file has been modified
                
        # regenerate the object if needed
        if force_reeval :
            
            # delete all the targets beforehand, so if the compilation 
            # thread is killed, the object will be regenerated next time
            try :
                if os.path.exists( oFilePath ) : os.remove( oFilePath )
            except Exception as e:
                return self._onError( "Deletion Error of " + oFilePath +" : Cause " + str(e)  )
     
            # print the command on stdout
            self.displayObjCommand( command , sourcePath , oFilePath , ccFlags , includes , progress )
            
            # launch the compilation sub-process 
            process = subprocess.Popen( command , stdout = subprocess.PIPE , stderr = subprocess.PIPE , env = environment ) # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
            ( stdout , stderr ) = process.communicate() 
            
            if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
             
            # check if errors were generated
            if process.returncode != 0 :
                sys.stderr.write( str(stderr.decode()) ) 
                sys.stderr.flush()
                if os.path.exists( oFilePath ) : os.remove( oFilePath )
                return self._onError( "Compilation Error for " + oFilePath + " return Code " + str(process.returncode) )
            
        # check if this object exists actually
        if not os.path.exists( oFilePath ) : 
            return self._onError( "Error " + oFilePath + " doesn't exist" )
        
        return oFilePath , force_reeval , writeCacheDictValue
        
        
    def evaluate( self , **kwargs ) :
        
        # set the compiler if needed
        if "compiler" in kwargs.keys() and kwargs["compiler"] == None :
            self._compiler = kwargs["compiler"]
            
        # record the starting time
        startTime = datetime.datetime.now()
        
        # select the the correct comparison method
        if self.diff_method == "mtime" : 
            self.hash_method = lambda filePath : str(os.stat( filePath ).st_mtime)
        elif self.diff_method == "md5" : 
            self.hash_method = lambda filePath : hashlib.md5( open( filePath , 'rb' ).read() ).hexdigest()
        else:
            return self._onError( "Unknown diff method : " + self.diff_method ) 
            
        # check if all sources exists 
        for src in self.srcs:
            if not os.path.exists( src ) :
                return self._onError( "Missing file " + src )
        
        # check if files of external libs exist
        allExternalLibsOk = True
        if False in [ self.checkExternalLibPaths(l) for l in self.extern_libs ] :
            return self._onError( "Missing file in external libs " )
            
        # override the compiler if needed
        environment = os.environ
        if "compiler" in kwargs.keys() and kwargs["compiler"] != None :
            self._compiler = kwargs["compiler"]
            try :
                environment = self.getCapturedEnvironment()
            except RuntimeError as e :
                return self._onError( "Error during compiler initialisation while capturing environment: " + str(e) )
        
        # generate the list of dependent node's properties
        dependentNodeList = [ node for node in self.nodeSequenceList ]
        
        # built destination and temporary directories
        try :
            if self.tmp_dir  not in ["","."] and not os.path.exists( self.tmp_dir  ) : os.mkdir( self.tmp_dir  )
            if self.dest_dir not in ["","."] and not os.path.exists( self.dest_dir ) : os.mkdir( self.dest_dir )
        except Exception as e:
            errMsg  = "Error while creating directories " + self.tmp_dir
            errMsg += " or " + self.dest_dir + " . Reason : "  + str(e)
            return self._onError( errMsg )

        # prefetch the noob cache
        import noob
        cacheDict = noob.filetools.loadCacheDict()
        
        # process all sources with futures and ThreadPoolExecutor
        objs        = []
        forceRelink = False
        errMsg      = ""
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_thread) as executor:
            future_to_src = {}
            
            for sourceNumber,sourcePath in enumerate( self.srcs ) : 
                progress = int( float(sourceNumber + 1) / float(len(self.srcs))  * 100 )
                future_to_src[ 
                    executor.submit( self.processObj , dependentNodeList , environment, sourcePath , cacheDict , progress )
                ] = sourcePath
                
                
            for future in concurrent.futures.as_completed(future_to_src):
                src = future_to_src[future]
                try:
                    oFilePath , force_reeval , writeCacheDictValue = future.result()
                    
                    objs.append( oFilePath )
                    if len(writeCacheDictValue) > 0 :
                        cacheDict.update( writeCacheDictValue )
                        noob.filetools.saveCacheDict( cacheDict ) 
                    
                    forceRelink = force_reeval or forceRelink
                    
                except Exception as e :
                    
                    errMsg += "Processing Error " + str(e) + " " + str(src) + "\n"
                    
                    if self.stop_on_error :
                        self.cancelAll = True 
                        
                    return errMsg , objs , forceRelink 
    
        
        if errMsg : return self._onError( errMsg )
        
        
        
        # all objects ready to be linked have been compiled from here
        # if at least one object has been recompiled, then forceRelink is True
        
        # force the relink process if :
        #   - at least one object has been previously recompiled
        #   - the target has been deleted or doesn't exist yet
        #   - the linking options have been modified
        #   - this node is a dynamic library or an executable and 
        #     at least one dependent library has been modified
        
        
        # the new values to cache at the end of the link when success
        newLinkCacheDict = {}
        
        # check if the target has been deleted or doesn't exist 
        targetPath = self.targets()[0]
        if not forceRelink  and not os.path.exists( targetPath ) :
            print( "TargetPath doesn't exists" , targetPath )
            forceRelink = True
        
        # check if the linking options have been modified
        linkCommand , ldFlags , libs = self.getLinkCommand( objs , targetPath , dependentNodeList )
        linkCommand = [ c.strip() for c in linkCommand ] # remove harmful spaces
        
        linkCmdKey            = self.name() + "_link_cmd"
        linkCmdCachedValueStr = cacheDict.get( linkCmdKey  , "" )
        linkCmdCachedValue    = set( s.strip() for s in linkCmdCachedValueStr[1:-1].split(",") )
        linkCmdValue          = set( v.strip() for v in linkCommand ) 
        if linkCmdCachedValue != linkCmdValue :
            addOpts = linkCmdValue      .difference( linkCmdCachedValue )
            subOpts = linkCmdCachedValue.difference( linkCmdValue       )
            msg     = ""
            if len( addOpts )!=0 : msg += "+['" + "','".join(addOpts) + "]"
            if len( subOpts )!=0 : msg += "-['" + "','".join(subOpts) + "]" 
            
            if not forceRelink : print( "Link command has changed " + msg + ": reeval" )
            
            # record the full command string as value to be able to display 
            # the changes to the user later if needed ( as above )
            newLinkCacheDict[ linkCmdKey ] = "[" + ",".join(linkCmdValue)  + "]" 
            forceRelink = True
            
        
        # check if a dependent library node has been modified
        # if this node is a static library, there is no use in relinking
        # it, even if one of the dependent library has been modified 
        # even in case of forceRelink to True, we have to compute
        # the mtime for all dependent nodes to store them later in the cache
        if self.nodeType in [ "Dynamic Library" , "Executable" ] :
            
            # retreive the list of dependent nodes that are dynamic or static libraries
            dependLibPaths = [ n.name() for n in dependentNodeList if n.nodeType in [ "Dynamic Library" , "Static Library" ] ]
            dependLibPaths = list( set( dependLibPaths ) )
            
            # this node is an executable or a dynamic library, it is
            # mandatory to relink against the modified dependent libraries
            for libFilePath in dependLibPaths :
                objKey         = self.name() + libFilePath
                objValue       = self.hash_method( libFilePath ) 
                objCachedValue = cacheDict.get( objKey , "" )
                if  objCachedValue!= objValue :
                    print( libFilePath + " has been modified : relinking ..." )
                    forceRelink = True
                    newLinkCacheDict[objKey] = objValue
        
        
        # from here , we can safely return if nothing has to be relinked : it means
        # that no headers, no command, and no dependent libraries have been modified
        # and this node is up-to-date
        if not forceRelink : return self._onUpToDate( startTime ) 
        
        # remove the target beforhand so if the compilation thread is killed 
        # here, the target will nevertheless be recompiled next time
        try :
            if os.path.exists( targetPath ) : os.remove( targetPath )
        except Exception as e:
            return self._onError( "Deletion Error of " + targetPath +" : Cause " + str(e) )
        
        # launch the linking sub-process 
        self.displayLinkCommand( linkCommand , targetPath , ldFlags , libs )
        process = subprocess.Popen( linkCommand , stderr = subprocess.PIPE , env = environment ) # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
        ( stdout , stderr ) = process.communicate()
        if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
        
        # check if errors where generated during the link process
        if len(stderr) != 0:
            sys.stderr.write( stderr.decode( sys.getdefaultencoding() ) )
            # if os.path.exists( targetPath ) : os.remove( targetPath )
            return self._onError( "Link Error for " + targetPath + " return Code " + str(process.returncode) )
        
        # check if the target has been correctly generated
        if not os.path.exists( targetPath ) : 
            return self._onError( "Error " + targetPath + " doesn't exist" )
        
        # record the new values in the cache if needed
        if len(newLinkCacheDict) > 0 :
            cacheDict.update( newLinkCacheDict )
            noob.filetools.saveCacheDict( cacheDict ) 
        
        # everything has been successfully built , we can leave now 
        return self._onBuilt( startTime )



class ExecutableNode( _CppNode ):
    
    def __init__( self , **params ):
        
        _CppNode.__init__( self )
        self.exe_name = "out" 
        
        # get the module's path to convert relative paths to absolute
        myFilename = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        
        # set the parameters
        self.nodeType = "Executable" 
        self.parms_allowed.update( { "exe_name" : "Name of the final executable ( mandatory )" })
        _CppNode._setParameters( self , params )
        
    def targets( self ) :
        return [ os.path.join( self.dest_dir , self.exe_name + noob.compiler.DETECTED_PLATFORM["exe_suffix"] ) ]
        


class StaticLibraryNode( _CppNode ):
    
    def __init__( self , **params ):
        
        _CppNode.__init__( self )
        self.lib_name = "" 
        self.exact_lib_name = "" 
        
        # get the module's path to convert relative paths to absolute
        myFilename = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        
        # set the parameters
        self.nodeType = "Static Library" 
        self.parms_allowed.update( { "lib_name" : "Name of the generated library ( suffix is automatically determined, and 'lib' may be used as prefix )" } )
        self.parms_allowed.update( { "exact_lib_name" : "Exact name of the generated library. No prefix nor suffix will be added" } )
        _CppNode._setParameters( self , params )
        
        
    def targets( self ):
        if   sys.platform in [ "darwin" , "linux" ] : libname = "lib" + self.lib_name
        elif sys.platform == "win32" : libname = self.lib_name
        libname += noob.compiler.DETECTED_PLATFORM["static_suffix" ] 
        return [ os.path.join( self.dest_dir , libname ) ]




class DynamicLibraryNode( _CppNode ):
    
    def __init__( self , **params ):
        
        _CppNode.__init__( self )
        self.lib_name = "" 
        self.exact_lib_name = "" 
        
        # get the module's path to convert relative paths to absolute
        myFilename = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        
        # set the parameters
        self.nodeType = "Dynamic Library"
        self.parms_allowed.update( { "lib_name" : "Name of the generated library ( suffix is automatically determined, and 'lib' may be used as prefix )" } )
        self.parms_allowed.update( { "exact_lib_name" : "Exact name of the generated library. No prefix nor suffix will be added" } )
        _CppNode._setParameters( self , params )
        
        
    def targets( self ):
        if self.exact_lib_name : libname = self.exact_lib_name
        else:
            if   sys.platform in [ "darwin" , "linux" ] : libname = "lib" + self.lib_name
            elif sys.platform == "win32"                : libname = self.lib_name
            libname += noob.compiler.DETECTED_PLATFORM["dynamic_suffix"]             
        return [ os.path.join( self.dest_dir , libname ) ]
        
    
    def cleanObjectAndTargets( self ) :
        # remove temporary files ( objects for instance )
        self.cleanObjects()

        # remove targets files
        for target in self.targets() :
            noob.filetools.rmFile( target )
        
        # on Windows , remove .exp and .lib files as well
        if sys.platform == "win32"  :
            noob.filetools.rmFile( self.targets()[0][:-4] + ".lib" )
            noob.filetools.rmFile( self.targets()[0][:-4] + ".exp" )
            
        # remove temporary directory if it's empty
        noob.filetools.rmDir( self.dest_dir )
        
        
        

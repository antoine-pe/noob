import os , subprocess , sys ,  hashlib , shlex , inspect
import noob.compiler
import noob.node
import noob.filetools


def checkCmd( cmd , *keywords ):
    for k in keywords : 
        if k not in cmd : return False
    return True


# Base class for ExeNode, DynamicLibNode and StaticLibNode
class _CppNode( noob.node.Node ) :
    
    def __init__( self ) : 
        
        noob.node.Node.__init__( self ) 
        
        # properties of this node
        self.compiler    = None
        self.incs        = [] # ex : [ "/my/path/to/inc/dir1" , "/my/path/to/inc/dir2" ]
        self.srcs        = [] # ex : [ "/my/path/to/file.cc"  , "/my/path/to/file2.cc" ]
        self.cc_flags    = [] # ex : [ "-DDEBUG" , "-g" , "-O3" , ... ]
        self.ld_flags    = [] # ex : [ "-nostdlib" , "-s" , ... ]
        self.dest_dir    = "." 
        self.tmp_dir     = "."
        self.extern_libs = [] # internal property . ex : [ {'lib_name' :'jpeg' , 'incs':'/dir/to/jpeg' , 'libs' : ['/path/to/jpeg.a'] } , {... other lib ... } ]" ,
        
        # functions to format output messages
        self.obj_display_func  = None
        self.link_display_func = None
        
        # dict of parameters allowed 
        self.parms_allowed.update( { 
            "incs"              : "Include directory paths. ex : [ '/my/path/to/inc/dir1 , '/my/path/to/inc/dir2' ]. default : [ '.' ] " ,
            "srcs"              : "Sources file paths ( mandatory ) . ex : [ '/my/path/to/file.cc'  , '/my/path/to/file2.cpp' ]"    ,
            "cc_flags"          : "Compiler options. ex : [ '-DDEBUG' , '-g' , '-O3' , '-std=c++11' ]"               , 
            "ld_flags"          : "Linker options. ex : [ '-nostdlib' , '-s' ]"                                      , 
            "dest_dir"          : "Destination directory, where the executable/library will be built. ex : '/my/dest/dir'"  , 
            "tmp_dir"           : "Temporary directory, where temporary objects (.o) will be built. ex : '/my/tmp/dir' "       , 
            "obj_display_func"  : "format function for compiling output messages , ex : def objDisplay( commandList , sourcePath , oFilePath , ccFlags , includes ) " ,
            "link_display_func" : "format function for linking output messages   , ex : def linkDisplay( commandList , targetPath , ldFlags , libs ) " 
        } )
        
        
    def name( self)  :
        return str( self.targets() ) 
    
    def help( self ) :
        self.displayAllowedParameters()
        
    def info( self ) :
        print("--- Infos for node ", self )
        for k,v in sorted( self.parms_allowed.items() ) : 
            print( '  {:<20}'.format(k) , ":" , str( getattr( self , k ) )  ) 
        print()
        
    
    def build( self , compiler = noob.compiler.DETECTED_COMPILER ) :
        if compiler == None : 
            displayMsg  = "[ERROR] " + self.nodeType + " : \"" + str( self.targets() ) +"\" build failed"
            displayMsg += " : Compiler not set"
            sys.stderr.write( displayMsg + "\n\n" )
            return
            
        noob.node.Node.execute( self , compiler = compiler )
    
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

    def cleanAll( self ) :
        for node in self.getDependentList() :
            node.cleanObjectAndTargets()
        self.cleanObjectAndTargets()
        
        
        
    
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
        print("\n--- Allowed parameters for node '" + str( self.targets() ) + "'" ) 
        for k,v in sorted( self.parms_allowed.items() ) : 
            print( '  {:<11}'.format(k) , ":" , v ) 
        print("\n")
        
        
    def addExternLib( self , params ):
        
        # list of allowed params when defining external library
        extern_parms_allowed = {
            "lib_name" : "name of the external library"                                              ,
            "incs"     : "list of include directory of the library"                                  ,
            "cc_flags" : "list of compiler flags of the library"                                     ,  
            "ld_flags" : "list of linker flags of the library"                                       ,
            "srcs"     : "list of sources of the library to compile along those of this node"        ,
            "libs"     : "list of static or dynamic library paths, this node has to to link against" 
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
        incPrefix = incs_prefix if incs_prefix else self.compiler["incs_prefix"]  
        
        # add include files inherited from the other library nodes
        for node in dependentNodeList :
            if node.nodeType in [ "Dynamic Library" , "Static Library" , "Swig Library" ]:
                
                # include files from the other library nodes
                automatic_includes += [ incPrefix + i for i in node.incs ]
                
                # include files from external libraries of the other nodes
                for extLib in node.extern_libs :
                    automatic_includes += [ incPrefix + i for i in extLib["incs"] ]
        
        # add this node's extern libraries 
        for extLib in self.extern_libs :
            automatic_includes += [ incPrefix + i for i in extLib["incs"] ]
          
#       print("automatic includes" , list( set( automatic_includes ) ) ) 
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
#               automatic_libs += node.libs
                
                # add this library dependency
                automatic_libs += node.targets()
                
                # add inherited external libraries of this inherited node
                for extLib in node.extern_libs :
                    automatic_libs += extLib["libs"]
                    
        return list( set( automatic_libs ) )
   
   
    def getObjCommand( self, sourcePath , oFilePath , dependentNodeList ):
        
        # get include files of this node
        incs = [ self.compiler["incs_prefix"] + i for i in self.incs ]
         
        # TODO : to further optimise the following , we may precaculate
        # once for all the automaticIncludes and automaticsCCFlags
        # because this method is called for every object file to compile
        
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
        if sourcePath.endswith(".cc") or sourcePath.endswith(".cpp") : cmd  = self.compiler["c++_obj_cmd"]
        else                                                         : cmd  = self.compiler["c_obj_cmd"  ]
            
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
        if   self.nodeType == "Executable"      : cmd = self.compiler["exe_link_cmd"    ]
        elif self.nodeType == "Dynamic Library" : cmd = self.compiler["dynamic_link_cmd"]
        elif self.nodeType == "Static Library"  : cmd = self.compiler["static_link_cmd" ]
        elif self.nodeType == "Swig Library"    : cmd = self.compiler["dynamic_link_cmd"]
            
            
        # inherited libs and flags. Static libraries don't inherited from node they depends on
        auto_libs    = []
        auto_ldflags = []
        
        # if self.nodeType != "Static Library" : # libs must be included on linux even for static libs
        
        if sys.platform == "linux" or self.nodeType != "Static Library" :
            # retreive all libraries
            auto_libs    = self.getAutomaticLibs( dependentNodeList )
            
            # retreive all linker flags
            auto_ldflags = self.getAutomaticLdFlags( dependentNodeList )
        
        
        # on windows if we want to link to a .dll , we must link to it's corresponding .lib
        cleanLibs = auto_libs[:]
        if self.compiler["config_name"] in [ "msvc2008" , "msvc2012" , "msvc2013" , "msvc2015" ] :
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
        
        if "init_script" in self.compiler.keys() :
            command = self.compiler["init_script"]
            if sys.platform in ["darwin" , "linux" ] : command += ["&&" , "env" ]
            else                                     : command += ["&&" , "SET" ]
            process = subprocess.Popen( command , shell = True , stdout = subprocess.PIPE , stderr = subprocess.PIPE ) 
            ( stdout , stderr ) = process.communicate() 
            returnCode = process.wait()
            
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
    def displayObjCommand( self , commandList , sourcePath , oFilePath , ccFlags , includes ) :
        if self.obj_display_func != None : self.obj_display_func( commandList , sourcePath , oFilePath , ccFlags , includes )
        else                             : print( " ".join(commandList) )
    
    
    def displayLinkCommand( self , commandList , targetPath , ldFlags , libs ) :
        if self.link_display_func != None : self.link_display_func( commandList , targetPath , ldFlags , libs )
        else                              : print( " ".join(commandList) )
        
        
    ## =========================
    ##  Compilation
    ## =========================
        
    def _onError( self , errMsg ) :
        
        sys.stderr.write( errMsg + "\n" )
        sys.stderr.flush()
        
        displayMsg  = "[ERROR] " + self.nodeType + " : \"" + str( self.targets() ) +"\" build failed"
        displayMsg += " : \n   --> " + errMsg
        sys.stderr.write( displayMsg + "\n\n" )
        sys.stderr.flush()
        
        self.status  = "Error"
        self.message = displayMsg + " : " + errMsg
        
        return self
    
    def _onBuilt( self ):
        msg = "[SUCCESS] " + self.nodeType + " : \"" + str( self.targets() ) +"\" built successfully"
        print( msg + "\n" )
        self.status  = "Built"
        self.message = msg
        return self
                
    def _onUpToDate( self ):
        msg = self.nodeType + " : \"" + str( self.targets() ) +"\" is up to date"
        print( msg + "\n" )
        self.status  = "Up-To-Date"
        self.message = msg
        return self

    def _getDirectHeaders( self , sourcePath , headerList ):
        
        # parse sourcePath file to look for "#include" directives
        import re
        p = re.compile( r'^#include "(.+)"')
        
        # open and parse sourcePath file
        with open( sourcePath ,'r', encoding = "latin1" ) as sourceFile:
            
            # search for #include directives
            incFileNames = []
            for line in sourceFile.readlines() :
                m = p.findall(line)
                if len(m) ==1 :
                    incFileNames += [ m[0] ]
        
            # for each '#include' found, locate the header in the filesystem
            for inc in incFileNames :
                
                localHeaderFound = None
                
                # search in the include directories specified by the user
                for p in self.incs:
                    testPath = os.path.join( p , inc )
                    if os.path.exists( testPath ) :
                        localHeaderFound = testPath
                        break
                
#                 # tester dans les librairies externes
#                 if not localHeaderFound:
#                     for externLib in self._externLibs :
#                         for p in externLib["incs"]:
#                             testPath = os.path.join(p,inc)
#                             if os.path.exists(testPath) :
#                                 localHeaderFound = testPath
#                                 break
                
#                 # tester dans les librairies dont ce noeud depend
#                 if not localHeaderFound:
#                     for plug in [ plug for plug in self.inputs() if "D_" in plug.name() ] :
#                         dependNode = plug._read()
#                         if dependNode.nodeType() in  ["Dynamic Library" , "Static Library" , "Swig Library" ]:
#                             for p in dependNode.incs:
#                                 testPath = os.path.join(p,inc)
#                                 if os.path.exists(testPath) :
#                                     localHeaderFound = testPath
#                                     break
                
                # if the header was found , execute recursively 
                if localHeaderFound :
                    headerList.append( localHeaderFound )

                    # recursif call
                    self._getDirectHeaders( localHeaderFound , headerList )
                    
                else :   
                    pass
                    #print( "include " + inc + " not found from " + sourcePath )
                    
                    
    def _getDependHeaders( self , sourcePath , headerList ) :
        
        # parse sourcePath file to look for "#include" directives
        import re
        p = re.compile( r'^#include "(.+)"')
        
        # open and parse sourcePath file
        with open( sourcePath ,'r') as sourceFile:
            incFileNames = []
            
            # search for #include directives
            for line in sourceFile :
                m = p.findall(line)
                if len(m) ==1 :
                    incFileNames += [ m[0] ]
            
            # for each '#include' found, locate the header in the filesystem
            for inc in incFileNames :
                
                localHeaderFound = None
                
                # look for headers included by parent nodes of this node
                if not localHeaderFound:
                    for dependNode in self.parentNodeList :
                        if dependNode.nodeType in  [ "Dynamic Library" , "Static Library" , "Swig Library" ]:
                            for p in dependNode.incs:
                                testPath = os.path.join(p,inc)
                                if os.path.exists(testPath) :
                                    localHeaderFound = testPath
                                    break
                                    
                                    
                # if the header was found , add it to the header list
                if localHeaderFound :
                    headerList.append(localHeaderFound)

                    # recursif call
                    #self._getDependHeaders( localHeaderFound , headerList )
                    

    def evaluate( self , **kwargs ) :
        
        # check if all sources exists 
        for src in self.srcs:
            if not os.path.exists( src ):
                return self._onError( "Missing file " + src )
        
        # override the compiler if needed
        environment = os.environ
        if "compiler" in kwargs.keys() and kwargs["compiler"] != None :
            self.compiler = kwargs["compiler"]
            try :
                environment = self.getCapturedEnvironment()
            except RuntimeError as e :
                return self._onError( "Error during compiler initialisation : " + str(e) )
        
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

        # compile each objects if needed
        force_reeval = False
        forceRelink  = False
        objs         = []
        for sourcePath in self.srcs:
            
            # generate the absolute path and the name of the object
            oFilePath = self.getObjectPath( sourcePath )
            if not os.path.isabs( oFilePath ):
                oFilePath = os.path.realpath( os.path.join( os.getcwd() , oFilePath ) ) 

            # generate the object compilation command in a list 
            # ex : [ '-c' , '-pipe' , '-g' , '-gdwarf-2' , '-arch x86_64' , '-w' , '-fPIC' ,'-o' , 'build/hello.o src/hello.cc' ]
            command , ccFlags , includes = self.getObjCommand( sourcePath , oFilePath , dependentNodeList )

            # (re)compile the object if :
            #  - the object file has been deleted or doesn't exist
            #  - the file has been modified
            #  - one of the command's flag has changed 
            #  - one of the include path has been deleted/modified ( adding a new include path does nothing ) 
            #  - one of the header included in this file has been modified ( from this node or from a dependency )
            
            # TODO : for performance reason, we may add multiple tests of force_reeval before checking value 
            # to avoid unecessary md5 calculations or file reading operations
            
            # check if the object doesn't exist 
            if not os.path.exists( oFilePath ) :
                print( oFilePath + " doesn't exist : eval" )
                force_reeval = True
            
            
            # check if the file has been modified. 
            srcKey   = hashlib.md5( ( sourcePath + "_src" ).encode("ascii") )  # + self.name()
            srcValue = hashlib.md5( open( sourcePath , 'r' ).read().encode("latin1")      ) 
            if noob.filetools.getCachedValue( srcKey ) != srcValue.hexdigest() :
                if not force_reeval : print( sourcePath + " has been modified : reeval" )
                force_reeval = True
            
            # check if the object command has been modified ( without include paths ) 
            cmdKey            = hashlib.md5( ( sourcePath + oFilePath + "_cmd").encode("ascii") )  #+ self.name()
            cmdCachedValueStr = noob.filetools.getCachedValue( cmdKey )
            cmdCachedValue    = set( s.strip() for s in cmdCachedValueStr[1:-1].split(",") )
            cmdValue          = set( v for v in command if v[0:2]!="-I" ) 
            if cmdCachedValue != cmdValue :
                addOpts = cmdValue      .difference( cmdCachedValue )
                subOpts = cmdCachedValue.difference( cmdValue       )
                msg  = ""
                if len( addOpts )!=0 : msg += "+['" + "','".join(addOpts) + "]"
                if len( subOpts )!=0 : msg += "-['" + "','".join(subOpts) + "]" 
                    
                if not force_reeval : print( sourcePath + " command has changed " + msg + ": reeval" )
                force_reeval = True
         
            
            # check if an include path has been deleted or modified
            incsKey            = hashlib.md5( ( sourcePath + "_incs_paths" ).encode("ascii") )  # + self.name()
            incsCachedValueStr = noob.filetools.getCachedValue( incsKey )
            incsValue          = set( v for v in command if v[0:2]=="-I" )
#           incsCachedValue    = set( s.strip() for s in incsCachedValueStr[1:-1].split(",") )
            if incsCachedValueStr[1:-1].split(",") == [''] : incsCachedValue = set()
            else : incsCachedValue = set( s.strip() for s in incsCachedValueStr[1:-1].split(",") )
            if incsCachedValue != incsValue :
#           if not incsCachedValue.issubset(incsValue) :
                if not force_reeval : print( sourcePath + " has one include path that has been deleted or modified : reeval" ) 
                force_reeval = True
            
            
            # TODO : to further optimise the following , we may precalculate 
            # a list of all headers files used by all the object to avoid redundant readings
            # of the same header files ( include of direct and dependent header files ) 
            # and pre-storing md5 in a dict for instance with the filepath as a key
            # beforehand of this loop. 
            # also we may also merge _getDirectHeaders() and _getDependHeaders() to avoid 
            # redundant readings when looking for #include directives
            
            # check if a direct header file has been modified
            directHeaderList = []
            self._getDirectHeaders( sourcePath , directHeaderList )
            for h in directHeaderList:
                objKey   = hashlib.md5( ( h + sourcePath ).encode("ascii") )
                objValue = hashlib.md5( (open(h,'rb').read()))
                if noob.filetools.getCachedValue(objKey) != objValue.hexdigest() :
                    if not force_reeval : print( h + " from direct header files has been modified : reeval" )
                    force_reeval = True
                    break
                        
            
            # check if a dependent header file has been modified
            dependHeaderList = []
            self._getDependHeaders( sourcePath , dependHeaderList ) 
            for h in dependHeaderList:
                objKey   = hashlib.md5( (h + sourcePath).encode("ascii") )
                objValue = hashlib.md5( open(h,'rb').read() )
                if noob.filetools.getCachedValue(objKey) != objValue.hexdigest() :
                    if not force_reeval : print( h + " from dependent header files has been modified : reeval" )
                    force_reeval = True
                    break
            
            
            # regenerate the object if needed
            if force_reeval :
                
                # delete all the targets beforehand, so if the compilation 
                # thread is killed, the object will be regenerated next time
                try :
                    if os.path.exists( oFilePath ) : os.remove( oFilePath )
                except Exception as e:
                    return self._onError( "Deletion Error of " + oFilePath +" : Cause " + str(e) )
         
                # print the command on stdout
                self.displayObjCommand( command , sourcePath , oFilePath , ccFlags , includes )
                
                # launch the compilation sub-process 
                process = subprocess.Popen( command , stdout = subprocess.PIPE , stderr = subprocess.PIPE , env = environment ) # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
                ( stdout , stderr ) = process.communicate() 
                
                if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
                returnCode = process.wait()
                 
                # check if errors were generated
                #if stderr and len(stderr) != 0 :
                if returnCode != 0 :
                    sys.stderr.write( str(stderr) ) 
                    if os.path.exists( oFilePath ) : os.remove( oFilePath )
                    return self._onError( "Compilation Error for " + oFilePath + " return Code " + str(process.returncode) )
                
                # at least one object has been recompiled : force the relink process
                forceRelink = True

                # save the new values of this object in the cache file
                noob.filetools.setCacheValue   ( srcKey  , srcValue                        )
                noob.filetools.setCacheStrValue( cmdKey  , "[" + ",".join(cmdValue)  + "]" )
                noob.filetools.setCacheStrValue( incsKey , "[" + ",".join(incsValue) + "]" )
            
            
            # check if this object exists actually
            if not os.path.exists( oFilePath ) : raise RuntimeError( "Error " + oFilePath + " doesn't exist")
            
            # add it to the list of object ready to be linked
            objs.append( oFilePath )
            
            # generate md5 for all header ( direct or dependent ) 
            # used by this object and save it in the cache file
            
            # TODO : for performance reason , move this part 
            # in the check sequence above to avoid re-reading files 
            # and md5 recalculation
            for directHeader in directHeaderList :
                objKey   = hashlib.md5( ( directHeader + sourcePath ).encode("ascii") )
                objValue = hashlib.md5( open( directHeader ,'rb' ).read() )
                noob.filetools.setCacheValue( objKey , objValue )
            
            for dependHeader in dependHeaderList:
                objKey   = hashlib.md5( (dependHeader + sourcePath ).encode("ascii") )
                objValue = hashlib.md5( open(dependHeader,'rb').read() )
                noob.filetools.setCacheValue( objKey, objValue ) 

        
        # all objects ready to be linked have been compiled from here
        # if at least one object has been recompiled, then forceRelink is True
        
        # force the relink process if :
        #   - at least one object has been previously recompiled
        #   - the target has been deleted or doesn't exist yet
        #   - the linking options have been modified
        #   - this node is a dynamic library or an executable and 
        #     at least one dependent library has been modified
        
        # check if the target has been deleted or doesn't exist 
        targetPath = self.targets()[0]
        if not forceRelink : 
            if not os.path.exists( targetPath ) :
                forceRelink = True
        
        # check if the linking options have been modified
        linkKey   = hashlib.md5( self.name().encode("ascii") + b"_link" ) 
        linkValue = hashlib.md5( " ".join( self.getLinkCommand( objs , targetPath , dependentNodeList )[0] ).encode("ascii") ) 
        if not forceRelink :
            if force_reeval or noob.filetools.getCachedValue( linkKey ) != linkValue.hexdigest() :
                forceRelink = True
        
        # check if a dependent library has been modified by checking its md5
        dependLibs = [ n.targets()[0] for n in dependentNodeList if n.nodeType in [ "Dynamic Library" , "Static Library" ] ]
        dependLibs = list( set( dependLibs ) )
        if not forceRelink :

            # if this node is a static library, there is no use in 
            # relinking it, if one of the dependent library has been modified
            if self.nodeType == "Static Library" :
                return self._onUpToDate()
            
            # if this node is an executable or a dynamic library, it is
            # mandatory to relink against the modified dependent libraries
            elif self.nodeType in [ "Dynamic Library" , "Executable" ] :
                for libFile in dependLibs :
                    objKey   = hashlib.md5( libFile.encode("ascii") ) # + self.name()
                    objValue = hashlib.md5( open( libFile ,'rb').read() ) # open the lib as a binary file
                    if noob.filetools.getCachedValue( objKey ) != objValue.hexdigest() :
                        print( libFile + " has been modified : relinking ..." )
                        forceRelink = True
                        break
                
                
        # from here , we can safely return if nothing has to be relinked : it means
        # that no headers, no command, and no dependent libraries have been modified
        # and this node is up-to-date
        if not forceRelink : return self._onUpToDate( ) 
        
        # remove the target beforhand so if the compilation thread is killed 
        # here, the target will nevertheless be recompiled next time
        try :
            if os.path.exists( targetPath ) : os.remove( targetPath )
        except Exception as e:
            return self._onError( "Deletion Error of " + targetPath +" : Cause " + str(e) )
        
        # generate link command and display it in the console
        command , ldFlags , libs = self.getLinkCommand( objs , targetPath , dependentNodeList )
        self.displayLinkCommand( command , targetPath , ldFlags , libs )
#       print( " ".join(command) )
        
        # launch the linking sub-process 
        process = subprocess.Popen( command , stderr = subprocess.PIPE , env = environment ) # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
        ( stdout , stderr ) = process.communicate()
        if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
        process.wait()
        
        
        # check if errors where generated during the link process
        if len(stderr) != 0:
            sys.stderr.write( stderr.decode( sys.getdefaultencoding() ) )
            # if os.path.exists( targetPath ) : os.remove( targetPath )
            return self._onError( "Link Error for " + targetPath + " return Code " + str(process.returncode) )

        # save the command's md5 in the cache file
        noob.filetools.setCacheValue( linkKey , linkValue )
        
        # save the libs's md5 in the cache file
        # TODO : for performance reason : move this part above to avoid
        # redondant readings and md5 calculations
        
        for libFile in dependLibs :
            objKey   = hashlib.md5( ( libFile ).encode("ascii") ) # + self.name()
            objValue = hashlib.md5( ( open( libFile , 'rb' ).read() ) ) # open the lib as a binary file
#           objValue = md5raw( libFile )
            noob.filetools.setCacheValue( objKey, objValue )
        
        # check if the target has been correctly generated
        if not os.path.exists( targetPath ) : 
            return self._onError( "Error " + targetPath + " doesn't exist" )
        
        # everything is ok , we can leave now 
        return self._onBuilt()








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
        
        # get the module's path to convert relative paths to absolute
        myFilename = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        
        # set the parameters
        self.nodeType = "Static Library" 
        self.parms_allowed.update( { "lib_name" : "Name of the generated library ( mandatory ) " } )
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
        
        # get the module's path to convert relative paths to absolute
        myFilename = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        
        # set the parameters
        self.nodeType = "Dynamic Library"
        self.parms_allowed.update( { "lib_name" : "Name of the generated library" } )
        _CppNode._setParameters( self , params )
        
        
    def targets( self ):
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
        

#from cppNode import _CppNode
import noob.cppnode
import noob.filetools
from noob.configs import python , swig

from noob.exceptions import AssertException , RuntimeException
from hashlib import md5
import os , sys , shutil, inspect , shlex , subprocess

        
class SwigNode( noob.cppnode._CppNode ) :
    
    def __init__( self , **params ):
        
        noob.cppnode._CppNode.__init__( self )
        self.lib_name = "" 
        self.swig_flags  = ["-python","-c++" ] #,"-debug-tmsearch"]
        
        # get the module's path to convert relative paths to absolute
        myFilename = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        
        # set the parameters
        self.nodeType          = "Swig Library" 
        self.swig_display_func = None
        self.parms_allowed.update( { 
            "lib_name"          : "Name of the generated library"  ,
            "swig_flags"        : "Options for swig.exe, ex : [\"-python\",\"-c++\"] " ,
            "swig_display_func" : "format function for swig output messages , ex : def swigDisplay( commandList , swigIPath , wrapPath , swigFlags , incsList ) " ,
        } )
        noob.cppnode._CppNode._setParameters( self , params )
        

    def clean(self):
        
        # remove temporary files 
        for src in self.srcs :
            wrapPath = self.getWrapperPath(src)
            noob.filetools.rmFile( wrapPath )
            
            objPath  = self.getObjectPath( src )
            noob.filetools.rmFile( objPath )
            
        # remove temporary directory if it's empty
        noob.filetools.rmDir( self.tmp_dir )

    def realclean(self):

        # remove temporary files 
        self.clean()

        # remove targets files
        for target in self.targets() :
            noob.filetools.rmFile( target )
            
        # remove temporary directory if it's empty
        noob.filetools.rmDir( self.dest_dir )

    
    
    ## =========================
    ##  Path and commands
    ## =========================
    
    def searchInclude( self , incFileName , dep_prop_list ):
        
        # look for a file called incFileName in 
        # their own include directories 
        for i in self.incs:
            if incFileName in os.listdir(i):
                return os.path.join(i,incFileName)
            
        # if not found, look into dependency's include directories
        for p in dep_prop_list :
            if p.nodeType in ["Dynamic Library" , "Static Library" , "Swig Library" ]:
                for i in p.incs:
                    if incFileName in os.listdir(i):
                        return os.path.join(i,incFileName)
        
            
#       INFO( "File " + incFileName + " not found in include paths")
        return None
    
    
    def _analyseSwigFile( self, swigIPath , dep_prop_list ) :
        
        # recursive function to read all 
        # files dependent of this swig file
        import re
        p = re.compile( r'^#include "(.+)"')
        
        # parse this .swig file to find "#include" directives
        with open( swigIPath ,'r' , encoding="latin1" ) as swigFile:
            incFileNames = []
            for line in swigFile :
                m = p.findall(line)
                if len(m) ==1 :
                    incFileNames += [ m[0] ]
            
            # read each .h file and concatenate it in a string
            res = b""
            for fileName in incFileNames:
                incFilePath = self.searchInclude(fileName, dep_prop_list)
                if incFilePath != None :
                    res += open(incFilePath,'rb').read()
            
            # parse this .swig file to find "%include" directives
            p = re.compile( r'^%include ([^\s]+)')
            incFileNames = []
            swigFile = open( swigIPath ,'r' , encoding="latin1" )
            for line in swigFile :
                m = p.findall(line)
                
                # remove quotation marks if needed
                if len(m) ==1 :
                    if m[0][0]  == "\"" : m[0] = m[0][1:]
                    if m[0][-1] == "\"" : m[0] = m[0][0:-1]
                    
                if len(m) ==1 and not m[0].endswith(".i"):
                    # don't take into account standard libs of swig
                    #if "std_string.i" in m[0] : continue
                    #if "typemaps.i"   in m[0] : continue
                    #if "exception.i"  in m[0] : continue
                    incFileNames += [ m[0] ]
                
        
        # - read included swig files and concatenate them
        # - then parse them recursively
        for fileName in incFileNames:
            incFilePath = self.searchInclude(fileName, dep_prop_list)
            if incFilePath != None :
                res += open(incFilePath,'rb').read()
                res += self._analyseSwigFile( incFilePath , dep_prop_list )

        return res
                
            
        
    def getIncMD5(self , swigIPath , dep_prop_list ):
        res = self._analyseSwigFile( swigIPath , dep_prop_list )
        return md5(res).hexdigest()
            
        
    def getWrapperPath( self , swigIPath ):
        wFilePath  = os.path.basename( swigIPath )
        wFilePath  = wFilePath.split(".")[0]
        wFilePath += "_wrap.cpp" 
        wFilePath  = os.path.join( self.tmp_dir , wFilePath )
        return wFilePath
    
    def getObjectPath(self , swigIPath ):
        oFilePath  = os.path.basename( swigIPath )
        oFilePath  = oFilePath.split(".")[0]
        oFilePath += noob.compiler.DETECTED_PLATFORM["obj_suffix"] 
        oFilePath  = os.path.join( self.tmp_dir , oFilePath )
        return oFilePath
    
    def getPythonWrapperPath( self , swigIPath ):
        hFilePath  = os.path.basename( swigIPath )
        hFilePath  = hFilePath.split(".")[0]
        hFilePath += ".py" 
        hFilePath  = os.path.join( self.tmp_dir , hFilePath )
        return hFilePath
    
    def getPythonWrapperPathDest( self , swigIPath ):
        hFilePath  = os.path.basename( swigIPath )
        hFilePath  = hFilePath.split(".")[0]
        hFilePath += ".py" 
        hFilePath  = os.path.join( self.dest_dir , hFilePath )
        return hFilePath
    
    def getObjectWrapPath( self , swigIPath ):
        owFilePath  = os.path.basename( swigIPath )
        owFilePath  = owFilePath.split(".")[0]
        owFilePath += "_wrap" + noob.compiler.DETECTED_PLATFORM["obj_suffix"] 
        owFilePath  = os.path.join( self.tmp_dir , owFilePath )
        return owFilePath
    
    
    def getWrapCommand(self , swigIPath , wrapPath , dep_prop_list ): 
        cmd  = swig.SWIG_CONFIG["swig_cmd"]
        
        # check the command format correcteness
        if not noob.cppnode.checkCmd(cmd , "$(IN)" , "$(OUT)" , "$(FLAGS)") : 
            raise AssertException("Misformed swig wrap command : missing either $(IN) , $(OUT) or $(FLAGS)")
        
        # substitution    
#       print( "swig flags" , self.swig_flags )
        flags   = self.swig_flags[:] # les flags propres a swig
        flags.extend( [ "-I" + i for i in self.incs] ) # swig utilise toujours -I
        
        # automatics includes
        #flags += " "
        flags .extend( self.getAutomaticIncludes(dep_prop_list ,"-I") )
        flags = list( set( flags ) )

        # first split the command , then do substitutions
        # to handle paths with space in it
        cmd = shlex.split(cmd)
        cmd_res = []
        for tok in cmd:
            if   "$(IN)"    in tok : cmd_res.append( tok.replace( "$(IN)"  , swigIPath ) )
            elif "$(OUT)"   in tok : cmd_res.append( tok.replace( "$(OUT)" , wrapPath  ) )
            elif "$(FLAGS)" in tok : 
                for f in flags: cmd_res.append(f)
            else :
                cmd_res.append(tok)
        
        return cmd_res , list( set( self.swig_flags[:] ) ) , list ( set( [ "-I" + i for i in self.incs] + self.getAutomaticIncludes(dep_prop_list ,"-I")  )) 
    
    def getWrapCommandDescription(self , swigIPath , wrapPath): 
        return swigIPath + " --> " + wrapPath
    
    def getWrapObjCommand( self, wrapPath , owFilePath , dep_prop_list) :
        cmd , ccFlags , includes = noob.cppnode._CppNode.getObjCommand( self , wrapPath , owFilePath , dep_prop_list )
        cmd += [ self.compiler["incs_prefix"] + i for i in python.PYTHON_CONFIG["incs"] ] 
        return cmd , ccFlags , includes
    
    def getWrapObjCommandDescription(self , wrapPath , owFilePath ) : 
        return wrapPath + " --> " + owFilePath
    
    def getLinkCommand(self , objs , targetPath , dep_prop_list ) :
        cmd , ldflags , libs  = noob.cppnode._CppNode.getLinkCommand( self , objs , targetPath , dep_prop_list )
        #cmd += shlex.split( self._compiler["python_libs"] )
        cmd += python.PYTHON_CONFIG["libs"] 
        return cmd , ldflags , libs

    def getLinkCommandDescription(self , objs , targetPath , dep_prop_list ) :
        return targetPath + " <-- " +  str(objs)
        
    def targets(self):
        swiglib = "_" + self.lib_name + swig.SWIG_CONFIG["swig_ext"]
        swigheader = self.lib_name + ".py"
        return [ os.path.join( self.dest_dir , swiglib ) , os.path.join( self.dest_dir , swigheader ) ]
        
        
        
    ## =========================
    ##  Display formatting functions
    ## =========================
    def displaySwigCommand( self , commandList , swigIPath , wrapPath , swigFlags , incs ) :
        if self.swig_display_func != None : self.swig_display_func( commandList , swigIPath , wrapPath , swigFlags , incs )
        else                              : print( " ".join(commandList) )
    
    ## =========================
    ##  Compilation
    ## =========================
    
    def evaluate( self , **kwargs ) :
        
        # invoke start callback if needed 
        if self.start_cb != None : self.start_cb( self )
        
        # override the compiler if needed
        if "compiler" in kwargs.keys() and kwargs["compiler"] != None :
            self.compiler = kwargs["compiler"]
            
        force_reeval = False 
        
        # check if all sources exists 
        for src in self.srcs:
            if not os.path.exists( src ):
                return self._onError( "Missing file " + src )
        
        # generate the list of dependent node's properties
        dep_prop_list = [ node for node in self.nodeSequenceList ]
        
        # built destination and temporary directories
        try :
            if self.tmp_dir  not in ["","."] and not os.path.exists( self.tmp_dir  ) : os.mkdir( self.tmp_dir  )
            if self.dest_dir not in ["","."] and not os.path.exists( self.dest_dir ) : os.mkdir( self.dest_dir )
        except Exception as e:
            errMsg  = "Error while creating directories " + self.tmp_dir
            errMsg += " or " + self.dest_dir + " . Reason : "  + str(e)
            return self._onError( errMsg )


        # generate the wrapper
        forceRelink = False
        objs        = []
        for swigIPath in [ s for s in self.srcs if s.endswith(".swig") or s.endswith(".i") ]:
              
            # generer le wrapper [...]_wrap.cpp et [...].py a partir de l'interface swigIPath si :
            # - le fichier .swig est modifie
            # - un des fichier #include du fichier .swig est modifie
            # - un des fichier %include du fichier .swig est modifie
            # - la commande "swig [...] -o [...] est modifiee
            # - l'un des fichiers destination [...]_wrap.cpp ou [...].py n'existe pas/plus 
            wrapPath              = self.getWrapperPath( swigIPath )
            wrap_cmd , swigFlags , incs  = self.getWrapCommand( swigIPath , wrapPath , dep_prop_list )
            wrapSwigKey           = md5( (swigIPath + self.name() + "_wrap").encode("ascii") ) 
            wrapSwigValue         = md5( (open(swigIPath,'rb').read().decode("latin1") + " ".join(wrap_cmd) + self.getIncMD5(swigIPath, dep_prop_list )).encode("latin1") ) 
            pythonWrapperDestPath = self.getPythonWrapperPathDest( swigIPath )
            
            # test
            wrapperRegenerated  = force_reeval
            wrapperRegenerated |= noob.filetools.getCachedValue(wrapSwigKey) != wrapSwigValue.hexdigest()
            wrapperRegenerated |= not os.path.exists(wrapPath)
            wrapperRegenerated |= not os.path.exists(pythonWrapperDestPath)
            if wrapperRegenerated :
#               print( " ".join(wrap_cmd) )
                self.displaySwigCommand( wrap_cmd , swigIPath , wrapPath , swigFlags , incs )
                #print self.getWrapCommandDescription( swigIPath , wrapPath )
                
                # lancer le sous-process de linking ( Popen lance et est bloquant )
                #process = subprocess.Popen( wrap_cmd , stderr = subprocess.PIPE) # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
                #(stdout ,stderr ) = process.communicate()
                
                # if stdout : print( stdout.decode("ascii") )
                process = subprocess.Popen( wrap_cmd ,  stdout = subprocess.PIPE , stderr = subprocess.PIPE)
                (stdout ,stderr ) = process.communicate()
                
                if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
                returnCode = process.wait()
                
                # checker si erreur de compilation
                #if len(stderr) != 0:
                if returnCode != 0 :
                    sys.stderr.write( stderr.decode( sys.getdefaultencoding() ) )
                    if os.path.exists( wrapPath ) : os.remove( wrapPath )
                    return self._onError( "Swig Error for " + swigIPath + " return Code " + str(process.returncode) )


                # deplacer le fichier .py dans le repertoire destination
                try:
                    if os.path.exists(pythonWrapperDestPath) : os.remove( pythonWrapperDestPath )
                    shutil.move( self.getPythonWrapperPath( swigIPath ) , self.dest_dir )
                except Exception as e:
                    print( str(e) )
                    print( "move " + self.getPythonWrapperPath( swigIPath ) + " to " + self.dest_dir )
                    return self._onError( "Swig Error : move of " + self.getPythonWrapperPath( swigIPath ) + " Failed " )
                
                noob.filetools.setCacheValue( wrapSwigKey, wrapSwigValue )
                forceRelink = True
                wrapperRegenerated = True
            else :
                print( "pas de regeneration du wrapper swig" )
                    
            # verfier que le wrapper.cpp a ete correctement genere
            if not os.path.exists( wrapPath ) : raise RuntimeException(self, "Error " + wrapPath + " doesn't exist")
            
            # generer l'objet [...]_wrap.o correspondant a [...]_wrap.cpp si :
            # - le fichier [...]_wrap.cpp vient d'etre regenere
            # - la commande "g++ [...]_wrap.cpp -o [...]_wrap.o est modifiee
            # - le fichier [...]_wrap.o n'existe pas/plus
            owFilePath   = self.getObjectWrapPath( swigIPath )
            wrap_obj_cmd , ccFlags , incs  = self.getWrapObjCommand( wrapPath , owFilePath , dep_prop_list )
            wrapObjKey   = md5( (wrapPath + self.name() + "_wrapObj").encode("ascii") ) 
            wrapObjValue = md5( (open(wrapPath,'rb').read().decode("latin1") + " ".join(wrap_obj_cmd)).encode("latin1") ) 
            
            # tester
            objWrapperGenerated  = force_reeval
            #objWrapperGenerated |= wrapperRegenerated # deja fait dans wrapObjValue() avec la lecture de _wrap.cpp
            objWrapperGenerated |= noob.filetools.getCachedValue(wrapObjKey) != wrapObjValue.hexdigest()
            objWrapperGenerated |= not os.path.exists(owFilePath)
            if objWrapperGenerated :
#               print( " ".join(wrap_obj_cmd) )
                noob.cppnode._CppNode.displayObjCommand( self , wrap_obj_cmd , wrapPath , owFilePath , ccFlags , incs )
                #print( self.getWrapObjCommandDescription( wrapPath , owFilePath ) )
                
                # lancer le sous-process de compilation de l'objet
                process = subprocess.Popen( wrap_obj_cmd , stdout=subprocess.PIPE , stderr = subprocess.PIPE) 
                (stdout ,stderr ) = process.communicate()
                
                if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
                returnCode = process.wait()
                
                # checker si erreur de compilation
                #if len(stderr) != 0:
                if returnCode != 0 :
                    sys.stderr.write(stderr.decode( sys.getdefaultencoding() ))
                    if os.path.exists( owFilePath ) : os.remove( owFilePath )
                    return self._onError( "Compilation Error for " + owFilePath + " return Code " + str(process.returncode) )


                noob.filetools.setCacheValue( wrapObjKey, wrapObjValue )
                forceRelink = True
            
            # ajouter a la liste des objets compiles
            objs.append( owFilePath )
            
            # verfier que le wrapper.o a ete correctement genere
            if not os.path.exists( owFilePath ) : raise RuntimeException( self , "Error " + owFilePath + " doesn't exist")
            
            
            
            
        for cppPath in [s for s in self.srcs if s.endswith(".cc") or  s.endswith(".cpp") ]:
            # generer l'objet [...].o correspondant a [...].cpp si :
            # - le fichier .cpp a change
            # - la commande "g++ -c [...].cpp -o [...].o" a ete modifiee
            # - le fichier [...].o n'existe pas/plus
            oFilePath = self.getObjectPath ( swigIPath )
            obj_cmd , ccFlags , includes  = self.getObjCommand ( cppPath , oFilePath , dep_prop_list )
            objKey    = md5( oFilePath + self.name() + "_obj") 
            objValue  = md5( open(cppPath,'r').read() + " ".join(obj_cmd) ) 
            
            # test
            objGenerated  = force_reeval
            objGenerated |= noob.filetools.getCachedValue( objKey ) != objValue.hexdigest()
            objGenerated |= not os.path.exists(oFilePath)
            if objGenerated :
                
                noob.cppnode._CppNode.displayObjCommand( self , obj_cmd , cppPath , oFilePath , ccFlags , includes )
#               print( " ".join(obj_cmd) )
                
                # lancer le sous-process de compilation de l'objet
                process = subprocess.Popen( obj_cmd , stdout=subprocess.PIPE, stderr = subprocess.PIPE)
                (stdout ,stderr ) = process.communicate()
                
                if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
                returnCode = process.wait()
                
                # checker si erreur de compilation
                #if len(stderr) != 0:
                if returnCode != 0 :
                    sys.stderr.write(stderr)
                    if os.path.exists( oFilePath ) : os.remove( oFilePath )
                    return self._onError( "Compilation Error for " + oFilePath + " return Code " + str(process.returncode) )


                noob.filetools.setCacheValue( objKey, objValue )
                forceRelink = True
            
            # ajouter a la liste des objets compiles
            objs.append( oFilePath )
            
            # verfier que le wrapper.o a ete correctement genere
            if not os.path.exists( oFilePath ) : raise RuntimeException( self , "Error " + oFilePath + " doesn't exist")


        # relancer le linking si:
        # - un des obj vient d'etre regenere
        # - la commande de link a change
        # - le .so n'existe pas/plus
        
        # si la lib dynamique n'existe pas, forcer un relink
        targetPath = self.targets()[0]
        if not os.path.exists( targetPath ) :
            forceRelink = True
        
        # si les options de linking ont change, forcer le relink
        linkKey   = md5( (self.name() + "_link").encode("ascii") ) 
        linkValue = md5( (" ".join(self.getLinkCommand( objs , targetPath , dep_prop_list )[0]) ).encode("latin1") ) 
        if force_reeval or noob.filetools.getCachedValue( linkKey ) != linkValue.hexdigest() :
            forceRelink = True
        
        # verifier qu'aucune librairie dont depend ce noeud swig n'a pas ete modifie
        dependLibs = [ p.targets()[0] for p in dep_prop_list if p.nodeType in [ "Dynamic Library" , "Static Library" ] ]
        dependLibs = list(set(dependLibs))
        if not forceRelink : 
            # verifier leur md5 
            for libFile in dependLibs :
                objKey   = md5( libFile + self.name() )
                objValue = md5( open(libFile,'r').read() )
                if noob.filetools.getCachedValue(objKey) != objValue.hexdigest() :
                    forceRelink = True
                    break
                
        
        # si les objets sont up-to-date  quitter
        if not forceRelink :
            return self._onUpToDate( ) 
        
        # si on relink, supprimer la target au prealable, comme ca 
        # en cas de kill du thread de compilation, la target sera relinkee
        # au prochain coup
        try :
            if os.path.exists( targetPath ) : os.remove( targetPath )
        except Exception as e:
            return self._onError( "Deletion Error of " + targetPath +" : Cause " + str(e) )
        
        # generer la commande de linking
        command , ldFlags , libs = self.getLinkCommand( objs , targetPath , dep_prop_list )
        noob.cppnode._CppNode.displayLinkCommand( self , command , targetPath , ldFlags , libs )
#       print( " ".join(command) )

        # lancer le sous-process de linking ( Popen lance et est bloquant )
        process = subprocess.Popen( command , stderr = subprocess.PIPE) # , stdout=subprocess.PIPE, stderr=subprocess.STDOUT )
        (stdout ,stderr ) = process.communicate()
        
        if stdout : print( stdout.decode( sys.getdefaultencoding() ) )
        returnCode = process.wait()
        
        # checker si erreur de compilation
        #if len(stderr) != 0:
        if returnCode != 0 :
            sys.stderr.write(stderr.decode( sys.getdefaultencoding() ))
            if os.path.exists(targetPath) : os.remove(targetPath)
            return self._onError( "Compilation Error on " + targetPath + " return Code " + str(process.returncode) )

        # mettre en cache 
        noob.filetools.setCacheValue( linkKey, linkValue )
        
        # flager les lib
        for libFile in dependLibs :
            objKey   = md5( ( libFile + self.name() ) .encode("ascii") )
            objValue = md5( open(libFile,'rb').read() )
            noob.filetools.setCacheValue( objKey, objValue )
                
        
        # verfier que le wrapper.cpp a ete correctement genere
        if not os.path.exists( targetPath ) : raise RuntimeException( "Error " + targetPath + " doesn't exist")
        
        # creer le fichier __init__.py si besoin dans le repertoire destination
        if not os.path.exists( os.path.join( self.dest_dir , "__init__.py" ) ) : open( os.path.join( self.dest_dir , "__init__.py" ) , 'a').close()
        
        # retourner le nom de l'executable/lib genere
        return self._onBuilt( )

    
    
    
    
    
    
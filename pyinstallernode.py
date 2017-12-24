import noob.node
from noob         import filetools
import os
import sys
import subprocess
import shutil
import inspect
import platform
import datetime


class PyInstallerNode( noob.node.Node ) :
    
    def __init__( self , **params ):
        
        noob.node.Node.__init__( self ) 
        self.nodeType = "PyInstaller Node"
        
        self.app_name         = ""
        self.dest_dir         = "."
        self.script_path      = None 
        self.tmp_dir          = "."
        self.flags            = []
        self.icon_path        = None
        self.environment      = os.environ
        self.datas            = {}
        self.pyinstaller_path = ""
        
        # macosx bundle options
        self.use_macdeployqt     = False
        self.bundle_version      = ""
        self.bundle_manufacturer = ""
        self.plist_template_path = ""
        
        # dict of parameters allowed 
        self.parms_allowed.update( { 
            "app_name"            : "Name of the target App" , 
            "dest_dir"            : "Destination directory, where the executable/library will be built. ex : '/my/dest/dir'"     , 
            "tmp_dir"             : "Temporary directory, where temporary objects (.o) will be built. ex : '/my/tmp/dir' "       , 
            "script_path"         : "Path to the main script to embedd in an App"                                                , 
            "tmp_dir"             : "Temporary directory, where temporary objects (.o) will be built. ex : '/my/tmp/dir' "       , 
            "flags"               : "Flags to pass to PyInstaller. ex : [ '-F' , '-w' , '-d' ]"                                  , 
            "icon_path"           : "Temporary directory, where temporary objects (.o) will be built. ex : '/my/tmp/dir' "       , 
            "bundle_version"      : "Version of the bundle ex : '1.5.3' "                                                        , 
            "bundle_manufacturer" : "Manufacturer of the bundle ex : 'My Company'"                                               , 
            "plist_template_path" : "Path to plist template (Mac only)"                                                          ,
            "environment"         : "Custom environment: Pyinstaller uses to locate modules/lib ( default : os.environ )"        ,
            "datas"               : "Extra datas to add to the bundle. ex : { '/path/to/myFile' : './relative/path/in/bundle/' }",
            "use_macdeployqt"     : "Run macdeployqt tool as a post-process (Mac only). macdeployqt must be in current path "    ,
            "pyinstaller_path"    : "Full path to pyinstaller.py"
        } )
        
        # get the module's path to convert relative paths to absolute
        myFilename             = inspect.getframeinfo( inspect.currentframe().f_back )[0]
        params["calling_path"] = os.path.split(myFilename)[0]
        if params["calling_path"] == "" : params["calling_path"] = "."
        self._setParameters( params )
                        
    def name( self )  :
        return self.app_name
    
    def help( self ) :
        self.displayAllowedParameters()
        
    def info( self ) :
        print("--- Infos for node ", self )
        for k,v in sorted( self.parms_allowed.items() ) : 
            print( '  {:<20}'.format(k) , ":" , str( getattr( self , k ) )  ) 
        print()
        
    def build( self ) :
        noob.node.Node.execute( self )
    
    def clean( self ):
        
        # generate target app name
        targetPath = os.path.join( self.dest_dir , self.app_name )
        
        # remove previous built bundles
        if os.path.exists( targetPath ) : 
            if os.path.exists( targetPath ) : 
                print( "Deleting : '" + targetPath + "'" )
                shutil.rmtree(targetPath)
        
        if "Darwin" in platform.platform() :
            # remove also the .app on Mac
            appDir = os.path.join( self.dest_dir , self.app_name + ".app" ) 
            if os.path.exists( appDir ) : 
                print( "Deleting : '" + appDir + "'" )
                shutil.rmtree( appDir )
        
        # remove previous tmp directory
        tmpDir = os.path.join( self.tmp_dir , self.app_name )
        if os.path.exists( tmpDir ) : 
            print( "Deleting : '" + tmpDir + "'" )
            shutil.rmtree( tmpDir )
            
    
    def cleanAll( self ) :
        for node in self.getDependentList() : 
            node.clean()
            
        self.clean()
    
        
    def _setParameters( self , params ) :
        
        # check if all parameters are valid
        for k,v in params.items() :
            if k not in list( self.parms_allowed.keys()) + ["calling_path"] :
                self.displayAllowedParameters()
                raise RuntimeError( "\"" + k + "\" parameter is not defined for "+ self.name() ) 
        
        # setting of parameters
        for k,v in params.items() :
            # always make paths absolute, based on the current calling path
            if k in [ "srcs" ] : 
                setattr( self , k , noob.filetools.makeAbsolutePath( params["calling_path"] , params[k] ) )
            else : 
                setattr( self , k , v )
                
    
    def displayAllowedParameters( self )  :
        print("\n--- Allowed parameters for node '" + str( self.name() ) + "'" ) 
        for k,v in sorted( self.parms_allowed.items() ) : 
            print( '  {:<11}'.format(k) , ":" , v ) 
        print("\n")
        
    
    ## =========================
    ##  Compilation
    ## =========================
    
    def _onError( self , errMsg ):
        
        sys.stderr.write( errMsg + "\n" )
        sys.stderr.flush()
        
        displayMsg  = "[ERROR] ProcessNode : \"" + str( self.name() ) +"\" build failed"
        displayMsg += " : \n   --> " + errMsg
        sys.stderr.write( displayMsg + "\n\n" )
        sys.stderr.flush()
        
        self.status  = "Error"
        self.message = displayMsg + " : " + errMsg
        
        return self
    
        
    def _onBuilt( self , startTime ):
        hours, remainder = divmod( (datetime.datetime.now() - startTime).seconds , 3600)
        minutes, seconds = divmod(remainder, 60)
        
        msg = "[SUCCESS] PyInstallerNode : \"" + str( self.name() ) +"\" built successfully"
        msg += " in " + "%.2dh:%.2dm:%.2ds"%(hours, minutes,seconds)
        
        print( msg + "\n" )
        self.status  = "Built"
        self.message = msg
        return self
    
    def _onUpToDate( self , startTime ):
        hours, remainder = divmod( (datetime.datetime.now() - startTime).seconds , 3600)
        minutes, seconds = divmod(remainder, 60)
        
        msg = "PyInstallerNode : \"" + str( self.name() ) +"\" is up to date " 
        msg += "("+ "%.2dh:%.2dm:%.2ds"%(hours, minutes,seconds) + ")"
        
        print( msg + "\n" )
        self.status  = "Up-To-Date"
        self.message = msg
        return self
        
    
    def getPyinstallerCmd( self ):
        
        # generate the pyinstaller main command
        buildCmd  = [ 
            ["python.exe"] if platform.system() == "Windows" else "python" , "-u" , 
            self.pyinstaller_path                                                 ,
            self.script_path                                                      , 
            "--name="     + self.app_name                                         ,
            "--distpath=" + self.dest_dir                                         ,
            "--workpath=" + self.tmp_dir                                          ,
            *self.flags
        ]
        
        # add extra-datas if needed
        for filePath, relativePath in self.datas.items() :
            buildCmd += ["--add-data" , filePath + ":" + relativePath ]
            
        # check if icon exists
        if self.icon_path :
            if not os.path.exists( self.icon_path ) :
                sys.stderr.write( "WARNING : '" + self.icon_path + "' icon path not found\n" )
            else :
                buildCmd += [ "-i", self.icon_path ]
        
        return buildCmd
        
        
    def evaluate( self , **kwargs ) :
        
        # record starting time
        startTime = datetime.datetime.now()
        
        # check if extra data files exist
        for dataPath,targetPath in self.datas.items() :
            if not os.path.exists( dataPath ):
                return self._onError( "Missing extra data : " + dataPath )
        
        try :
            
            # check if the main script exists
            if not os.path.exists( self.script_path ):
                return self._onError( "Missing file : " + self.script_path )
            
            # create the destination directory
            try :
                if self.dest_dir not in ["","."] and not os.path.exists( self.dest_dir ): 
                    os.mkdir( self.dest_dir )
            except Exception as e:
                errMsg  = "Error while creating destination directory : '" + self.dest_dir + "'"
                errMsg += " : "  + str(e)
                return self._onError( errMsg )
            
            # generate the target path
            targetPath = os.path.join( self.dest_dir , self.app_name )
            
            # remove previous built bundles
            if os.path.exists( targetPath ) : 
                if os.path.exists( targetPath ) : 
                    print( "Deleting : '" + targetPath + "'" )
                    shutil.rmtree(targetPath)
            
            if "Darwin" in platform.platform() :
                # remove also the .app on Mac
                appDir = os.path.join( self.dest_dir , self.app_name + ".app" ) 
                if os.path.exists( appDir ) : 
                    print( "Deleting : '" + appDir + "'")
                    shutil.rmtree( appDir )
            
            # remove previous tmp directory
            tmpDir = os.path.join( self.tmp_dir , self.app_name )
            if os.path.exists( tmpDir ) : 
                print( "Deleting : '" + tmpDir + "'" )
                shutil.rmtree( tmpDir )
            
            # launch pyinstaller in a sub-process
            packagerCmd = " ".join( self.getPyinstallerCmd( ) )
            print( packagerCmd )
            process = subprocess.Popen( packagerCmd , shell = True , stdout = subprocess.PIPE , stderr = subprocess.PIPE  , env = self.environment ) 
            ( stdout , stderr ) = process.communicate()
            print("-------------------------------")
            if stdout : print( stdout.decode("ascii") )
            if stderr : print( stderr.decode("ascii") )
            print("-------------------------------")
            
            # return immediately if command failed
            if process.returncode != 0:
                sys.stderr.write( str(stderr) ) 
                sys.stderr.flush()
                return self._onError( "Build Error : pyinstaller  return Code " + str(process.returncode) )
            
            # on macsox, some extra steps are sometimes needed
            if "Darwin" in platform.platform() :
                appPath = os.path.join( self.dest_dir , self.app_name + ".app" ) 
                
                # if this app has no lib linking to Qt, just use the qt.conf
                # in located in ./Contents/Resources provided by pyinstaller. 
                # Otherwise , you have to use macdeployqt to embed Qt libs
                if not self.use_macdeployqt :
                    if os.path.exists( appPath ) :
                        f = open( os.path.join( appPath, "Contents" , "Resources" ,"qt.conf") , "w" )
                        f.close()
                        
                else :
                    
    #               macdeployqtCmd = [ "/Users/antoine/dev/lib/qt/4.8.6/lib/bin/macdeployqt"  , str( appPath ) ] #, "--dmg"
                    macdeployqtCmd = [ "macdeployqt" , str( appPath ) ] #, "--dmg"
                    print( " ".join( macdeployqtCmd ) )
                    process = subprocess.Popen( macdeployqtCmd , stdout = subprocess.PIPE , stderr = subprocess.PIPE) 
                    ( stdout , stderr ) = process.communicate()
                        
                    if stdout : print( stdout.decode("ascii") )
                    if stderr : print( stderr.decode("ascii") )
                    if process.returncode != 0:
                        sys.stderr.write(stderr)
                        return self._onError( "Build Error : pyinstaller  return Code " + str(process.returncode) )
                
                
                # use a provided Info.plist
                if self.plist_template_path :
                    
                    # copy the provided Info.plist to the app directory
                    targetTemplatePath = os.path.join( appPath , "Contents" ,"Info.plist")
                    shutil.copy( self.plist_template_path , targetTemplatePath )
                    
                    print("Copy plist_template_path" , "-->" , targetTemplatePath )
                    
                    # read this Info.plist
                    with open( self.plist_template_path ) as infoFile :
                        infoText = infoFile.read()
                        
                    # replace keywords with those provided
                    appInfos = { 
                        "APP_VERSION"    : self.bundle_version                 ,
                        "APP_NAME"       : self.app_name                       ,
                        "ICON_FILE"      : os.path.basename( self.icon_path )  ,
                        "APP_IDENTIFIER" : "com." + self.bundle_manufacturer + "." +  self.app_name
                    }
                    infoText = infoText.format( **appInfos )
                    
                    # rewrite into the Info.plist located in the bundle
                    with open( targetTemplatePath , "w+") as infoFile :
                        infoFile.write( infoText )
                
        except Exception as e :
            return self._onError( "Build Error : pyinstaller exception " + str(e) )
            
        # everything has been successfully built , we can leave now 
        return self._onBuilt( startTime )

    
    def status(self):
        return self.status()


    
    
    
    
    
    
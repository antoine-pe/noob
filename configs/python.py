import os , platform , sys , subprocess

# automatically detect the current Python version
process = subprocess.Popen( ["python","--version"] ,  stdout = subprocess.PIPE , stderr = subprocess.PIPE )
( stdout , stderr ) = process.communicate()
process.wait()

if (sys.version_info.major,sys.version_info.minor) == (2,7) : version = str( stderr )[9:]
else                                                        : version = str( stdout )[9:]
    
major       = version[0]
minor       = version[2]
patch       = version[4]
majDotMinor = major + "." + minor

print( "Python : v." + major + "." + minor + "." + patch )

if "Darwin" in platform.platform():
    
    PYTHON_CONFIG = {
#       "incs" : [ "/System/Library/Frameworks/Python.framework/Versions/" + majDotMinor + "/include/python" + majDotMinor  ] , 
#       "libs" : [ "/System/Library/Frameworks/Python.framework/Versions/" + majDotMinor + "/Python"                        ] 
        
        "incs" : [ "/Library/Frameworks/Python.framework/Versions/3.5/include/python3.5m" ] , 
        "libs" : [ "/Library/Frameworks/Python.framework/Versions/3.5/Python" ] #"/System/Library/Frameworks/Python.framework/Versions/" + majDotMinor + "/Python"                        ] 
    }
    
    # "libs" : [ "-L/System/Library/Frameworks/Python.framework/Versions/2.7/lib" , "-lpython2.7" ] # pas sur ... 
    
    
    
    
elif "Windows" in platform.platform():
    #if   compiler.COMPILER_CONFIGS[ "msvc" ][ "machine" ] == "32" : pythonDirPath = "C:/Python27"
    #elif compiler.COMPILER_CONFIGS[ "msvc" ][ "machine" ] == "64" : pythonDirPath = "C:/Python271_64"
    
#   if major == "2" :
#       if   compiler.COMPILER_CONFIG[ "machine" ] == "32" : pythonDirPath = "C:/Python27"
#       elif compiler.COMPILER_CONFIG[ "machine" ] == "64" : pythonDirPath = "C:/Python271_64"
#   elif major == "3" :
    if   compiler.COMPILER_CONFIG[ "machine" ] == "32" : pythonDirPath = "C:/Python" + major + "_" + minor
    elif compiler.COMPILER_CONFIG[ "machine" ] == "64" : pythonDirPath = "C:/Python" + major + minor +"_64" # a affiner pour le 64 bits ( ajouter "_64bits" ? )
    
    print("python DIR" ,pythonDirPath )
    
    PYTHON_CONFIG = {
        "lib_name" : "python"                            ,
        "incs"     : [ os.path.join( pythonDirPath , "include" )                             ] , 
        "libs"     : [ os.path.join( pythonDirPath , "libs/python" + major + minor + ".lib") ] 
    }
    
    
#   if version == "2.7.6" :
#       PYTHON_CONFIG = {
#           "lib_name" : "python"                            ,
#           "incs"     : [ os.path.join( pythonDirPath , "include" ) ] , 
#           "libs"     : [ os.path.join( pythonDirPath , "libs/python27.lib") ] #"C:/Python27/libs/python27.lib" ] 
#       }
#   elif version == "2.7.1" :
#       PYTHON_CONFIG = {
#           "lib_name" : "python"                            ,
#           "incs"     : [ os.path.join( pythonDirPath , "include" ) ] , 
#           "libs"     : [ os.path.join( pythonDirPath , "libs/python27.lib") ] #"C:/Python27/libs/python27.lib" ] 
#       }
#   elif version == "2.6.4":
#       PYTHON_CONFIG = {
#           "lib_name" : "python"                            ,
#           "incs"     : [ "C:/Program Files/Autodesk/Maya2012/include/python2.6" ] , 
#           "libs"     : [ "C:/Program Files/Autodesk/Maya2012/lib/python26.lib"  ] 
#       }
#    
#   elif version == "3.4.2":
#       PYTHON_CONFIG = {
#           "lib_name" : "python"                            ,
#           "incs"     : [ os.path.join( pythonDirPath , "include" )          ] , 
#           "libs"     : [ os.path.join( pythonDirPath , "libs/python34.lib") ] 
#       }
        
        

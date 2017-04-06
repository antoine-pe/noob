import subprocess , sys

# This file registers all well-known compilers in a single dict with the format
# KNOWN_COMPILERS[ OSName ][ compilerName_bitness ] ( ex KNOWN_COMPILERS["windows"]["msvc2008_32"] )
# can be used outside to switch to another compiler configuration
KNOWN_COMPILERS = {
    "windows" : {} ,
    "macOS"   : {} ,
    "linux"   : {} 
}


## =========================
##  Windows compilers
## =========================

# define usual msvc flags
common_compiler_windows_flags = [
    
    # GENERAL OPTIONS
    "/nologo"                    , # hide compiler intro message
    "/EHsc"                      ,
    
    # WINDOWS PLATFORM DEFINITION
    "/D_WINDOWS"                 ,
    "/DWIN32"                    ,
    "/D__WIN32__"                ,
    "/D_WIN32"                   , # always defined by cl.exe   
   
    # define how <windows.h> is included ( http://msdn.microsoft.com/en-us/library/windows/desktop/aa383745%28v=vs.85%29.aspx )
    "/DWIN32_LEAN_AND_MEAN"      , # speed up the compilation by removing not so commonly used headers (Crypto,dde,rpc,shell,winsockets)
    "/D\"_WIN32_WINNT=0x0601\""  , # definition of the windows version : 0x0502 : xp , 0x0600 :vista, 0x0601 : seven 
    "/D\"WINVER=0x0601\""        , # definition of the windows version (idem)
    "/DUNICODE"                  , # unicode handling
    "/D_UNICODE"                 , # unicode handling bis ( useful because of non uniform naming convention )
    
    # WARNING OPTIONS
    "/D_CRT_SECURE_NO_DEPRECATE"  , # remove security warnings (ex : strcpy est non safe, strcpy_s plutot)
    "/D_CRT_NONSTDC_NO_DEPRECATE" , # remove deprecation warnings (ex : chdir en _chdir)
    "/D_D_CRT_NONSTDC_NO_WARNINGS", # remove POSIX and C runtime warnings 
    "/W3"                         , # set a high level of warnings
    
    # COMPILATION OPTIONS
    "/FC"                        , # display short compilation error messages 
    "/Gy"                        , # don't embed unused functions (with conjonction of /OPT:REF for the linker )
    "/errorReport:none"          , # don't send crash report ( otherwise a prompt is showing up )
    "/Zc:wchar_t"                ,
    
]

# record different msvc versions with the name "mvsc[year]_[bitness]".
versMap = {
    "msvc2008" : { "vsVersion" : "9.0"  , "msvcDefine" : "/D_MSC_VER=1500" } ,
    "msvc2012" : { "vsVersion" : "11.0" , "msvcDefine" : "/D_MSC_VER=1700" } ,
    "msvc2013" : { "vsVersion" : "12.0" , "msvcDefine" : "/D_MSC_VER=1800" } ,
    "msvc2015" : { "vsVersion" : "14.0" , "msvcDefine" : "/D_MSC_VER=1900" } 
}

for msvcVer in [ "msvc2008" , "msvc2012" , "msvc2013" , "msvc2015" ] : 
    
    for bitness in [ "32" , "64" ] :
        
        KNOWN_COMPILERS["windows"][ msvcVer + "_" + bitness ] = {
            "bitness"          : bitness                                                            ,
            "config_name"      : msvcVer + "_" + bitness                                            ,
            "init_script"      : [ "C:/Program Files (x86)/Microsoft Visual Studio " + versMap[msvcVer]["vsVersion"] + "/VC/vcvarsall.bat", "x86" if bitness == "32" else "x64" ]  ,
            "c++_obj_cmd"      : "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + [ versMap[msvcVer]["msvcDefine"] ] ) + " /TP" , 
            "c_obj_cmd"        : "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + [ versMap[msvcVer]["msvcDefine"] ] ) + " /TC" , 
            "dynamic_link_cmd" : "link.exe /NOLOGO /DLL $(IN) /OUT:$(OUT) $(FLAGS)"                 ,
            "static_link_cmd"  : "lib.exe /NOLOGO /OUT:$(OUT) $(IN) $(FLAGS)"                       ,
            "exe_link_cmd"     : "link.exe /NOLOGO $(IN) /OUT:$(OUT) $(FLAGS)"                      ,
            "incs_prefix"      : "-I"                                                               ,
        }
        
        
        

## =========================
##  MacOS compilers
## =========================
KNOWN_COMPILERS["macOS"]["g++_64"] = {
    "bitness"                  : "64"                                                  ,
    "config_name"              : "g++ MacOS"                                           ,
    "c++_obj_cmd"              : "g++ -c $(IN) -o $(OUT) $(FLAGS)"                     ,
    "c_obj_cmd"                : "gcc -c $(IN) -o $(OUT) $(FLAGS)"                     ,
    "dynamic_link_cmd"         : "g++ $(IN) -o $(OUT) $(FLAGS) -headerpad_max_install_names -arch x86_64 -single_module -dynamiclib",
    "static_link_cmd"          : "ar qcs $(OUT) $(IN) $(FLAGS)"                        , # "ar rcs $(OUT) $(IN) $(FLAGS)",
    "exe_link_cmd"             : "g++ $(IN) -o $(OUT) $(FLAGS)"                        ,
    "incs_prefix"              : "-I"                                                  ,
}


## =========================
##  Linux compilers
## =========================
KNOWN_COMPILERS["linux"]["g++_64"] = {
    "machine"                  : "64"                                                  ,
    "config_name"              : "gcc"                                                 ,
    "c++_obj_cmd"              : "g++ -c -fPIC $(IN) -o $(OUT) $(FLAGS)"               ,
    "c_obj_cmd"                : "g++ -c $(IN) -o $(OUT) $(FLAGS)"                     ,
    "dynamic_link_cmd"         : "g++ -shared $(IN) -o $(OUT) $(FLAGS)"                ,
    "static_link_cmd"          : "ar qcs $(OUT) $(IN) $(FLAGS)"                        , # "ar rcs $(OUT) $(IN) $(FLAGS)",
    "exe_link_cmd"             : "g++ -lstdc++ $(IN) -o $(OUT) $(FLAGS)"               ,
    "incs_prefix"              : "-I"                                                  ,
}


# now set the DETECTED_COMPILER variable depending on the current compiler 
# and set the DETECTED_PLATFORM variable collecting various informations
# if automatic detection fails, make Bud happy ;)
DETECTED_COMPILER = None
DETECTED_PLATFORM = None

if sys.platform == "win32" : 
    
    # check if the compiler is 32 or 64 bits
    process             = subprocess.Popen( "cl.exe" ,  stdout = subprocess.PIPE , stderr = subprocess.PIPE )
    ( stdout , stderr ) = process.communicate()
    returnCode          = process.wait()
    
    # check architecture used by the current compiler
    bitness = "undetected"
    if   "x64"   in str( stderr )                           : bitness = "64" 
    elif "80x86" in str( stderr ) or "x86" in str( stderr ) : bitness = "32"
    print( "Windows : " + bitness + "-bits PLATEFORM" )
    
    # set the msvc version according to the answer
    msvcYear = "undetected" 
    if   "Version 15.00" in str( stderr ) : msvcYear = "2008"
    elif "Version 17.00" in str( stderr ) : msvcYear = "2012"
    elif "Version 18.00" in str( stderr ) : msvcYear = "2013"
    elif "Version 19.00" in str( stderr ) : msvcYear = "2015"
    print( "Visual Studio " + msvcYear + " " + bitness + "bits" )
    
    DETECTED_COMPILER = KNOWN_COMPILERS["windows"]["msvc" + msvcYear + "_" + bitness ]
    DETECTED_PLATFORM = {
        "obj_suffix"     : ".obj" ,
        "dynamic_suffix" : ".dll" ,
        "static_suffix"  : ".lib" ,
        "exe_suffix"     : ".exe" 
    }
    
    
elif sys.platform == "darwin" : 
    print( "Mac OS : 64-bits PLATEFORM" )
    print( "LLVM   : g++" )
    DETECTED_COMPILER = KNOWN_COMPILERS["macOS"]["g++_64"]
    DETECTED_PLATFORM = {
        "obj_suffix"     : ".o"     ,  
        "dynamic_suffix" : ".dylib" , 
        "static_suffix"  : ".a"     ,
        "exe_suffix"     : ""       
    }


elif sys.platform == "linux" : 
    print( "Linux    : 64-bits PLATEFORM" )
    print( "Compiler : gcc" )
    DETECTED_COMPILER = KNOWN_COMPILERS["linux"]["g++_64"]
    DETECTED_PLATFORM = {
        "obj_suffix"     : ".o"  ,  
        "dynamic_suffix" : ".so" , 
        "static_suffix"  : ".a"  ,
        "exe_suffix"     : ""       
    }
    
else :
    sys.stderr.write( "[ERROR] Platform '" + sys.platform + "' unsupported\n\n" )
    
if DETECTED_COMPILER == None : 
    sys.stderr.write( "[WARNING] Compiler auto-detection failed\n\n" )
    
    

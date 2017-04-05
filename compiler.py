import os , subprocess , sys

# This file registers all well-known compilers in a single dict
# each key is the name of the compiler ( eg "mscv2008" , "msvc2015" , "g++" , ... ) 


KNOWN_COMPILERS = {}


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
    
    # "/D_WIN32_WINNT_WIN7"        , # definition of the windows version (idem)
    # "/DNOMINMAX"                , # disable the use of min() and max() macro defined in <windows/h>  
    # "/D_CRT_RAND_S"             , # enable the use of rand_s() , a safe integer random generator
    # "/D\"_HAS_TR1=1\""          , # enable/disable headers conforming the TR1 extensions
    # "/D\"_HAS_EXCEPTIONS=0\""   , # enable the use of exceptions and the header  <exceptions.h>
     
    # WARNING OPTIONS
    "/D_CRT_SECURE_NO_DEPRECATE"  , # remove security warnings (ex : strcpy est non safe, strcpy_s plutot)
    "/D_CRT_NONSTDC_NO_DEPRECATE" , # remove deprecation warnings (ex : chdir en _chdir)
    "/D_D_CRT_NONSTDC_NO_WARNINGS", # remove POSIX and C runtime warnings 
    "/W3"                         , # set a high level of warnings
    # /wdxxxx                      , # xxxx is the level number to activate
    # "/w"                         , # remove all warnings ( note : w is lowercase )
    
    # COMPILATION OPTIONS
    "/FC"                        , # display short compilation error messages 
    "/Gy"                        , # don't embed unused functions (with conjonction of /OPT:REF for the linker )
    "/errorReport:none"          , # don't send crash report ( otherwise a prompt is showing up )
    "/Zc:wchar_t"                ,
    
    # "/RTCs"                     ,    
    # "/GS" 
    # "/TP"                       , # file are written in c++ ( as opposed to c files , activated with the /TC option ) 
    # "/Zi"                       , # generate symbols in the .pdb
    # "/RTC1"                     , # check memory allocation and numerical overflow 
    # "/MD","/MT"                 , # generate dynamic library ( as opposed to static library with /MT option )
    # "/GR-"                      , # enable the rtti with a '+' or disable it with a '-'
    # "/MP"                       , # multithread compilation ( equivalent of -j5 for make )
    # "/Zc:wchar_t-"              , # disable the native type wchar_t, defined by default
    # "/FdProg.pdb                , # set the name of the final .pdb ( VCx0.pdb is the defaut name ) 
    # "/Oy-"                      , # frame pointer omission optimization :  if used with the /Zi option ( = .pdb generation ) then /Oy- is mandatory
]


# Visual Studio 2008 - template for all other versions
KNOWN_COMPILERS["msvc2008"] = {
    "config_name"      : "msvc2008"                                                         ,
    "init_script"      : [ "C:/Program Files (x86)/Microsoft Visual Studio 9.0/VC/vcvarsall.bat", "x64" ]  ,
    "machine"          : "32"                                                               ,
    "c++_obj_cmd"      : "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1500" ] ) + " /TP" , 
    "c_obj_cmd"        : "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1500" ] ) + " /TC" , 
    "dynamic_link_cmd" : "link.exe /NOLOGO /DLL $(IN) /OUT:$(OUT) $(FLAGS)"                 ,
    "static_link_cmd"  : "lib.exe /NOLOGO /OUT:$(OUT) $(IN) $(FLAGS)"                       ,
    "exe_link_cmd"     : "link.exe /NOLOGO $(IN) /OUT:$(OUT) $(FLAGS)"                      ,
    "obj_suffix"       : ".obj"                                                             ,  
    "dynamic_suffix"   : ".dll"                                                             ,
    "static_suffix"    : ".lib"                                                             ,
    "exe_suffix"       : ".exe"                                                             ,
    "incs_prefix"      : "-I"                                                               ,
}

# Visual Studio 2012
KNOWN_COMPILERS["msvc2012"] = KNOWN_COMPILERS["msvc2008"].copy() 
KNOWN_COMPILERS["msvc2012"]["config_name"] = "msvc2012"
KNOWN_COMPILERS["msvc2012"]["init_script"] = [ "C:/Program Files (x86)/Microsoft Visual Studio 11.0/VC/vcvarsall.bat", "x64" ]
KNOWN_COMPILERS["msvc2012"]["c++_obj_cmd"] = "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1700" ] ) + " /TP" 
KNOWN_COMPILERS["msvc2012"]["c_obj_cmd"  ] = "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1700" ] ) + " /TC" 

# Visual Studio 2013
KNOWN_COMPILERS["msvc2013"] = KNOWN_COMPILERS["msvc2008"].copy() 
KNOWN_COMPILERS["msvc2013"]["config_name"] = "msvc2013"
KNOWN_COMPILERS["msvc2013"]["init_script"] = ["C:/Program Files (x86)/Microsoft Visual Studio 12.0/VC/vcvarsall.bat",  "x64" ]
KNOWN_COMPILERS["msvc2013"]["c++_obj_cmd"] = "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1800" ] ) + " /TP" 
KNOWN_COMPILERS["msvc2013"]["c_obj_cmd"  ] = "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1800" ] ) + " /TC" 

# Visual Studio 2015
KNOWN_COMPILERS["msvc2015"] = KNOWN_COMPILERS["msvc2008"].copy()
KNOWN_COMPILERS["msvc2015"]["config_name"] = "msvc2015"
KNOWN_COMPILERS["msvc2015"]["init_script"] = [ "C:/Program Files (x86)/Microsoft Visual Studio 14.0/VC/vcvarsall.bat", "x64" ]
KNOWN_COMPILERS["msvc2015"]["c++_obj_cmd"] = "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1900" ] ) + " /TP" 
KNOWN_COMPILERS["msvc2015"]["c_obj_cmd"  ] = "cl.exe /c $(IN) -Fo$(OUT) $(FLAGS) " + " ".join( common_compiler_windows_flags + ["/D_MSC_VER=1900" ] ) + " /TC" 


# MacOS g++
KNOWN_COMPILERS["g++ MacOS"] = {
    "machine"                  : "64"                                                  ,
    "config_name"              : "g++ MacOS"                                           ,
    "c++_obj_cmd"              : "g++ -c $(IN) -o $(OUT) $(FLAGS)"                     ,
    "c_obj_cmd"                : "gcc -c $(IN) -o $(OUT) $(FLAGS)"                     ,
    "dynamic_link_cmd"         : "g++ $(IN) -o $(OUT) $(FLAGS) -headerpad_max_install_names -arch x86_64 -single_module -dynamiclib",
    "static_link_cmd"          : "ar qcs $(OUT) $(IN) $(FLAGS)"                        , # "ar rcs $(OUT) $(IN) $(FLAGS)",
    "exe_link_cmd"             : "g++ $(IN) -o $(OUT) $(FLAGS)"                        ,
    "obj_suffix"               : ".o"                                                  ,  
    "dynamic_suffix"           : ".dylib"                                              , 
    "static_suffix"            : ".a"                                                  ,
    "exe_suffix"               : ""                                                    ,
    "incs_prefix"              : "-I"                                                  ,
}


KNOWN_COMPILERS["gcc"] = {
    "machine"                  : "64"                                                  ,
    "config_name"              : "gcc"                                                 ,
    "c++_obj_cmd"              : "g++ -c -fPIC $(IN) -o $(OUT) $(FLAGS)"               ,
    "c_obj_cmd"                : "g++ -c $(IN) -o $(OUT) $(FLAGS)"                     ,
    "dynamic_link_cmd"         : "g++ -shared $(IN) -o $(OUT) $(FLAGS)"                ,
    "static_link_cmd"          : "ar qcs $(OUT) $(IN) $(FLAGS)"                        , # "ar rcs $(OUT) $(IN) $(FLAGS)",
    "exe_link_cmd"             : "g++ -lstdc++ $(IN) -o $(OUT) $(FLAGS)"               ,
    "obj_suffix"               : ".o"                                                  ,  
    "dynamic_suffix"           : ".so"                                                 , 
    "static_suffix"            : ".a"                                                  ,
    "exe_suffix"               : ""                                                    ,
    "incs_prefix"              : "-I"                                                  ,
}


KNOWN_COMPILERS["clang++"] = {
    "machine"                  : "64"                                                  ,
    "config_name"              : "clang++"                                             ,
    "c++_obj_cmd"              : "clang++ -c $(IN) -o $(OUT) $(FLAGS)"                 ,
    "c_obj_cmd"                : "clang -c $(IN) -o $(OUT) $(FLAGS)"                   ,
    "dynamic_link_cmd"         : "clang++ $(IN) -o $(OUT) $(FLAGS) -headerpad_max_install_names -arch x86_64 -single_module -dynamiclib",
    "static_link_cmd"          : "ar qcs $(OUT) $(IN) $(FLAGS)"                        ,
    "exe_link_cmd"             : "clang++ $(IN) -o $(OUT) $(FLAGS)"                    ,
    "obj_suffix"               : ".o"                                                  ,  
    "dynamic_suffix"           : ".dylib"                                              , 
    "static_suffix"            : ".a"                                                  ,
    "exe_suffix"               : ""                                                    ,
    "incs_prefix"              : "-I"                                                  
}




# now set the DETECTED_COMPILER variable depending on the current platform

if sys.platform in "win32" : 
    
    # check if the compiler is 32 or 64 bits
    process             = subprocess.Popen( "cl.exe" ,  stdout = subprocess.PIPE , stderr = subprocess.PIPE )
    ( stdout , stderr ) = process.communicate()
    returnCode          = process.wait()
    
    # check architecture used by the current compiler
    if "x64" in str( stderr ) : 
        print( "Windows : 64-bits PLATEFORM" )
        KNOWN_COMPILERS["msvc2008"]["machine"] = "64"
        KNOWN_COMPILERS["msvc2012"]["machine"] = "64"
        KNOWN_COMPILERS["msvc2013"]["machine"] = "64"
        KNOWN_COMPILERS["msvc2015"]["machine"] = "64"
    elif "80x86" in str( stderr ) or "x86" in str( stderr ) : 
        print( "Windows : 32-bits PLATEFORM" )
        KNOWN_COMPILERS["msvc2008"]["machine"] = "32"
        KNOWN_COMPILERS["msvc2012"]["machine"] = "32"
        KNOWN_COMPILERS["msvc2013"]["machine"] = "32"
        KNOWN_COMPILERS["msvc2015"]["machine"] = "32"
    
    # set the msvc version according to the answer
    if "Version 15.00" in str( stderr ) :
        print( "Visual Studio 2008 ," , KNOWN_COMPILERS["msvc2008"]["machine"] + "bits" )
        DETECTED_COMPILER = KNOWN_COMPILERS["msvc2008"]
    elif "Version 17.00" in str( stderr ):
        print( "Visual Studio 2012 ,", KNOWN_COMPILERS["msvc2012"]["machine"] + "bits" )
        DETECTED_COMPILER = KNOWN_COMPILERS["msvc2012"]
    elif "Version 18.00" in str( stderr ) :
        print( "Visual Studio 2013 ,", KNOWN_COMPILERS["msvc2013"]["machine"] + "bits" )
        DETECTED_COMPILER = KNOWN_COMPILERS["msvc2013"]
    elif "Version 19.00" in str( stderr ) :
        print( "Visual Studio 2015 ,", KNOWN_COMPILERS["msvc2015"]["machine"] + "bits" )
        DETECTED_COMPILER = KNOWN_COMPILERS["msvc2015"]
    
    
elif sys.platform == "darwin" :
    print( "Mac OS : 64-bits PLATEFORM" )
    print( "LLVM   : gcc" )
    DETECTED_COMPILER = KNOWN_COMPILERS["g++ MacOS"]


elif sys.platform == "linux" :
    print( "Linux : 64-bits PLATEFORM" )
    print( "gcc" )
    DETECTED_COMPILER = KNOWN_COMPILERS["gcc"]
    

    

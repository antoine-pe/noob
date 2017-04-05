from noob.staticlibrary  import StaticLibraryNode
from noob.dynamiclibrary import DynamicLibraryNode
from noob.executable     import ExecutableNode
from noob                import compiler
import sys

if __name__ == '__main__':
    
    # this dynamic library defines the otherHello() function
    # uses the __declspec mechanism on windows
    otherLibNode = DynamicLibraryNode( 
        lib_name  = "myOtherLib"     , 
        srcs      = [ "./dynamicLib.cpp"]  , 
        tmp_dir   = "./tmp" ,
        cc_flags  = [] if sys.platform in ["darwin" , "linux"] else [ "/DEXPORT" ] , # use the __declspec mechanism on windows
        dest_dir  = "./exe" ,
    )
    
    # this static library defines the sayHello() function
    # calling the otherHello() from the previous dynamic lib
    libNode = StaticLibraryNode( 
        lib_name  = "myLib"     , 
        srcs      = ["./staticLib.cpp"] ,
        tmp_dir   = "./tmp" ,
        dest_dir  = "./exe" ,
    )
    libNode.depends( otherLibNode ) 
    
    # hello executable call the sayHello() from the static lib
    helloExe = ExecutableNode( 
        exe_name  = "hello" ,
        srcs      = ["./main.cc"] ,
        tmp_dir   = "./tmp" ,
        dest_dir  = "./exe" 
        
    )
    helloExe.depends( libNode ) 
    helloExe.cleanAll()
    helloExe.build()
    
    
    # example of multi-targets build on Windows :
    
#   libNode.tmp_dir      = "./tmp2008"
#   otherLibNode.tmp_dir = "./tmp2008"
#   helloExe.tmp_dir     = "./tmp2008"
#   helloExe.dest_dir    = "./exe2008"
#   helloExe.build( ) #compiler = compiler.COMPILER_CONFIG_DICT["msvc2008"] )
    
#   libNode.tmp_dir      = "./tmp2015"
#   otherLibNode.tmp_dir = "./tmp2015"
#   helloExe.tmp_dir     = "./tmp2015"
#   helloExe.dest_dir    = "./exe2015"
#   helloExe.build( compiler = compiler.COMPILER_CONFIG_DICT["msvc2015"] )
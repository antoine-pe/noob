import platform

if "Darwin" in platform.platform():
    SWIG_CONFIG = {
          "config_name" : "swig" ,
          "swig_ext"    : ".so"  , 
          "swig_cmd"    : "/Users/antoine/dev/app/swig/bin/swig -Wall $(FLAGS) -o $(OUT) $(IN)"
    }
    
elif "Windows" in platform.platform():
    SWIG_CONFIG = {
      "config_name" : "swig" , 
      "swig_ext"    : ".pyd" ,
#     "swig_cmd"    : "C:/dev/app/swig/2.0.4/swig.exe -Wall -DWIN32 $(FLAGS) -o $(OUT) $(IN)"    
      "swig_cmd"    : "C:/dev/app/swig/3.0.10/prebuild/swig.exe -Wall -DWIN32 $(FLAGS) -o $(OUT) $(IN)"    
    }



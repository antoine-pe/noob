# Noob
Noob is a new easy-to-use programmable build system written in Python. It's an open source, self-contained, python 
module aimed to ease the process of compiling c++ libraries or executables. It is cross-platform and works on Windows, Linux 
and MacOS with the main compilers available ( gcc, llvm , msvc > 2008 , ... ). It is mainly 
oriented to build C++ projects for now, but can be easily extended to do other kind of task. 

Main web page : http://www.noob-builder.org/

A minimal example can be provided as so :

```
# file : build_hello.py
from noob.exenode import ExecutableNode
 
helloWorldNode = ExecutableNode( 
  srcs     = [ "/my/path/to/helloWorld.cpp" ],
  cc_flags = [ "-O3" , "-std=c++11"         ],
  exe_name = "hello"                       
)
helloWorldNode.build() # build the "hello world" executable 
```

#ifndef DYNAMIC_LIB_H
#define DYNAMIC_LIB_H

// this is a minimal example of multi-platform code
#ifdef _WINDOWS
	// the _WINDOWS define is automatically set when using msvc
	#ifdef EXPORT_HELLO_API  
	#define HELLO_API __declspec(dllexport)   
	#else  
	#define HELLO_API __declspec(dllimport)   
	#endif  
#else 
	// we are on linux or mac os here so the __declspec mechanism is meaningless
	#define HELLO_API
#endif

extern HELLO_API void otherHello() ;

#endif

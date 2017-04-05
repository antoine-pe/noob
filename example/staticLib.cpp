#include "staticLib.h"
#include "dynamicLib.h"
#include <iostream>

void sayHello() {
	otherHello();
	std::cout << "Hello World from static lib!!" << std::endl;
}
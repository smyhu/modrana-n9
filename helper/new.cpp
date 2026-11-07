// operator new/delete without libstdc++ (the N9 has libstdc++ from gcc 4.4)
#include <stdlib.h>
void *operator new(unsigned int n) { return malloc(n ? n : 1); }
void *operator new[](unsigned int n) { return malloc(n ? n : 1); }
void operator delete(void *p) throw() { free(p); }
void operator delete[](void *p) throw() { free(p); }
void operator delete(void *p, unsigned int) throw() { free(p); }
void operator delete[](void *p, unsigned int) throw() { free(p); }
extern "C" void __cxa_pure_virtual() { abort(); }
// unwind tables from libc_nonshared.a; exceptions are not used
extern "C" void __aeabi_unwind_cpp_pr0() { abort(); }
extern "C" void __aeabi_unwind_cpp_pr1() { abort(); }

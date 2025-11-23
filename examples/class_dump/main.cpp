#include "../../fct.h"
#include <stdint.h>

#define PRINTABLE FCT_NOTE("printable")

struct PRINTABLE Person
{
    char const* name;
    int age;
};

#include "g/printables.g.h"

int main()
{
    auto p = Person { .name = "John", .age = 30 };
    g::print_class(p);

    return 0;
}
#include "../../fct.h"
#include <stdint.h>
#include <iostream>

#define SOA FCT_NOTE("soa")
#define REPR FCT_NOTE("struct_repr_inline")

struct SOA REPR Person
{
    char const* name;
    uint8_t age;
};

#include "g/soa.g.h"
#include "g/repr.g.h"

#define DUMP(expr) std::cout << #expr << "\n↳ " << (expr) << "\n\n";

int main()
{
    auto p = Person { .name = "John", .age = 30 };
    auto people = g::Soa<Person, 100>();
    people.set(10, p);

    DUMP(g::repr(p));
    DUMP(g::repr(people.get(10)));

    DUMP(uint(people.get_age(10)));
    DUMP(uint(people.get_age(2)));

    return 0;
}
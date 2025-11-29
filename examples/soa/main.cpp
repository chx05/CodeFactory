#include <stdint.h>
#include <iostream>

#define FCT_NOTE(s) [[clang::annotate(s)]]
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
    constexpr auto NumberOfPeople = 100;

    // soa first

    auto p = Person { .name = "John", .age = 30 };
    auto soa_people = g::Soa<Person, NumberOfPeople>();
    soa_people.set(10, p);
    
    DUMP(g::repr(p));
    DUMP(g::repr(soa_people.get(10)));
    DUMP(soa_people.get_name(10));
    DUMP(uint(soa_people.get_age(10)));

    // back to aos

    Person aos_people[NumberOfPeople];
    soa_people.copy_to_aos(aos_people);

    DUMP(g::repr(aos_people[10]));

    return 0;
}
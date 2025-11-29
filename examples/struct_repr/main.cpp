#include "../../fct.h"
#include <stdint.h>
#include <string>
#include <iostream>

#define REPR FCT_NOTE("struct_repr")
#define REPR_INLINE FCT_NOTE("struct_repr_inline")

namespace some_lib::math
{
    struct REPR_INLINE Position
    {
        float x;
        float y;
        float z;
    };
}

struct REPR Person
{
    struct REPR SubPerson
    {
        std::string sub_name;
        int8_t sub_age;
        char sex;
        bool is_alive;
        int some_int;
        char const* text;
        some_lib::math::Position pos;
    };

    char const* name;
    uint8_t age;
    SubPerson sp;
};

#include "g/repr.g.h"

int main()
{
    auto p = Person
    {
        .name = "John",
        .age = 30,
        .sp = Person::SubPerson
        {
            .sub_name = "SubJohn",
            .sub_age = -15,
            .sex = 'm',
            // this also works 
            //.sex = '\n',
            .is_alive = true,
            .some_int = 123,
            .text = "some new line \n, some tab \t, some quotes: \"Hello World!\"",
            .pos = some_lib::math::Position { .x = 1.2, .y = 2.3, .z = 3.4 }
        }
    };

    std::cout << g::repr(p) << std::endl;
    return 0;
}
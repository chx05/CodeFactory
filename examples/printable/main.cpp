#include "../../fct.h"
#include <stdint.h>
#include <string>

#define PRINTABLE FCT_NOTE("printable")

struct PRINTABLE Person
{
    struct PRINTABLE SubPerson
    {
        std::string sub_name;
        int8_t sub_age;
        char sex;
        bool is_alive;
        int some_int;
        char const* text;
    };

    char const* name;
    uint8_t age;
    SubPerson sp;
};

#include "g/printables.g.h"

int main()
{
    auto sp = Person::SubPerson
    {
        .sub_name = "SubJohn",
        .sub_age = -15,
        .sex = 'm',
        .is_alive = true,
        .some_int = 123,
        .text = "some new line \n, some tab \t, some quotes: \"Hello World!\""
    };
    g::print_class(sp);

    auto p = Person
    {
        .name = "John",
        .age = 30,
        .sp = sp
    };
    g::print_class(p);

    return 0;
}
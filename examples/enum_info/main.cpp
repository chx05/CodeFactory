#include <stdint.h>
#include <iostream>

#define FCT_NOTE(s) [[clang::annotate(s)]]
#define ENUM_INFO FCT_NOTE("enum_info")

enum struct ENUM_INFO TokenKind : char
{
    eof,

    ident,
    literal_int,
    literal_float,
    literal_str,

    plus = '+',
    minus = '-',
    star = '*',
    slash = '/',

    kw_def,
    kw_pass,
    kw_return,
};

namespace some_lib::io
{
    enum struct ENUM_INFO FileError
    {
        Ok = 0,
        FileNotFound,
        AccessDenied,
        IsDirectory
    };
}

#include "g/enum_info.g.h"

int main()
{
    constexpr auto number_of_token_kinds = g::EnumInfo<TokenKind>::Count;
    auto some_kind = TokenKind::ident;
    auto unbound_kind = (TokenKind)123;
    std::cout << "Number of token kinds: " << number_of_token_kinds << std::endl;
    std::cout << "Some: " << g::EnumInfo<TokenKind>::repr(some_kind) << std::endl;
    std::cout << "Unbound: " << g::EnumInfo<TokenKind>::repr(unbound_kind) << std::endl;

    std::cout << "Number of file error kinds: " << g::EnumInfo<some_lib::io::FileError>::Count << std::endl;
    std::cout << "FileNotFound: " << g::EnumInfo<some_lib::io::FileError>::repr(some_lib::io::FileError::FileNotFound) << std::endl;

    return 0;
}
"""
Unit tests for Codebase Cartographer parsers.
"""
import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from cartographer.parsers import (
    PythonParser,
    JavaScriptTypeScriptParser,
    GoParser,
    RubyParser,
    CParser,
    CppParser,
    CSharpParser,
    SQLParser,
    GraphQLParser,
    PrismaParser,
    LanguageDetector,
    get_parser_for_file,
)


class TestLanguageDetector:
    """Test language detection."""

    def test_detect_python(self):
        detector = LanguageDetector()
        assert detector.detect(Path('test.py')) == 'python'
        assert detector.detect(Path('test.pyi')) == 'python'

    def test_detect_typescript(self):
        detector = LanguageDetector()
        assert detector.detect(Path('test.ts')) == 'typescript'
        assert detector.detect(Path('test.tsx')) == 'typescript-react'

    def test_detect_javascript(self):
        detector = LanguageDetector()
        assert detector.detect(Path('test.js')) == 'javascript'
        assert detector.detect(Path('test.jsx')) == 'javascript-react'

    def test_detect_go(self):
        detector = LanguageDetector()
        assert detector.detect(Path('test.go')) == 'go'

    def test_detect_sql(self):
        detector = LanguageDetector()
        assert detector.detect(Path('schema.sql')) == 'sql'

    def test_detect_graphql(self):
        detector = LanguageDetector()
        assert detector.detect(Path('schema.graphql')) == 'graphql'
        assert detector.detect(Path('schema.gql')) == 'graphql'

    def test_detect_prisma(self):
        detector = LanguageDetector()
        assert detector.detect(Path('schema.prisma')) == 'prisma'

    def test_detect_c(self):
        detector = LanguageDetector()
        assert detector.detect(Path('main.c')) == 'c'
        assert detector.detect(Path('header.h')) == 'c-header'

    def test_detect_cpp(self):
        detector = LanguageDetector()
        assert detector.detect(Path('main.cpp')) == 'cpp'
        assert detector.detect(Path('main.cc')) == 'cpp'
        assert detector.detect(Path('header.hpp')) == 'cpp-header'

    def test_detect_csharp(self):
        detector = LanguageDetector()
        assert detector.detect(Path('Program.cs')) == 'csharp'


class TestPythonParser:
    """Test Python parser."""

    def test_parse_function(self):
        parser = PythonParser()
        code = '''
def hello(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"
'''
        result = parser.parse(code, 'test.py')
        assert len(result.components) == 1
        assert result.components[0].name == 'hello'
        assert result.components[0].type == 'function'

    def test_parse_class(self):
        parser = PythonParser()
        code = '''
class User:
    """User model."""
    def __init__(self, name):
        self.name = name

    def greet(self):
        return f"Hello, {self.name}"
'''
        result = parser.parse(code, 'test.py')
        # Should find: class User, __init__, greet
        class_comps = [c for c in result.components if c.type == 'class']
        method_comps = [c for c in result.components if c.type == 'method']
        assert len(class_comps) == 1
        assert class_comps[0].name == 'User'
        assert len(method_comps) == 2

    def test_parse_async_function(self):
        parser = PythonParser()
        code = '''
async def fetch_data(url: str) -> dict:
    """Fetch data from URL."""
    pass
'''
        result = parser.parse(code, 'test.py')
        assert len(result.components) == 1
        assert result.components[0].is_async == True

    def test_parse_dataclass(self):
        parser = PythonParser()
        code = '''
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int
'''
        result = parser.parse(code, 'test.py')
        class_comps = [c for c in result.components if c.type == 'class']
        assert len(class_comps) == 1
        assert class_comps[0].metadata.get('subtype') == 'dataclass'

    def test_parse_constant(self):
        parser = PythonParser()
        code = '''
MAX_RETRIES = 3
API_VERSION = "v1"
'''
        result = parser.parse(code, 'test.py')
        constants = [c for c in result.components if c.type == 'constant']
        assert len(constants) == 2


class TestJavaScriptTypeScriptParser:
    """Test JavaScript/TypeScript parser."""

    def test_parse_function(self):
        parser = JavaScriptTypeScriptParser(is_typescript=False)
        code = '''
function greet(name) {
    return `Hello, ${name}`;
}
'''
        result = parser.parse(code, 'test.js')
        funcs = [c for c in result.components if c.type == 'function']
        assert len(funcs) == 1
        assert funcs[0].name == 'greet'

    def test_parse_arrow_function(self):
        parser = JavaScriptTypeScriptParser(is_typescript=False)
        code = '''
const add = (a, b) => a + b;
'''
        result = parser.parse(code, 'test.js')
        funcs = [c for c in result.components if c.type == 'function']
        assert len(funcs) == 1
        assert funcs[0].name == 'add'

    def test_parse_class(self):
        parser = JavaScriptTypeScriptParser(is_typescript=True)
        code = '''
export class UserService {
    constructor(private db: Database) {}

    async getUser(id: string): Promise<User> {
        return this.db.find(id);
    }
}
'''
        result = parser.parse(code, 'test.ts')
        classes = [c for c in result.components if c.type == 'class']
        assert len(classes) == 1
        assert classes[0].name == 'UserService'
        assert classes[0].exported == True

    def test_parse_routes(self):
        parser = JavaScriptTypeScriptParser(is_typescript=True)
        code = '''
app.get('/users', async (req, res) => {
    res.json(users);
});

app.post('/users', async (req, res) => {
    // Create user
});
'''
        result = parser.parse(code, 'routes.ts')
        routes = [c for c in result.components if c.type == 'route']
        assert len(routes) == 2

    def test_parse_interface(self):
        parser = JavaScriptTypeScriptParser(is_typescript=True)
        code = '''
export interface User {
    id: string;
    name: string;
    email: string;
}
'''
        result = parser.parse(code, 'types.ts')
        interfaces = [c for c in result.components if c.type == 'interface']
        assert len(interfaces) == 1
        assert interfaces[0].name == 'User'

    def test_parse_enum(self):
        parser = JavaScriptTypeScriptParser(is_typescript=True)
        code = '''
export enum Status {
    Active,
    Inactive,
    Pending
}
'''
        result = parser.parse(code, 'types.ts')
        enums = [c for c in result.components if c.type == 'enum']
        assert len(enums) == 1
        assert enums[0].name == 'Status'

    def test_parse_test_blocks(self):
        parser = JavaScriptTypeScriptParser(is_typescript=True)
        code = '''
describe('UserService', () => {
    it('should create user', () => {
        expect(true).toBe(true);
    });

    test('should delete user', () => {
        expect(true).toBe(true);
    });
});
'''
        result = parser.parse(code, 'user.test.ts')
        suites = [c for c in result.components if c.type == 'test_suite']
        cases = [c for c in result.components if c.type == 'test_case']
        assert len(suites) == 1
        assert len(cases) == 2


class TestGoParser:
    """Test Go parser."""

    def test_parse_struct(self):
        parser = GoParser()
        code = '''
package main

type User struct {
    ID   string
    Name string
}
'''
        result = parser.parse(code, 'main.go')
        structs = [c for c in result.components if c.type == 'struct']
        assert len(structs) == 1
        assert structs[0].name == 'User'
        assert structs[0].exported == True

    def test_parse_function(self):
        parser = GoParser()
        code = '''
package main

func Hello(name string) string {
    return "Hello, " + name
}
'''
        result = parser.parse(code, 'main.go')
        funcs = [c for c in result.components if c.type == 'function']
        assert len(funcs) == 1
        assert funcs[0].name == 'Hello'

    def test_parse_method(self):
        parser = GoParser()
        code = '''
package main

func (u *User) Greet() string {
    return "Hello, " + u.Name
}
'''
        result = parser.parse(code, 'main.go')
        methods = [c for c in result.components if c.type == 'method']
        assert len(methods) == 1
        assert methods[0].name == 'Greet'
        assert methods[0].parent == 'User'

    def test_parse_constant(self):
        parser = GoParser()
        code = '''
package main

const MaxRetries = 3

const (
    StatusActive = "active"
    StatusInactive = "inactive"
)
'''
        result = parser.parse(code, 'main.go')
        constants = [c for c in result.components if c.type == 'constant']
        assert len(constants) == 3


class TestCParser:
    """Test C parser."""

    def test_parse_function(self):
        parser = CParser()
        code = '''
int add(int a, int b) {
    return a + b;
}
'''
        result = parser.parse(code, 'math.c')
        funcs = [c for c in result.components if c.type == 'function']
        assert len(funcs) == 1
        assert funcs[0].name == 'add'

    def test_parse_static_function(self):
        parser = CParser()
        code = '''
static int helper(int x) {
    return x * 2;
}
'''
        result = parser.parse(code, 'helper.c')
        funcs = [c for c in result.components if c.type == 'function']
        assert len(funcs) == 1
        assert funcs[0].exported == False
        assert 'static' in funcs[0].modifiers

    def test_parse_struct(self):
        parser = CParser()
        code = '''
struct Point {
    int x;
    int y;
};
'''
        result = parser.parse(code, 'types.c')
        structs = [c for c in result.components if c.type == 'struct']
        assert len(structs) == 1
        assert structs[0].name == 'Point'

    def test_parse_macro(self):
        parser = CParser()
        code = '''
#define MAX_SIZE 100
#define MIN(a, b) ((a) < (b) ? (a) : (b))
'''
        result = parser.parse(code, 'macros.h')
        macros = [c for c in result.components if c.type == 'macro']
        assert len(macros) == 2
        # Check function-like macro
        min_macro = [m for m in macros if m.name == 'MIN'][0]
        assert min_macro.metadata.get('function_like') == True

    def test_parse_enum(self):
        parser = CParser()
        code = '''
enum Color {
    RED,
    GREEN,
    BLUE
};
'''
        result = parser.parse(code, 'colors.h')
        enums = [c for c in result.components if c.type == 'enum']
        assert len(enums) == 1
        assert enums[0].name == 'Color'

    def test_parse_includes(self):
        parser = CParser()
        code = '''
#include <stdio.h>
#include "myheader.h"

int main() {
    return 0;
}
'''
        result = parser.parse(code, 'main.c')
        # Check relationships
        imports = [r for r in result.relationships if r['type'] == 'imports']
        assert len(imports) == 2


class TestCppParser:
    """Test C++ parser."""

    def test_parse_class(self):
        parser = CppParser()
        code = '''
class Rectangle {
public:
    int width;
    int height;
};
'''
        result = parser.parse(code, 'shapes.cpp')
        classes = [c for c in result.components if c.type == 'class']
        assert len(classes) == 1
        assert classes[0].name == 'Rectangle'

    def test_parse_class_inheritance(self):
        parser = CppParser()
        code = '''
class Square : public Rectangle {
public:
    int side;
};
'''
        result = parser.parse(code, 'shapes.cpp')
        classes = [c for c in result.components if c.type == 'class']
        assert len(classes) == 1
        # Check inheritance relationship
        extends = [r for r in result.relationships if r['type'] == 'extends']
        assert len(extends) == 1
        assert extends[0]['to'] == 'Rectangle'

    def test_parse_namespace(self):
        parser = CppParser()
        code = '''
namespace myapp {
    int value = 42;
}
'''
        result = parser.parse(code, 'app.cpp')
        namespaces = [c for c in result.components if c.type == 'namespace']
        assert len(namespaces) == 1
        assert namespaces[0].name == 'myapp'

    def test_parse_struct(self):
        parser = CppParser()
        code = '''
struct Item {
    int weight;
    int profit;
};
'''
        result = parser.parse(code, 'items.cpp')
        structs = [c for c in result.components if c.type == 'struct']
        assert len(structs) == 1
        assert structs[0].name == 'Item'

    def test_parse_function(self):
        parser = CppParser()
        code = '''
int partition(int arr[], int low, int high) {
    return 0;
}
'''
        result = parser.parse(code, 'sort.cpp')
        funcs = [c for c in result.components if c.type == 'function']
        assert len(funcs) == 1
        assert funcs[0].name == 'partition'

    def test_parse_enum_class(self):
        parser = CppParser()
        code = '''
enum class Color {
    Red,
    Green,
    Blue
};
'''
        result = parser.parse(code, 'colors.cpp')
        enums = [c for c in result.components if c.type == 'enum']
        assert len(enums) == 1
        assert enums[0].metadata.get('scoped') == True

    def test_parse_template_function(self):
        parser = CppParser()
        code = '''
template<typename T>
T max(T a, T b) {
    return (a > b) ? a : b;
}
'''
        result = parser.parse(code, 'utils.cpp')
        templates = [c for c in result.components if c.type == 'template_function']
        assert len(templates) == 1
        assert templates[0].name == 'max'


class TestCSharpParser:
    """Test C# parser."""

    def test_parse_namespace(self):
        parser = CSharpParser()
        code = '''
namespace MyApp.Models;

public class User { }
'''
        result = parser.parse(code, 'User.cs')
        namespaces = [c for c in result.components if c.type == 'namespace']
        assert len(namespaces) == 1
        assert namespaces[0].name == 'MyApp.Models'
        assert namespaces[0].metadata.get('file_scoped') == True

    def test_parse_class(self):
        parser = CSharpParser()
        code = '''
public class UserService {
    public async Task<User> GetUser(string id) {
        return null;
    }
}
'''
        result = parser.parse(code, 'UserService.cs')
        classes = [c for c in result.components if c.type == 'class']
        methods = [c for c in result.components if c.type == 'method']
        assert len(classes) == 1
        assert classes[0].name == 'UserService'
        assert len(methods) == 1
        assert methods[0].is_async == True

    def test_parse_interface(self):
        parser = CSharpParser()
        code = '''
public interface IUserRepository {
    Task<User> FindById(string id);
}
'''
        result = parser.parse(code, 'IUserRepository.cs')
        interfaces = [c for c in result.components if c.type == 'interface']
        assert len(interfaces) == 1
        assert interfaces[0].name == 'IUserRepository'

    def test_parse_struct(self):
        parser = CSharpParser()
        code = '''
public readonly struct Point {
    public int X { get; }
    public int Y { get; }
}
'''
        result = parser.parse(code, 'Point.cs')
        structs = [c for c in result.components if c.type == 'struct']
        assert len(structs) == 1
        assert 'readonly' in structs[0].modifiers

    def test_parse_enum(self):
        parser = CSharpParser()
        code = '''
public enum Status {
    Active,
    Inactive,
    Pending
}
'''
        result = parser.parse(code, 'Status.cs')
        enums = [c for c in result.components if c.type == 'enum']
        assert len(enums) == 1
        assert enums[0].name == 'Status'

    def test_parse_record(self):
        parser = CSharpParser()
        code = '''
public record Person(string FirstName, string LastName);
'''
        result = parser.parse(code, 'Person.cs')
        records = [c for c in result.components if c.type == 'record']
        assert len(records) == 1
        assert records[0].name == 'Person'

    def test_parse_generic_class(self):
        parser = CSharpParser()
        code = '''
public class Cache<TKey, TValue> where TKey : notnull {
    private readonly Dictionary<TKey, TValue> items;
}
'''
        result = parser.parse(code, 'Cache.cs')
        classes = [c for c in result.components if c.type == 'class']
        assert len(classes) == 1
        assert classes[0].metadata.get('generic_params') == 'TKey, TValue'

    def test_parse_properties(self):
        parser = CSharpParser()
        code = '''
public class Person {
    public string Name { get; set; }
    public int Age { get; private set; }
}
'''
        result = parser.parse(code, 'Person.cs')
        props = [c for c in result.components if c.type == 'property']
        assert len(props) == 2

    def test_parse_using_statements(self):
        parser = CSharpParser()
        code = '''
using System;
using System.Collections.Generic;

public class Demo { }
'''
        result = parser.parse(code, 'Demo.cs')
        imports = [r for r in result.relationships if r['type'] == 'imports']
        assert len(imports) == 2


class TestSQLParser:
    """Test SQL parser."""

    def test_parse_table(self):
        parser = SQLParser()
        code = '''
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);
'''
        result = parser.parse(code, 'schema.sql')
        tables = [c for c in result.components if c.type == 'table']
        assert len(tables) == 1
        assert tables[0].name == 'users'

    def test_parse_index(self):
        parser = SQLParser()
        code = '''
CREATE INDEX idx_users_email ON users(email);
CREATE UNIQUE INDEX idx_users_name ON users(name);
'''
        result = parser.parse(code, 'schema.sql')
        indexes = [c for c in result.components if c.type == 'index']
        assert len(indexes) == 2

    def test_parse_view(self):
        parser = SQLParser()
        code = '''
CREATE VIEW active_users AS
SELECT * FROM users WHERE status = 'active';
'''
        result = parser.parse(code, 'schema.sql')
        views = [c for c in result.components if c.type == 'view']
        assert len(views) == 1
        assert views[0].name == 'active_users'


class TestGraphQLParser:
    """Test GraphQL parser."""

    def test_parse_type(self):
        parser = GraphQLParser()
        code = '''
type User {
    id: ID!
    name: String!
    email: String!
}
'''
        result = parser.parse(code, 'schema.graphql')
        types = [c for c in result.components if c.type == 'type']
        assert len(types) == 1
        assert types[0].name == 'User'

    def test_parse_query(self):
        parser = GraphQLParser()
        code = '''
type Query {
    users: [User!]!
    user(id: ID!): User
}
'''
        result = parser.parse(code, 'schema.graphql')
        queries = [c for c in result.components if c.type == 'query']
        assert len(queries) == 2

    def test_parse_mutation(self):
        parser = GraphQLParser()
        code = '''
type Mutation {
    createUser(input: CreateUserInput!): User!
    deleteUser(id: ID!): Boolean!
}
'''
        result = parser.parse(code, 'schema.graphql')
        mutations = [c for c in result.components if c.type == 'mutation']
        assert len(mutations) == 2

    def test_parse_enum(self):
        parser = GraphQLParser()
        code = '''
enum Status {
    ACTIVE
    INACTIVE
    PENDING
}
'''
        result = parser.parse(code, 'schema.graphql')
        enums = [c for c in result.components if c.type == 'enum']
        assert len(enums) == 1
        assert enums[0].name == 'Status'


class TestPrismaParser:
    """Test Prisma parser."""

    def test_parse_model(self):
        parser = PrismaParser()
        code = '''
model User {
    id        String   @id @default(cuid())
    email     String   @unique
    name      String?
    posts     Post[]
    createdAt DateTime @default(now())
}
'''
        result = parser.parse(code, 'schema.prisma')
        models = [c for c in result.components if c.type == 'model']
        assert len(models) == 1
        assert models[0].name == 'User'

    def test_parse_enum(self):
        parser = PrismaParser()
        code = '''
enum Role {
    USER
    ADMIN
    MODERATOR
}
'''
        result = parser.parse(code, 'schema.prisma')
        enums = [c for c in result.components if c.type == 'enum']
        assert len(enums) == 1
        assert enums[0].name == 'Role'

    def test_parse_relations(self):
        parser = PrismaParser()
        code = '''
model Post {
    id       String @id
    author   User   @relation(fields: [authorId], references: [id])
    authorId String
}
'''
        result = parser.parse(code, 'schema.prisma')
        models = [c for c in result.components if c.type == 'model']
        assert len(models) == 1
        # Check that User is captured as a relation
        assert 'User' in models[0].metadata.get('relations', [])


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

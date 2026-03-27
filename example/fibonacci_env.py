import pywasm
pywasm.log.lvl = 1


def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def fibonacci_host(_: pywasm.core.Machine, args: list[int]) -> list[int]:
    return [fibonacci(args[0])]


runtime = pywasm.core.Runtime()
runtime.imports['env'] = {}
runtime.imports['env']['fibonacci_host'] = runtime.allocate_func_host(
    pywasm.core.FuncType([pywasm.core.ValType.i32()], [pywasm.core.ValType.i32()]),
    fibonacci_host,
)
m = runtime.instance_from_file('example/fibonacci_env/bin/fibonacci_env.wasm')
r = runtime.invocate(m, 'fibonacci', [10])
print(f'fibonacci(10) = {r[0]}')

import glob
import json
import math
import pathlib
import pywasm


pywasm.log.lvl = 0


def valj(j: dict) -> pywasm.ValInst:
    match j['type']:
        case 'i32':
            return pywasm.ValInst.from_i32(pywasm.arith.i32.fit(int(j['value'])))
        case 'i64':
            return pywasm.ValInst.from_i64(pywasm.arith.i64.fit(int(j['value'])))
        case 'f32':
            match j['value']:
                case 'nan:canonical':
                    return pywasm.ValInst.from_f32_u32(0x7fc00000)
                case 'nan:arithmetic':
                    return pywasm.ValInst.from_f32_u32(0x7fc00001)
                case _:
                    return pywasm.ValInst.from_f32_u32(int(j['value']))
        case 'f64':
            match j['value']:
                case 'nan:canonical':
                    return pywasm.ValInst.from_f64_u64(0x7ff8000000000000)
                case 'nan:arithmetic':
                    return pywasm.ValInst.from_f64_u64(0x7ff8000000000001)
                case _:
                    return pywasm.ValInst.from_f64_u64(int(j['value']))
        case 'v128':
            match j['lane_type']:
                case 'i8':
                    return pywasm.ValInst.from_v128_i8([pywasm.arith.i8.fit(int(c)) for c in j['value']])
                case 'i16':
                    return pywasm.ValInst.from_v128_i16([pywasm.arith.i16.fit(int(c)) for c in j['value']])
                case 'i32':
                    return pywasm.ValInst.from_v128_i32([pywasm.arith.i32.fit(int(c)) for c in j['value']])
                case 'i64':
                    return pywasm.ValInst.from_v128_i64([pywasm.arith.i64.fit(int(c)) for c in j['value']])
                case 'f32':
                    data = [valj({'type': 'f32', 'value': e}).into_u32() for e in j['value']]
                    return pywasm.ValInst.from_v128_u32(data)
                case 'f64':
                    data = [valj({'type': 'f64', 'value': e}).into_u64() for e in j['value']]
                    return pywasm.ValInst.from_v128_u64(data)
                case _:
                    raise Exception('unreachable')
        case 'funcref':
            match j['value']:
                case 'null':
                    return pywasm.ValInst.zero(pywasm.core.ValType.ref_func())
                case _:
                    return pywasm.ValInst.from_ref(pywasm.core.ValType.ref_extern(), int(j['value']))
        case 'externref':
            match j['value']:
                case 'null':
                    return pywasm.ValInst.zero(pywasm.core.ValType.ref_extern())
                case _:
                    return pywasm.ValInst.from_ref(pywasm.core.ValType.ref_extern(), int(j['value']))
        case _:
            raise Exception('unreachable')


def vale(a: pywasm.ValInst, b: pywasm.ValInst) -> bool:
    if a.type != b.type:
        return False
    if a.type == pywasm.core.ValType.i32():
        return a.into_i32() == b.into_i32()
    if a.type == pywasm.core.ValType.i64():
        return a.into_i64() == b.into_i64()
    if a.type == pywasm.core.ValType.f32():
        if math.isnan(a.into_f32()):
            return math.isnan(b.into_f32())
        return math.isclose(a.into_f32(), b.into_f32(), rel_tol=1e-6)
    if a.type == pywasm.core.ValType.f64():
        if math.isnan(a.into_f64()):
            return math.isnan(b.into_f64())
        return math.isclose(a.into_f64(), b.into_f64(), rel_tol=1e-6)
    if a.type == pywasm.core.ValType.v128():
        if a.into_v128() == b.into_v128():
            return True
        x = [pywasm.core.ValInst.from_f32(e) for e in a.into_v128_f32()]
        y = [pywasm.core.ValInst.from_f32(e) for e in b.into_v128_f32()]
        if all([vale(x, y) for x, y in zip(x, y)]):
            return True
        x = [pywasm.core.ValInst.from_f64(e) for e in a.into_v128_f64()]
        y = [pywasm.core.ValInst.from_f64(e) for e in b.into_v128_f64()]
        if all([vale(x, y) for x, y in zip(x, y)]):
            return True
        return False
    if a.type == pywasm.core.ValType.ref_func():
        return a.into_i64() == b.into_i64()
    if a.type == pywasm.core.ValType.ref_extern():
        return a.into_i64() == b.into_i64()
    raise Exception('unreachable')


def host(runtime: pywasm.core.Runtime):
    # See https://github.com/WebAssembly/spec/blob/w3c-1.0/interpreter/host/spectest.ml
    runtime.imports['spectest'] = {
        'global_i32': runtime.allocate_global(
            pywasm.core.GlobalType(pywasm.core.ValType.i32(), 0), pywasm.core.ValInst.from_i32(666)
        ),
        'global_i64': runtime.allocate_global(
            pywasm.core.GlobalType(pywasm.core.ValType.i64(), 0), pywasm.core.ValInst.from_i64(666)
        ),
        'global_f32': runtime.allocate_global(
            pywasm.core.GlobalType(pywasm.core.ValType.f32(), 0), pywasm.core.ValInst.from_f32(666.6)
        ),
        'global_f64': runtime.allocate_global(
            pywasm.core.GlobalType(pywasm.core.ValType.f64(), 0), pywasm.core.ValInst.from_f64(666.6)
        ),
        'table': runtime.allocate_table(
            pywasm.core.TableType(pywasm.core.ValType.ref_func(), pywasm.core.Limits(10, 20))
        ),
        'memory': runtime.allocate_memory(
            pywasm.core.MemType(pywasm.core.Limits(1, 2))
        ),
        'print': runtime.allocate_func_host(
            pywasm.core.FuncType([], []), lambda m, a: []
        ),
        'print_i32': runtime.allocate_func_host(
            pywasm.core.FuncType([pywasm.core.ValType.i32()], []), lambda m, a: []
        ),
        'print_i64': runtime.allocate_func_host(
            pywasm.core.FuncType([pywasm.core.ValType.i64()], []), lambda m, a: []
        ),
        'print_f32': runtime.allocate_func_host(
            pywasm.core.FuncType([pywasm.core.ValType.f32()], []), lambda m, a: []
        ),
        'print_f64': runtime.allocate_func_host(
            pywasm.core.FuncType([pywasm.core.ValType.f64()], []), lambda m, a: []
        ),
        'print_i32_f32': runtime.allocate_func_host(
            pywasm.core.FuncType([pywasm.core.ValType.i32(), pywasm.core.ValType.f32()], []), lambda m, a: []
        ),
        'print_f64_f64': runtime.allocate_func_host(
            pywasm.core.FuncType([pywasm.core.ValType.f64(), pywasm.core.ValType.f64()], []), lambda m, a: []
        ),
    }


all_test = [
    *sorted(glob.glob('res/spec/test/core/*.json')),
    *sorted(glob.glob('res/spec/test/core/simd/*.json'))
]
for desc in all_test:
    suit = json.loads(pathlib.Path(desc).read_text())['commands']
    runtime = pywasm.Runtime()
    cmodule = pywasm.ModuleInst()
    lmodule = pywasm.ModuleInst()
    mmodule = {}
    host(runtime)
    for elem in suit:
        print(elem)
        match elem['type']:
            case 'action':
                match elem['action']['type']:
                    case 'invoke':
                        cmodule = lmodule
                        if 'module' in elem['action']:
                            cmodule = mmodule[elem['action']['module']]
                        name = elem['action']['field']
                        args = [valj(e) for e in elem['action']['args']]
                        good = [valj(e) for e in elem['expected']]
                        addr = [e for e in cmodule.exps if e.name == name][0].data.data
                        rets = runtime.machine.invocate(addr, args)
                        for a, b in zip(rets, good):
                            assert vale(a, b), f'{rets}, {good}'
                    case _:
                        assert 0
            case 'assert_exhaustion':
                match elem['action']['type']:
                    case 'invoke':
                        cmodule = lmodule
                        if 'module' in elem['action']:
                            cmodule = mmodule[elem['action']['module']]
                        name = elem['action']['field']
                        args = [valj(e) for e in elem['action']['args']]
                        addr = [e for e in cmodule.exps if e.name == name][0].data.data
                        try:
                            runtime.machine.invocate(addr, args)
                        except Exception as e:
                            runtime.machine.stack.frame.clear()
                            runtime.machine.stack.label.clear()
                            runtime.machine.stack.value.clear()
                        else:
                            assert 0
                    case _:
                        assert 0
            case 'assert_invalid':
                assert 1
            case 'assert_malformed':
                assert 1
            case 'assert_return':
                match elem['action']['type']:
                    case 'get':
                        cmodule = lmodule
                        if 'module' in elem['action']:
                            cmodule = mmodule[elem['action']['module']]
                        good = [valj(e) for e in elem['expected']]
                        rets = runtime.exported_global(cmodule, elem['action']['field'])
                        assert vale(rets.data, good[0])
                    case 'invoke':
                        cmodule = lmodule
                        if 'module' in elem['action']:
                            cmodule = mmodule[elem['action']['module']]
                        name = elem['action']['field']
                        args = [valj(e) for e in elem['action']['args']]
                        good = [valj(e) for e in elem['expected']]
                        addr = [e for e in cmodule.exps if e.name == name][0].data.data
                        rets = runtime.machine.invocate(addr, args)
                        for a, b in zip(rets, good):
                            assert vale(a, b), f'{rets}, {good}'
                    case _:
                        assert 0
            case 'assert_trap':
                match elem['action']['type']:
                    case 'invoke':
                        cmodule = lmodule
                        if 'module' in elem['action']:
                            cmodule = mmodule[elem['action']['module']]
                        name = elem['action']['field']
                        args = [valj(e) for e in elem['action']['args']]
                        addr = [e for e in cmodule.exps if e.name == name][0].data.data
                        try:
                            runtime.machine.invocate(addr, args)
                        except Exception as e:
                            runtime.machine.stack.frame.clear()
                            runtime.machine.stack.label.clear()
                            runtime.machine.stack.value.clear()
                        else:
                            assert 0
                    case _:
                        assert 0
            case 'assert_uninstantiable':
                name = str(pathlib.Path(desc).parent.joinpath(elem['filename']))
                try:
                    lmodule = runtime.instance_from_file(name)
                except:
                    runtime.machine.stack.frame.clear()
                    runtime.machine.stack.label.clear()
                    runtime.machine.stack.value.clear()
                else:
                    assert 0
            case 'assert_unlinkable':
                name = str(pathlib.Path(desc).parent.joinpath(elem['filename']))
                try:
                    lmodule = runtime.instance_from_file(name)
                except:
                    runtime.machine.stack.frame.clear()
                    runtime.machine.stack.label.clear()
                    runtime.machine.stack.value.clear()
                else:
                    assert 0
            case 'module':
                name = str(pathlib.Path(desc).parent.joinpath(elem['filename']))
                lmodule = runtime.instance_from_file(name)
                if 'name' in elem:
                    mmodule[elem['name']] = lmodule
            case 'register':
                mmodule[elem['as']] = lmodule
                runtime.imports[elem['as']] = {}
                for e in lmodule.exps:
                    runtime.imports[elem['as']][e.name] = e.data
            case _:
                assert 0

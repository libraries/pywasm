import contextlib
import glob
import io
import json
import os
import platform
import pywasm
import shutil
import sys
import typing


@contextlib.contextmanager
def cd(dst: str) -> typing.Generator[None, typing.Any, None]:
    cwd = os.getcwd()
    os.chdir(dst)
    yield
    os.chdir(cwd)


if platform.system().lower() in ['windows']:
    sys.exit(0)

with cd('res/wasi-testsuite'):
    for e in glob.glob('**/*/*.cleanup', recursive=True):
        if os.path.islink(e):
            os.remove(e)
        if os.path.exists(e) and os.path.isfile(e):
            os.remove(e)
        if os.path.exists(e) and os.path.isdir(e):
            shutil.rmtree(e)
case = []
case.extend(sorted(glob.glob('res/wasi-testsuite/tests/assemblyscript/testsuite/wasm32-wasip1/*.wasm')))
case.extend(sorted(glob.glob('res/wasi-testsuite/tests/c/testsuite/wasm32-wasip1/*.wasm')))
case.extend(sorted(glob.glob('res/wasi-testsuite/tests/rust/testsuite/wasm32-wasip1/*.wasm')))
skip = []
for wasm_path in case:
    if wasm_path in skip:
        continue
    print(wasm_path)
    root = os.path.dirname(wasm_path)
    name = os.path.splitext(os.path.basename(wasm_path))[0]
    conf_path = wasm_path[:-5] + '.json'
    conf = {}
    if os.path.exists(conf_path):
        with open(conf_path) as f:
            conf = json.load(f)
    runtime = pywasm.core.Runtime()
    wasi = pywasm.wasi.Preview1(
        [f'{name}.wasm'] + conf.get('args', []),
        {'/': os.path.join(root, conf['root'])} if 'root' in conf else {},
        conf.get('env', {}),
    )
    wasi.fd[1].pipe = io.BytesIO(bytearray())
    wasi.bind(runtime)
    exit = wasi.main(runtime, runtime.instance_from_file(wasm_path))
    wasi.fd[1].pipe.seek(0)
    if 'stdout' in conf:
        assert wasi.fd[1].pipe.read().decode() == conf['stdout']
    assert exit == conf.get('exit_code', 0)

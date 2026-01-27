import dataclasses
import fcntl
import os
import platform
import pywasm.core
import random
import select
import socket
import stat
import sys
import time
import typing


class Preview1:

    # Wasi started with launching what is now called preview 1. This specification is now widely supported. Preview1
    # corresponds to the import module name "wasi_snapshot_preview1".
    #
    # Pywasm's wasi preview 1 refers to the following rust code.
    # See https://docs.rs/crate/wasi/0.11.1+wasi-snapshot-preview1/source/src/lib_generated.rs
    # See https://docs.rs/wasi/0.11.1+wasi-snapshot-preview1/wasi/wasi_snapshot_preview1/index.html
    # See https://github.com/bytecodealliance/wasmtime/blob/main/crates/wasi-preview1-component-adapter/src/lib.rs

    # The application has no advice to give on its behavior with respect to the specified data.
    ADVICE_NORMAL = 0
    # The application expects to access the specified data sequentially from lower offsets to higher offsets.
    ADVICE_SEQUENTIAL = 1
    # The application expects to access the specified data in a random order.
    ADVICE_RANDOM = 2
    # The application expects to access the specified data in the near future.
    ADVICE_WILLNEED = 3
    # The application expects that it will not access the specified data in the near future.
    ADVICE_DONTNEED = 4
    # The application expects to access the specified data once and then not reuse it thereafter.
    ADVICE_NOREUSE = 5

    # The clock measuring real time. Time value zero corresponds with 1970-01-01T00:00:00Z.
    CLOCKID_REALTIME = 0
    # The store-wide monotonic clock, which is defined as a clock measuring real time, whose value cannot be adjusted
    # and which cannot have negative clock jumps. The epoch of this clock is undefined. The absolute time value of this
    # clock therefore has no meaning.
    CLOCKID_MONOTONIC = 1
    # The CPU-time clock associated with the current process.
    CLOCKID_PROCESS_CPUTIME_ID = 2
    # The CPU-time clock associated with the current thread.
    CLOCKID_THREAD_CPUTIME_ID = 3

    # Special Dircookie value indicating the start of a directory.
    DIRCOOKIE_START = 0

    # No error occurred. System call completed successfully.
    ERRNO_SUCCESS = 0
    # Argument list too long.
    ERRNO_2BIG = 1
    # Permission denied.
    ERRNO_ACCES = 2
    # Address in use.
    ERRNO_ADDRINUSE = 3
    # Address not available.
    ERRNO_ADDRNOTAVAIL = 4
    # Address family not supported.
    ERRNO_AFNOSUPPORT = 5
    # Resource unavailable, or operation would block.
    ERRNO_AGAIN = 6
    # Connection already in progress.
    ERRNO_ALREADY = 7
    # Bad file descriptor.
    ERRNO_BADF = 8
    # Bad message.
    ERRNO_BADMSG = 9
    # Device or resource busy.
    ERRNO_BUSY = 10
    # Operation canceled.
    ERRNO_CANCELED = 11
    # No child processes.
    ERRNO_CHILD = 12
    # Connection aborted.
    ERRNO_CONNABORTED = 13
    # Connection refused.
    ERRNO_CONNREFUSED = 14
    # Connection reset.
    ERRNO_CONNRESET = 15
    # Resource deadlock would occur.
    ERRNO_DEADLK = 16
    # Destination address required.
    ERRNO_DESTADDRREQ = 17
    # Mathematics argument out of domain of function.
    ERRNO_DOM = 18
    # Reserved.
    ERRNO_DQUOT = 19
    # File exists.
    ERRNO_EXIST = 20
    # Bad address.
    ERRNO_FAULT = 21
    # File too large.
    ERRNO_FBIG = 22
    # Host is unreachable.
    ERRNO_HOSTUNREACH = 23
    # Identifier removed.
    ERRNO_IDRM = 24
    # Illegal byte sequence.
    ERRNO_ILSEQ = 25
    # Operation in progress.
    ERRNO_INPROGRESS = 26
    # Interrupted function.
    ERRNO_INTR = 27
    # Invalid argument.
    ERRNO_INVAL = 28
    # I/O error.
    ERRNO_IO = 29
    # Socket is connected.
    ERRNO_ISCONN = 30
    # Is a directory.
    ERRNO_ISDIR = 31
    # Too many levels of symbolic links.
    ERRNO_LOOP = 32
    # File descriptor value too large.
    ERRNO_MFILE = 33
    # Too many links.
    ERRNO_MLINK = 34
    # Message too large.
    ERRNO_MSGSIZE = 35
    # Reserved.
    ERRNO_MULTIHOP = 36
    # Filename too long.
    ERRNO_NAMETOOLONG = 37
    # Network is down.
    ERRNO_NETDOWN = 38
    # Connection aborted by network.
    ERRNO_NETRESET = 39
    # Network unreachable.
    ERRNO_NETUNREACH = 40
    # Too many files open in system.
    ERRNO_NFILE = 41
    # No buffer space available.
    ERRNO_NOBUFS = 42
    # No such device.
    ERRNO_NODEV = 43
    # No such file or directory.
    ERRNO_NOENT = 44
    # Executable file format error.
    ERRNO_NOEXEC = 45
    # No locks available.
    ERRNO_NOLCK = 46
    # Reserved.
    ERRNO_NOLINK = 47
    # Not enough space.
    ERRNO_NOMEM = 48
    # No message of the desired type.
    ERRNO_NOMSG = 49
    # Protocol not available.
    ERRNO_NOPROTOOPT = 50
    # No space left on device.
    ERRNO_NOSPC = 51
    # Function not supported.
    ERRNO_NOSYS = 52
    # The socket is not connected.
    ERRNO_NOTCONN = 53
    # Not a directory or a symbolic link to a directory.
    ERRNO_NOTDIR = 54
    # Directory not empty.
    ERRNO_NOTEMPTY = 55
    # State not recoverable.
    ERRNO_NOTRECOVERABLE = 56
    # Not a socket.
    ERRNO_NOTSOCK = 57
    # Not supported, or operation not supported on socket.
    ERRNO_NOTSUP = 58
    # Inappropriate I/O control operation.
    ERRNO_NOTTY = 59
    # No such device or address.
    ERRNO_NXIO = 60
    # Value too large to be stored in data type.
    ERRNO_OVERFLOW = 61
    # Previous owner died.
    ERRNO_OWNERDEAD = 62
    # Operation not permitted.
    ERRNO_PERM = 63
    # Broken pipe.
    ERRNO_PIPE = 64
    # Protocol error.
    ERRNO_PROTO = 65
    # Protocol not supported.
    ERRNO_PROTONOSUPPORT = 66
    # Protocol wrong type for socket.
    ERRNO_PROTOTYPE = 67
    # Result too large.
    ERRNO_RANGE = 68
    # Read-only file system.
    ERRNO_ROFS = 69
    # Invalid seek.
    ERRNO_SPIPE = 70
    # No such process.
    ERRNO_SRCH = 71
    # Reserved.
    ERRNO_STALE = 72
    # Connection timed out.
    ERRNO_TIMEDOUT = 73
    # Text file busy.
    ERRNO_TXTBSY = 74
    # Cross-device link.
    ERRNO_XDEV = 75
    # Extension: Capabilities insufficient.
    ERRNO_NOTCAPABLE = 76

    # The peer of this socket has closed or disconnected.
    EVENTRWFLAGS_FD_READWRITE_HANGUP = 1 << 0

    # The time value of clock subscription_clock::id has reached timestamp subscription_clock::timeout.
    EVENTTYPE_CLOCK = 0
    # File descriptor subscription_fd_readwrite::file_descriptor has data available for reading. This event always
    # triggers for regular files.
    EVENTTYPE_FD_READ = 1
    # File descriptor subscription_fd_readwrite::file_descriptor has capacity available for writing. This event always
    # triggers for regular files.
    EVENTTYPE_FD_WRITE = 2

    # Append mode: Data written to the file is always appended to the file's end.
    FDFLAGS_APPEND = 1 << 0
    # Write according to synchronized I/O data integrity completion. Only the data stored in the file is synchronized.
    FDFLAGS_DSYNC = 1 << 1
    # Non-blocking mode.
    FDFLAGS_NONBLOCK = 1 << 2
    # Synchronized read I/O operations.
    FDFLAGS_RSYNC = 1 << 3
    # Write according to synchronized I/O file integrity completion. In addition to synchronizing the data stored in
    # the file, the implementation may also synchronously update the file's metadata.
    FDFLAGS_SYNC = 1 << 4

    FD_STDIN = 0
    FD_STDOUT = 1
    FD_STDERR = 2

    # The type of the file descriptor or file is unknown or is different from any of the other types specified.
    FILETYPE_UNKNOWN = 0
    # The file descriptor or file refers to a block device inode.
    FILETYPE_BLOCK_DEVICE = 1
    # The file descriptor or file refers to a character device inode.
    FILETYPE_CHARACTER_DEVICE = 2
    # The file descriptor or file refers to a directory inode.
    FILETYPE_DIRECTORY = 3
    # The file descriptor or file refers to a regular file inode.
    FILETYPE_REGULAR_FILE = 4
    # The file descriptor or file refers to a datagram socket.
    FILETYPE_SOCKET_DGRAM = 5
    # The file descriptor or file refers to a byte-stream socket.
    FILETYPE_SOCKET_STREAM = 6
    # The file refers to a symbolic link inode.
    FILETYPE_SYMBOLIC_LINK = 7

    # Adjust the last data access timestamp to the value stored in filestat::atim.
    FSTFLAGS_ATIM = 1 << 0
    # Adjust the last data access timestamp to the time of clock clockid::realtime.
    FSTFLAGS_ATIM_NOW = 1 << 1
    # Adjust the last data modification timestamp to the value stored in filestat::mtim.
    FSTFLAGS_MTIM = 1 << 2
    # Adjust the last data modification timestamp to the time of clock clockid::realtime.
    FSTFLAGS_MTIM_NOW = 1 << 3

    # As long as the resolved path corresponds to a symbolic link, it is expanded.
    LOOKUPFLAGS_SYMLINK_FOLLOW = 1 << 0

    # Create file if it does not exist.
    OFLAGS_CREAT = 1 << 0
    # Fail if not a directory.
    OFLAGS_DIRECTORY = 1 << 1
    # Fail if file already exists.
    OFLAGS_EXCL = 1 << 2
    # Truncate file to size 0.
    OFLAGS_TRUNC = 1 << 3

    # A pre-opened directory.
    PREOPENTYPE_DIR = 0

    # Returns the message without removing it from the socket's receive queue.
    RIFLAGS_RECV_PEEK = 1 << 0
    # On byte-stream sockets, block until the full amount of data can be returned.
    RIFLAGS_RECV_WAITALL = 1 << 1

    RIGHTS_FD_DATASYNC = 1 << 0
    RIGHTS_FD_READ = 1 << 1
    RIGHTS_FD_SEEK = 1 << 2
    RIGHTS_FD_FDSTAT_SET_FLAGS = 1 << 3
    RIGHTS_FD_SYNC = 1 << 4
    RIGHTS_FD_TELL = 1 << 5
    RIGHTS_FD_WRITE = 1 << 6
    RIGHTS_FD_ADVISE = 1 << 7
    RIGHTS_FD_ALLOCATE = 1 << 8
    RIGHTS_PATH_CREATE_DIRECTORY = 1 << 9
    RIGHTS_PATH_CREATE_FILE = 1 << 10
    RIGHTS_PATH_LINK_SOURCE = 1 << 11
    RIGHTS_PATH_LINK_TARGET = 1 << 12
    RIGHTS_PATH_OPEN = 1 << 13
    RIGHTS_FD_READDIR = 1 << 14
    RIGHTS_PATH_READLINK = 1 << 15
    RIGHTS_PATH_RENAME_SOURCE = 1 << 16
    RIGHTS_PATH_RENAME_TARGET = 1 << 17
    RIGHTS_PATH_FILESTAT_GET = 1 << 18
    RIGHTS_PATH_FILESTAT_SET_SIZE = 1 << 19
    RIGHTS_PATH_FILESTAT_SET_TIMES = 1 << 20
    RIGHTS_FD_FILESTAT_GET = 1 << 21
    RIGHTS_FD_FILESTAT_SET_SIZE = 1 << 22
    RIGHTS_FD_FILESTAT_SET_TIMES = 1 << 23
    RIGHTS_PATH_SYMLINK = 1 << 24
    RIGHTS_PATH_REMOVE_DIRECTORY = 1 << 25
    RIGHTS_PATH_UNLINK_FILE = 1 << 26
    RIGHTS_POLL_FD_READWRITE = 1 << 27
    RIGHTS_SOCK_SHUTDOWN = 1 << 28
    RIGHTS_SOCK_ACCEPT = 1 << 29

    # Returned by sock_recv: Message data has been truncated.
    ROFLAGS_RECV_DATA_TRUNCATED = 1 << 0

    # Disables further receive operations.
    SDFLAGS_RD = 1 << 0
    # Disables further send operations.
    SDFLAGS_WR = 1 << 1
    SDFLAGS_RW = SDFLAGS_RD | SDFLAGS_WR

    # No signal. Note that POSIX has special semantics for kill(pid, 0), so this value is reserved.
    SIGNAL_NONE = 0
    # Hangup. Action: Terminates the process.
    SIGNAL_HUP = 1
    # Terminate interrupt signal. Action: Terminates the process.
    SIGNAL_INT = 2
    # Terminal quit signal. Action: Terminates the process.
    SIGNAL_QUIT = 3
    # Illegal instruction. Action: Terminates the process.
    SIGNAL_ILL = 4
    # Trace/breakpoint trap. Action: Terminates the process.
    SIGNAL_TRAP = 5
    # Process abort signal. Action: Terminates the process.
    SIGNAL_ABRT = 6
    # Access to an undefined portion of a memory object. Action: Terminates the process.
    SIGNAL_BUS = 7
    # Erroneous arithmetic operation. Action: Terminates the process.
    SIGNAL_FPE = 8
    # Kill. Action: Terminates the process.
    SIGNAL_KILL = 9
    # User-defined signal 1. Action: Terminates the process.
    SIGNAL_USR1 = 10
    # Invalid memory reference. Action: Terminates the process.
    SIGNAL_SEGV = 11
    # User-defined signal 2. Action: Terminates the process.
    SIGNAL_USR2 = 12
    # Write on a pipe with no one to read it. Action: Ignored.
    SIGNAL_PIPE = 13
    # Alarm clock. Action: Terminates the process.
    SIGNAL_ALRM = 14
    # Termination signal. Action: Terminates the process.
    SIGNAL_TERM = 15
    # Child process terminated, stopped, or continued. Action: Ignored.
    SIGNAL_CHLD = 16
    # Continue executing, if stopped. Action: Continues executing, if stopped.
    SIGNAL_CONT = 17
    # Stop executing. Action: Stops executing.
    SIGNAL_STOP = 18
    # Terminal stop signal. Action: Stops executing.
    SIGNAL_TSTP = 19
    # Background process attempting read. Action: Stops executing.
    SIGNAL_TTIN = 20
    # Background process attempting write. Action: Stops executing.
    SIGNAL_TTOU = 21
    # High bandwidth data is available at a socket. Action: Ignored.
    SIGNAL_URG = 22
    # CPU time limit exceeded. Action: Terminates the process.
    SIGNAL_XCPU = 23
    # File size limit exceeded. Action: Terminates the process.
    SIGNAL_XFSZ = 24
    # Virtual timer expired. Action: Terminates the process.
    SIGNAL_VTALRM = 25
    # Profiling timer expired. Action: Terminates the process.
    SIGNAL_PROF = 26
    # Window changed. Action: Ignored.
    SIGNAL_WINCH = 27
    # I/O possible. Action: Terminates the process.
    SIGNAL_POLL = 28
    # Power failure. Action: Terminates the process.
    SIGNAL_PWR = 29
    # Bad system call. Action: Terminates the process.
    SIGNAL_SYS = 30

    SUBCLOCKFLAGS_SUBSCRIPTION_CLOCK_ABSTIME = 1 << 0

    # Seek relative to start-of-file.
    WHENCE_SET = 0
    # Seek relative to current position.
    WHENCE_CUR = 1
    # Seek relative to end-of-file.
    WHENCE_END = 2

    FILE_STATUS_OPENED = 0
    FILE_STATUS_CLOSED = 1

    @dataclasses.dataclass
    class File:
        host_fd: int
        host_flag: int
        host_name: str
        host_status: int
        pipe: typing.Optional[typing.BinaryIO]
        wasm_fd: int
        wasm_flag: int
        wasm_name: str
        wasm_rights_base: int
        wasm_rights_root: int
        wasm_status: int
        wasm_type: int

    def __init__(self, args: typing.List[str], dirs: typing.Dict[str, str], envs: typing.Dict[str, str]):
        self.args = args
        self.dirs = {os.path.normpath(k): os.path.normpath(v) for k, v in dirs.items()}
        self.envs = ['='.join(e) for e in sorted(envs.items())]
        # By setting the pipe to io.BytesIO(bytearray()) to capture output or provide input.
        self.fd: typing.List[Preview1.File] = []
        self.fd.append(self.File(
            host_fd=sys.stdin.fileno(),
            host_flag=0,
            host_name=sys.stdin.name,
            host_status=self.FILE_STATUS_OPENED,
            pipe=None,
            wasm_fd=self.FD_STDIN,
            wasm_flag=0,
            wasm_name=sys.stdin.name,
            wasm_rights_base=self.RIGHTS_POLL_FD_READWRITE | self.RIGHTS_FD_READ,
            wasm_rights_root=0,
            wasm_status=self.FILE_STATUS_OPENED,
            wasm_type=self.FILETYPE_CHARACTER_DEVICE,
        ))
        self.fd.append(self.File(
            host_fd=sys.stdout.fileno(),
            host_flag=0,
            host_name=sys.stdout.name,
            host_status=self.FILE_STATUS_OPENED,
            pipe=None,
            wasm_fd=self.FD_STDOUT,
            wasm_flag=0,
            wasm_name=sys.stdout.name,
            wasm_rights_base=self.RIGHTS_POLL_FD_READWRITE | self.RIGHTS_FD_WRITE,
            wasm_rights_root=0,
            wasm_status=self.FILE_STATUS_OPENED,
            wasm_type=self.FILETYPE_CHARACTER_DEVICE,
        ))
        self.fd.append(self.File(
            host_fd=sys.stderr.fileno(),
            host_flag=0,
            host_name=sys.stderr.name,
            host_status=self.FILE_STATUS_OPENED,
            pipe=None,
            wasm_fd=self.FD_STDERR,
            wasm_flag=0,
            wasm_name=sys.stderr.name,
            wasm_rights_base=self.RIGHTS_POLL_FD_READWRITE | self.RIGHTS_FD_WRITE,
            wasm_rights_root=0,
            wasm_status=self.FILE_STATUS_OPENED,
            wasm_type=self.FILETYPE_CHARACTER_DEVICE,
        ))
        for k, v in sorted(self.dirs.items()):
            k = os.path.normpath(k)
            v = os.path.abspath(os.path.normpath(v))
            self.fd.append(self.File(
                host_fd=os.open(v, os.O_RDONLY | os.O_DIRECTORY),
                host_flag=os.O_RDONLY | os.O_DIRECTORY,
                host_name=v,
                host_status=self.FILE_STATUS_OPENED,
                pipe=None,
                wasm_fd=len(self.fd),
                wasm_flag=0,
                wasm_name=k,
                wasm_rights_base=0b00000111101111111111111000000000,
                wasm_rights_root=0b00001111111111111111111111111111,
                wasm_status=self.FILE_STATUS_OPENED,
                wasm_type=self.FILETYPE_DIRECTORY,
            ))
        # By default, when wasi applications call proc_exit(), wasi.main() will return with the exit code specified
        # rather than terminating the process. Setting this option to 0 will cause the python process to exit with the
        # specified exit code instead.
        self.return_on_exit = 1

    def args_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Read command-line argument data. The size of the array should match that returned by args_sizes_get. Each
        # argument is expected to be \0 terminated.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        argv = args[0]
        argv_buf = args[1]
        for e in self.args:
            mems.put_u32(argv, argv_buf)
            argv += 4
            mems.put(argv_buf, bytearray(e.encode()))
            argv_buf += len(e)
            mems.put_u8(argv_buf, 0)
            argv_buf += 1
        return [self.ERRNO_SUCCESS]

    def args_sizes_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return command-line argument data sizes.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        mems.put_u32(args[0], len(self.args))
        mems.put_u32(args[1], sum([len(e) + 1 for e in self.args]))
        return [self.ERRNO_SUCCESS]

    def bind(self, runtime: pywasm.core.Runtime) -> None:
        i32 = pywasm.core.ValType.i32()
        i64 = pywasm.core.ValType.i64()
        vec = [
            ['args_get', [i32, i32], [i32], self.args_get],
            ['args_sizes_get', [i32, i32], [i32], self.args_sizes_get],
            ['clock_res_get', [i32, i32], [i32], self.clock_res_get],
            ['clock_time_get', [i32, i64, i32], [i32], self.clock_time_get],
            ['environ_get', [i32, i32], [i32], self.environ_get],
            ['environ_sizes_get', [i32, i32], [i32], self.environ_sizes_get],
            ['fd_advise', [i32, i64, i64, i32], [i32], self.fd_advise],
            ['fd_allocate', [i32, i64, i64], [i32], self.fd_allocate],
            ['fd_close', [i32], [i32], self.fd_close],
            ['fd_datasync', [i32], [i32], self.fd_datasync],
            ['fd_fdstat_get', [i32, i32], [i32], self.fd_fdstat_get],
            ['fd_fdstat_set_flags', [i32, i32], [i32], self.fd_fdstat_set_flags],
            ['fd_fdstat_set_rights', [i32, i64, i64], [i32], self.fd_fdstat_set_rights],
            ['fd_filestat_get', [i32, i32], [i32], self.fd_filestat_get],
            ['fd_filestat_set_size', [i32, i64], [i32], self.fd_filestat_set_size],
            ['fd_filestat_set_times', [i32, i64, i64, i32], [i32], self.fd_filestat_set_times],
            ['fd_pread', [i32, i32, i32, i64, i32], [i32], self.fd_pread],
            ['fd_prestat_dir_name', [i32, i32, i32], [i32], self.fd_prestat_dir_name],
            ['fd_prestat_get', [i32, i32], [i32], self.fd_prestat_get],
            ['fd_pwrite', [i32, i32, i32, i64, i32], [i32], self.fd_pwrite],
            ['fd_read', [i32, i32, i32, i32], [i32], self.fd_read],
            ['fd_readdir', [i32, i32, i32, i64, i32], [i32], self.fd_readdir],
            ['fd_renumber', [i32, i32], [i32], self.fd_renumber],
            ['fd_seek', [i32, i64, i32, i32], [i32], self.fd_seek],
            ['fd_sync', [i32], [i32], self.fd_sync],
            ['fd_tell', [i32, i32], [i32], self.fd_tell],
            ['fd_write', [i32, i32, i32, i32], [i32], self.fd_write],
            ['path_create_directory', [i32, i32, i32], [i32], self.path_create_directory],
            ['path_filestat_get', [i32, i32, i32, i32, i32], [i32], self.path_filestat_get],
            ['path_filestat_set_times', [i32, i32, i32, i32, i64, i64, i32], [i32], self.path_filestat_set_times],
            ['path_link', [i32, i32, i32, i32, i32, i32, i32], [i32], self.path_link],
            ['path_open', [i32, i32, i32, i32, i32, i64, i64, i32, i32], [i32], self.path_open],
            ['path_readlink', [i32, i32, i32, i32, i32, i32], [i32], self.path_readlink],
            ['path_remove_directory', [i32, i32, i32], [i32], self.path_remove_directory],
            ['path_rename', [i32, i32, i32, i32, i32, i32], [i32], self.path_rename],
            ['path_symlink', [i32, i32, i32, i32, i32], [i32], self.path_symlink],
            ['path_unlink_file', [i32, i32, i32], [i32], self.path_unlink_file],
            ['poll_oneoff', [i32, i32, i32, i32], [i32], self.poll_oneoff],
            ['proc_exit', [i32], [], self.proc_exit],
            ['proc_raise', [i32], [i32], self.proc_raise],
            ['random_get', [i32, i32], [i32], self.random_get],
            ['sched_yield', [], [i32], self.sched_yield],
            ['sock_accept', [i32, i32, i32], [i32], self.sock_accept],
            ['sock_recv', [i32, i32, i32, i32, i32, i32], [i32], self.sock_recv],
            ['sock_send', [i32, i32, i32, i32, i32], [i32], self.sock_send],
            ['sock_shutdown', [i32, i32], [i32], self.sock_shutdown],
        ]
        runtime.imports['wasi_snapshot_preview1'] = {}
        for e in vec:
            funkype = pywasm.core.FuncType(e[1], e[2])
            runtime.imports['wasi_snapshot_preview1'][e[0]] = runtime.allocate_func_host(funkype, e[3])

    def clock_res_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return the resolution of a clock.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        mems.put_u64(args[1], 1)
        return [self.ERRNO_SUCCESS]

    def clock_time_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return the time value of a clock.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        mems.put_u64(args[2], self.help_time(args[0]))
        return [self.ERRNO_SUCCESS]

    def environ_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Read environment variable data. The sizes of the buffers should match that returned by environ_sizes_get.
        # Key/value pairs are expected to be joined with =, and terminated with 0.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        environ = args[0]
        environ_buf = args[1]
        for e in self.envs:
            mems.put_u32(environ, environ_buf)
            environ += 4
            mems.put(environ_buf, bytearray(e.encode()))
            environ_buf += len(e)
            mems.put_u8(environ_buf, 0)
            environ_buf += 1
        return [self.ERRNO_SUCCESS]

    def environ_sizes_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return environment variable data sizes.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        mems.put_u32(args[0], len(self.envs))
        mems.put_u32(args[1], sum([len(e) + 1 for e in self.envs]))
        return [self.ERRNO_SUCCESS]

    def fd_advise(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Provide file advisory information on a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_FD_ADVISE):
            return [self.ERRNO_NOTCAPABLE]
        return [self.ERRNO_SUCCESS]

    def fd_allocate(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Force the allocation of space in a file.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_ALLOCATE):
            return [self.ERRNO_NOTCAPABLE]
        file = self.fd[args[0]]
        size = args[1] + args[2] - os.stat(file.host_fd).st_size
        if size <= 0:
            return [self.ERRNO_SUCCESS]
        offs = os.lseek(file.host_fd, 0, os.SEEK_CUR)
        os.lseek(file.host_fd, 0, os.SEEK_END)
        os.write(file.host_fd, bytearray(size))
        os.lseek(file.host_fd, offs, os.SEEK_SET)
        return [self.ERRNO_SUCCESS]

    def fd_close(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Close a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        file = self.fd[args[0]]
        if file.wasm_type != self.FILETYPE_CHARACTER_DEVICE:
            os.close(file.host_fd)
            file.host_status = self.FILE_STATUS_CLOSED
        file.wasm_status = self.FILE_STATUS_CLOSED
        return [self.ERRNO_SUCCESS]

    def fd_datasync(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Synchronize the data of a file to disk.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_FD_DATASYNC):
            return [self.ERRNO_NOTCAPABLE]
        return [self.ERRNO_SUCCESS]

    def fd_fdstat_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Get the attributes of a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        mems.put_u8(args[1], file.wasm_type)
        mems.put_u16(args[1]+2, file.wasm_flag)
        mems.put_u64(args[1]+8, file.wasm_rights_base)
        mems.put_u64(args[1]+16, file.wasm_rights_root)
        return [self.ERRNO_SUCCESS]

    def fd_fdstat_set_flags(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Adjust the flags associated with a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_FD_FDSTAT_SET_FLAGS):
            return [self.ERRNO_NOTCAPABLE]
        file = self.fd[args[0]]
        fyes = self.FDFLAGS_APPEND | self.FDFLAGS_APPEND
        if file.wasm_flag ^ args[1] | fyes != fyes:
            # Only support changing the NONBLOCK or APPEND flags.
            return [self.ERRNO_INVAL]
        file.host_flag &= ~os.O_APPEND
        file.host_flag &= ~os.O_NONBLOCK
        file.wasm_flag &= ~self.FDFLAGS_APPEND
        file.wasm_flag &= ~self.FDFLAGS_NONBLOCK
        if args[1] & self.FDFLAGS_APPEND:
            file.host_flag |= os.O_APPEND
            file.wasm_flag |= self.FDFLAGS_APPEND
        if args[1] & self.FDFLAGS_NONBLOCK:
            file.host_flag |= os.O_NONBLOCK
            file.wasm_flag |= self.FDFLAGS_NONBLOCK
        fcntl.fcntl(file.host_fd, fcntl.F_SETFL, file.host_flag)
        return [self.ERRNO_SUCCESS]

    def fd_fdstat_set_rights(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Adjust the rights associated with a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        file = self.fd[args[0]]
        # This can only be used to remove rights
        if file.wasm_rights_base & args[1] != args[1]:
            return [self.ERRNO_NOTCAPABLE]
        if file.wasm_rights_root & args[2] != args[2]:
            return [self.ERRNO_NOTCAPABLE]
        file.wasm_rights_base = args[1]
        file.wasm_rights_root = args[2]
        return [self.ERRNO_SUCCESS]

    def fd_filestat_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return the attributes of an open file.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_FD_FILESTAT_GET):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        info = os.stat(file.host_name)
        mems.put_u64(args[1], 1)
        mems.put_u64(args[1] + 8, info.st_ino)
        mems.put_u8(args[1] + 16, file.wasm_type)
        mems.put_u64(args[1] + 24, info.st_nlink)
        mems.put_u64(args[1] + 32, info.st_size)
        mems.put_u64(args[1] + 40, info.st_atime_ns)
        mems.put_u64(args[1] + 48, info.st_mtime_ns)
        mems.put_u64(args[1] + 56, info.st_ctime_ns)
        return [self.ERRNO_SUCCESS]

    def fd_filestat_set_size(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Adjust the size of an open file. If this increases the file's size, the extra bytes are filled with zeros.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_FILESTAT_SET_SIZE):
            return [self.ERRNO_NOTCAPABLE]
        file = self.fd[args[0]]
        os.ftruncate(file.host_fd, args[1])
        return [self.ERRNO_SUCCESS]

    def fd_filestat_set_times(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Adjust the timestamps of an open file or directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_FD_FILESTAT_SET_TIMES):
            return [self.ERRNO_NOTCAPABLE]
        if args[3] & self.FSTFLAGS_ATIM and args[3] & self.FSTFLAGS_ATIM_NOW:
            return [self.ERRNO_INVAL]
        if args[3] & self.FSTFLAGS_MTIM and args[3] & self.FSTFLAGS_MTIM_NOW:
            return [self.ERRNO_INVAL]
        file = self.fd[args[0]]
        info = os.stat(file.host_fd)
        atim = info.st_atime_ns
        if args[3] & self.FSTFLAGS_ATIM:
            atim = args[1]
        if args[3] & self.FSTFLAGS_ATIM_NOW:
            atim = time.time_ns()
        mtim = info.st_mtime_ns
        if args[3] & self.FSTFLAGS_MTIM:
            mtim = args[2]
        if args[3] & self.FSTFLAGS_MTIM_NOW:
            mtim = args[2]
        os.utime(file.host_fd, ns=(atim, mtim))
        return [self.ERRNO_SUCCESS]

    def fd_pread(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Read from a file descriptor, without using and updating the file descriptor's offset.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_READ):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        iovs_ptr = args[1]
        iovs_len = args[2]
        offs = args[3]
        for _ in range(iovs_len):
            elem_ptr = mems.get_u32(iovs_ptr)
            elem_len = mems.get_u32(iovs_ptr + 4)
            data = os.pread(file.host_fd, elem_len, offs)
            if len(data) == 0:
                break
            mems.put(elem_ptr, bytearray(data))
            iovs_ptr += 8
            offs += len(data)
            if len(data) < elem_len:
                break
        mems.put_u32(args[4], offs - args[3])
        return [self.ERRNO_SUCCESS]

    def fd_prestat_dir_name(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return a description of the given preopened file descriptor.
        if self.help_badf(args[0]) or args[0] - 2 > len(self.dirs):
            return [self.ERRNO_BADF]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = bytearray(file.wasm_name.encode())
        if len(name) > args[2]:
            return [self.ERRNO_NAMETOOLONG]
        mems.put(args[1], name)
        return [self.ERRNO_SUCCESS]

    def fd_prestat_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return a description of the given preopened file descriptor.
        if self.help_badf(args[0]) or args[0] - 2 > len(self.dirs):
            return [self.ERRNO_BADF]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = bytearray(file.wasm_name.encode())
        mems.put_u8(args[1], self.PREOPENTYPE_DIR)
        mems.put_u32(args[1] + 4, len(name))
        return [self.ERRNO_SUCCESS]

    def fd_pwrite(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Write to a file descriptor, without using and updating the file descriptor's offset.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_WRITE):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        iovs_ptr = args[1]
        iovs_len = args[2]
        data = bytearray()
        for _ in range(iovs_len):
            elem_ptr = mems.get_u32(iovs_ptr)
            elem_len = mems.get_u32(iovs_ptr + 4)
            elem = mems.get(elem_ptr, elem_len)
            iovs_ptr += 8
            data.extend(elem)
        size = os.pwrite(file.host_fd, data, args[3])
        mems.put_u32(args[4], size)
        return [self.ERRNO_SUCCESS]

    def fd_read(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Read from a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_READ):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        iovs_ptr = args[1]
        iovs_len = args[2]
        size = 0
        for _ in range(iovs_len):
            elem_ptr = mems.get_u32(iovs_ptr)
            elem_len = mems.get_u32(iovs_ptr + 4)
            data = [
                lambda: os.read(file.host_fd, elem_len),
                lambda: file.pipe.read(elem_len) if file.pipe else b'',
            ][self.help_pipe(args[0])]()
            if len(data) == 0:
                break
            mems.put(elem_ptr, bytearray(data))
            iovs_ptr += 8
            size += len(data)
            if len(data) < elem_len:
                break
        mems.put_u32(args[3], size)
        return [self.ERRNO_SUCCESS]

    def fd_readdir(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Read directory entries from a directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_FD_READDIR):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        dirent = args[1]
        buflen = args[2]
        bufend = dirent + buflen
        cookie = args[3]
        result = ['.', '..', *sorted(os.listdir(file.host_fd))]
        for name in result[cookie:]:
            if dirent + 24 > bufend:
                break
            info = os.stat(os.path.normpath(os.path.join(file.host_name, name)))
            mems.put_u64(dirent, cookie + 1)
            mems.put_u64(dirent + 8, info.st_ino)
            mems.put_u32(dirent + 16, len(name))
            mems.put_u8(dirent + 20, self.help_wasm_type(info))
            dirent += 24
            if dirent + len(name) > bufend:
                break
            mems.put(dirent, bytearray(name.encode()))
            dirent += len(name)
            cookie += 1
        mems.put_u32(args[4], dirent - args[1] if cookie >= len(result) else buflen)
        return [self.ERRNO_SUCCESS]

    def fd_renumber(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        if self.help_badf(args[0]) or self.help_badf(args[1]):
            return [self.ERRNO_BADF]
        stem = self.fd[args[0]]
        dest = self.fd[args[1]]
        if dest.wasm_type != self.FILETYPE_CHARACTER_DEVICE:
            os.close(dest.host_fd)
        dest.host_fd = stem.host_fd
        dest.host_flag = stem.host_flag
        dest.host_name = stem.host_name
        dest.host_status = stem.host_status
        dest.pipe = stem.pipe
        dest.wasm_fd = stem.wasm_fd
        dest.wasm_flag = stem.wasm_flag
        dest.wasm_name = stem.wasm_name
        dest.wasm_rights_base = stem.wasm_rights_base
        dest.wasm_rights_root = stem.wasm_rights_root
        dest.wasm_status = stem.wasm_status
        dest.wasm_type = stem.wasm_type
        stem.host_status = self.FILE_STATUS_CLOSED
        stem.wasm_status = self.FILE_STATUS_CLOSED
        return [self.ERRNO_SUCCESS]

    def fd_seek(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Move the offset of a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_SEEK):
            return [self.ERRNO_NOTCAPABLE]
        assert self.WHENCE_SET == os.SEEK_SET
        assert self.WHENCE_CUR == os.SEEK_CUR
        assert self.WHENCE_END == os.SEEK_END
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        ocur = os.lseek(file.host_fd, 0, args[2])
        # Seek before byte 0 is an error though.
        if ocur + args[1] < 0:
            return [self.ERRNO_INVAL]
        offs = os.lseek(file.host_fd, args[1], args[2])
        mems.put_u64(args[3], offs)
        return [self.ERRNO_SUCCESS]

    def fd_sync(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Synchronize the data and metadata of a file to disk.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_SYNC):
            return [self.ERRNO_NOTCAPABLE]
        file = self.fd[args[0]]
        os.fsync(file.host_fd)
        return [self.ERRNO_SUCCESS]

    def fd_tell(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return the current offset of a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_TELL):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        offs = os.lseek(file.host_fd, 0, os.SEEK_CUR)
        mems.put_u64(args[1], offs)
        return [self.ERRNO_SUCCESS]

    def fd_write(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Write to a file descriptor.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_idir(args[0]):
            return [self.ERRNO_ISDIR]
        if self.help_perm(args[0], self.RIGHTS_FD_WRITE):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        iovs_ptr = args[1]
        iovs_len = args[2]
        data = bytearray()
        for _ in range(iovs_len):
            elem_ptr = mems.get_u32(iovs_ptr)
            elem_len = mems.get_u32(iovs_ptr + 4)
            elem = mems.get(elem_ptr, elem_len)
            iovs_ptr += 8
            data.extend(elem)
        size = [
            lambda: os.write(file.host_fd, data),
            lambda: file.pipe.write(data) if file.pipe else 0,
        ][int(self.help_pipe(args[0]))]()
        mems.put_u32(args[3], size)
        return [self.ERRNO_SUCCESS]

    def help_badf(self, fd: int) -> bool:
        return fd < 0 or fd >= len(self.fd) or self.fd[fd].wasm_status != self.FILE_STATUS_OPENED

    def help_escp(self, root: str, name: str) -> bool:
        return not os.path.normpath(os.path.join(root, name)).startswith(root)

    def help_wasm_type(self, info: os.stat_result) -> int:
        match info.st_mode:
            case x if stat.S_ISBLK(x):
                return self.FILETYPE_BLOCK_DEVICE
            case x if stat.S_ISCHR(x):
                return self.FILETYPE_CHARACTER_DEVICE
            case x if stat.S_ISDIR(x):
                return self.FILETYPE_DIRECTORY
            case x if stat.S_ISREG(x):
                return self.FILETYPE_REGULAR_FILE
            case x if stat.S_ISSOCK(x):
                return self.FILETYPE_UNKNOWN
            case x if stat.S_ISLNK(x):
                return self.FILETYPE_SYMBOLIC_LINK
            case _:
                return self.FILETYPE_UNKNOWN

    def help_idir(self, fd: int) -> bool:
        return self.fd[fd].wasm_type == self.FILETYPE_DIRECTORY

    def help_perm(self, fd: int, perm: int) -> bool:
        return self.fd[fd].wasm_rights_base & perm == 0

    def help_pipe(self, fd: int) -> bool:
        return fd < 3 and self.fd[fd].pipe is not None

    def help_sock(self, fd: int) -> bool:
        return self.fd[fd].wasm_type not in [self.FILETYPE_SOCKET_DGRAM, self.FILETYPE_SOCKET_STREAM]

    def help_time(self, id: int) -> int:
        match id:
            case self.CLOCKID_REALTIME:
                return time.time_ns()
            case self.CLOCKID_MONOTONIC:
                return time.monotonic_ns()
            case self.CLOCKID_PROCESS_CPUTIME_ID:
                return time.process_time_ns()
            case self.CLOCKID_THREAD_CPUTIME_ID:
                return time.thread_time_ns()
            case _:
                return 0

    def main(self, runtime: pywasm.core.Runtime, module: pywasm.core.ModuleInst) -> int:
        # Attempt to begin execution of instance as a wasi command by invoking its _start() export. If instance does
        # not contain a _start() export, then an exception is thrown.
        try:
            runtime.invocate(module, '_start', [])
        except Exception as e:
            runtime.machine.stack.frame.clear()
            runtime.machine.stack.label.clear()
            runtime.machine.stack.value.clear()
            if len(e.args) >= 1 and e.args[0] == SystemExit:
                return e.args[1]
            raise e
        else:
            return 0
        finally:
            for e in self.fd[self.FD_STDOUT: self.FD_STDERR + 1]:
                if e.pipe:
                    e.pipe.seek(0)
            for e in self.fd[self.FD_STDERR + 1:]:
                if e.wasm_type == self.FILETYPE_CHARACTER_DEVICE:
                    continue
                if e.host_status != self.FILE_STATUS_CLOSED:
                    os.close(e.host_fd)
                    e.host_status = self.FILE_STATUS_CLOSED

    def path_create_directory(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Create a directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_CREATE_DIRECTORY):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = mems.get(args[1], args[2]).decode()
        if self.help_escp(file.wasm_name, name):
            return [self.ERRNO_PERM]
        try:
            os.mkdir(name, dir_fd=file.host_fd)
        except FileExistsError:
            return [self.ERRNO_EXIST]
        return [self.ERRNO_SUCCESS]

    def path_filestat_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Return the attributes of a file or directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_FILESTAT_GET):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        flag = args[1]
        name = mems.get(args[2], args[3]).decode()
        if self.help_escp(file.wasm_name, name):
            return [self.ERRNO_PERM]
        foll = flag & self.LOOKUPFLAGS_SYMLINK_FOLLOW != 0
        try:
            info = os.stat(name, dir_fd=file.host_fd, follow_symlinks=foll)
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        mems.put_u64(args[4], 1)
        mems.put_u64(args[4] + 8, info.st_ino)
        mems.put_u8(args[4] + 16, self.help_wasm_type(info))
        mems.put_u64(args[4] + 24, info.st_nlink)
        mems.put_u64(args[4] + 32, info.st_size)
        mems.put_u64(args[4] + 40, info.st_atime_ns)
        mems.put_u64(args[4] + 48, info.st_mtime_ns)
        mems.put_u64(args[4] + 56, info.st_ctime_ns)
        return [self.ERRNO_SUCCESS]

    def path_filestat_set_times(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Adjust the timestamps of a file or directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_FILESTAT_SET_TIMES):
            return [self.ERRNO_NOTCAPABLE]
        if args[6] & self.FSTFLAGS_ATIM and args[6] & self.FSTFLAGS_ATIM_NOW:
            return [self.ERRNO_INVAL]
        if args[6] & self.FSTFLAGS_MTIM and args[6] & self.FSTFLAGS_MTIM_NOW:
            return [self.ERRNO_INVAL]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        flag = args[1]
        name = mems.get(args[2], args[3]).decode()
        if self.help_escp(file.wasm_name, name):
            return [self.ERRNO_PERM]
        info = os.stat(name, dir_fd=file.host_fd)
        atim = info.st_atime_ns
        if args[6] & self.FSTFLAGS_ATIM:
            atim = args[4]
        if args[6] & self.FSTFLAGS_ATIM_NOW:
            atim = time.time_ns()
        mtim = info.st_mtime_ns
        if args[6] & self.FSTFLAGS_MTIM:
            mtim = args[5]
        if args[6] & self.FSTFLAGS_MTIM_NOW:
            mtim = time.time_ns()
        foll = flag & self.LOOKUPFLAGS_SYMLINK_FOLLOW != 0
        try:
            os.utime(name, ns=(atim, mtim), dir_fd=file.host_fd, follow_symlinks=foll)
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        return [self.ERRNO_SUCCESS]

    def path_link(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Create a hard link.
        if self.help_badf(args[0]) or self.help_badf(args[4]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_LINK_SOURCE):
            return [self.ERRNO_NOTCAPABLE]
        if self.help_perm(args[4], self.RIGHTS_PATH_LINK_TARGET):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        stem = self.fd[args[0]]
        dest = self.fd[args[4]]
        stem_name = mems.get(args[2], args[3]).decode()
        dest_name = mems.get(args[5], args[6]).decode()
        if self.help_escp(stem.wasm_name, stem_name):
            return [self.ERRNO_PERM]
        if self.help_escp(dest.wasm_name, dest_name):
            return [self.ERRNO_PERM]
        foll = args[1] & self.LOOKUPFLAGS_SYMLINK_FOLLOW != 0
        try:
            os.link(stem_name, dest_name, src_dir_fd=stem.host_fd, dst_dir_fd=dest.host_fd, follow_symlinks=foll)
        except FileExistsError:
            return [self.ERRNO_EXIST]
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        except PermissionError:
            return [self.ERRNO_PERM]
        return [self.ERRNO_SUCCESS]

    def path_open(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Open a file or directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_OPEN):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = mems.get(args[2], args[3]).decode()
        wasm_name = os.path.normpath(os.path.join(file.wasm_name, name))
        host_name = os.path.normpath(os.path.join(file.host_name, name))
        if '\0' in name:
            return [self.ERRNO_ILSEQ]
        if self.help_escp(file.host_name, name):
            return [self.ERRNO_PERM]
        flag = 0
        if args[1] & self.LOOKUPFLAGS_SYMLINK_FOLLOW == 0:
            flag |= os.O_NOFOLLOW
        if args[4] & self.OFLAGS_CREAT:
            flag |= os.O_CREAT
        if args[4] & self.OFLAGS_DIRECTORY:
            flag |= os.O_DIRECTORY
        if args[4] & self.OFLAGS_EXCL:
            flag |= os.O_EXCL
        if args[4] & self.OFLAGS_TRUNC:
            flag |= os.O_TRUNC
            if file.wasm_rights_base & self.RIGHTS_PATH_FILESTAT_SET_SIZE == 0:
                return [self.ERRNO_PERM]
        if args[5] & self.RIGHTS_FD_READ + self.RIGHTS_FD_WRITE == self.RIGHTS_FD_READ:
            flag |= os.O_RDONLY
        if args[5] & self.RIGHTS_FD_READ + self.RIGHTS_FD_WRITE == self.RIGHTS_FD_WRITE:
            flag |= os.O_WRONLY
        if args[5] & self.RIGHTS_FD_READ + self.RIGHTS_FD_WRITE == self.RIGHTS_FD_READ + self.RIGHTS_FD_WRITE:
            flag |= os.O_RDWR
        if args[7] & self.FDFLAGS_APPEND:
            flag |= os.O_APPEND
        wasm_fd = len(self.fd)
        try:
            host_fd = os.open(name, flag, 0o644, dir_fd=self.fd[args[0]].host_fd)
        except FileExistsError:
            return [self.ERRNO_EXIST]
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        except IsADirectoryError:
            return [self.ERRNO_ISDIR]
        except NotADirectoryError:
            return [self.ERRNO_NOTDIR]
        except OSError as e:
            if platform.system().lower() == 'darwin' and e.errno == 62:
                return [self.ERRNO_LOOP]
            if platform.system().lower() == 'linux' and e.errno == 40:
                return [self.ERRNO_LOOP]
            raise e
        rights_base = args[5]
        rights_root = args[6]
        # Drectory does not have the seek right.
        if os.path.isdir(host_fd):
            void = self.RIGHTS_FD_SEEK
            rights_base &= ~void
            rights_root &= ~void
        # Files shouldn't have rights for path_* syscalls even if manually given.
        if os.path.isfile(host_fd):
            void = sum([
                self.RIGHTS_PATH_CREATE_DIRECTORY,
                self.RIGHTS_PATH_CREATE_FILE,
                self.RIGHTS_PATH_LINK_SOURCE,
                self.RIGHTS_PATH_LINK_TARGET,
                self.RIGHTS_PATH_OPEN,
                self.RIGHTS_PATH_READLINK,
                self.RIGHTS_PATH_RENAME_SOURCE,
                self.RIGHTS_PATH_RENAME_TARGET,
                self.RIGHTS_PATH_FILESTAT_GET,
                self.RIGHTS_PATH_FILESTAT_SET_SIZE,
                self.RIGHTS_PATH_FILESTAT_SET_TIMES,
                self.RIGHTS_PATH_SYMLINK,
                self.RIGHTS_PATH_REMOVE_DIRECTORY,
                self.RIGHTS_PATH_UNLINK_FILE,
            ])
            rights_base &= ~void
            rights_root &= ~void
        self.fd.append(Preview1.File(
            host_fd=host_fd,
            host_flag=flag,
            host_name=host_name,
            host_status=self.FILE_STATUS_OPENED,
            pipe=None,
            wasm_fd=wasm_fd,
            wasm_flag=args[7],
            wasm_name=wasm_name,
            wasm_rights_base=rights_base,
            wasm_rights_root=rights_root,
            wasm_status=self.FILE_STATUS_OPENED,
            wasm_type=self.help_wasm_type(os.fstat(host_fd)),
        ))
        mems.put_u32(args[8], wasm_fd)
        return [self.ERRNO_SUCCESS]

    def path_readlink(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Read the contents of a symbolic link.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_READLINK):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = mems.get(args[1], args[2]).decode()
        if self.help_escp(file.wasm_name, name):
            return [self.ERRNO_PERM]
        try:
            data = os.readlink(name, dir_fd=file.host_fd)
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        size = min(len(data), args[4])
        mems.put(args[3], bytearray(data[:size].encode()))
        mems.put_u32(args[5], size)
        return [self.ERRNO_SUCCESS]

    def path_remove_directory(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Remove a directory.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_REMOVE_DIRECTORY):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = mems.get(args[1], args[2]).decode()
        if self.help_escp(file.wasm_name, name):
            return [self.ERRNO_PERM]
        try:
            os.rmdir(name, dir_fd=file.host_fd)
        except NotADirectoryError:
            return [self.ERRNO_NOTDIR]
        except OSError as e:
            if platform.system().lower() == 'darwin' and e.errno == 66:
                return [self.ERRNO_NOTEMPTY]
            if platform.system().lower() == 'linux' and e.errno == 39:
                return [self.ERRNO_NOTEMPTY]
            raise e
        return [self.ERRNO_SUCCESS]

    def path_rename(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Rename a file or directory.
        if self.help_badf(args[0]) or self.help_badf(args[3]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_RENAME_SOURCE):
            return [self.ERRNO_NOTCAPABLE]
        if self.help_perm(args[3], self.RIGHTS_PATH_RENAME_TARGET):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        stem = self.fd[args[0]]
        dest = self.fd[args[3]]
        stem_name = mems.get(args[1], args[2]).decode()
        dest_name = mems.get(args[4], args[5]).decode()
        if self.help_escp(stem.wasm_name, stem_name):
            return [self.ERRNO_PERM]
        if self.help_escp(dest.wasm_name, dest_name):
            return [self.ERRNO_PERM]
        try:
            os.rename(stem_name, dest_name, src_dir_fd=stem.host_fd, dst_dir_fd=dest.host_fd)
        except FileExistsError:
            return [self.ERRNO_EXIST]
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        except IsADirectoryError:
            return [self.ERRNO_ISDIR]
        except NotADirectoryError:
            return [self.ERRNO_NOTDIR]
        except OSError as e:
            if platform.system().lower() == 'darwin' and e.errno == 66:
                return [self.ERRNO_NOTEMPTY]
            if platform.system().lower() == 'linux' and e.errno == 39:
                return [self.ERRNO_NOTEMPTY]
            raise e
        return [self.ERRNO_SUCCESS]

    def path_symlink(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Create a symbolic link.
        if self.help_badf(args[2]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[2], self.RIGHTS_PATH_SYMLINK):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[2]]
        stem = mems.get(args[0], args[1]).decode()
        dest = mems.get(args[3], args[4]).decode()
        if self.help_escp(file.wasm_name, stem):
            return [self.ERRNO_PERM]
        if self.help_escp(file.wasm_name, dest):
            return [self.ERRNO_PERM]
        try:
            os.symlink(stem, dest, dir_fd=file.host_fd)
        except FileExistsError:
            return [self.ERRNO_EXIST]
        except FileNotFoundError:
            return [self.ERRNO_NOENT]
        except NotADirectoryError:
            return [self.ERRNO_NOTDIR]
        return [self.ERRNO_SUCCESS]

    def path_unlink_file(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Unlink a file.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_perm(args[0], self.RIGHTS_PATH_UNLINK_FILE):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        name = mems.get(args[1], args[2]).decode()
        if self.help_escp(file.wasm_name, name):
            return [self.ERRNO_PERM]
        try:
            os.unlink(name, dir_fd=file.host_fd)
        except IsADirectoryError:
            return [self.ERRNO_ISDIR]
        except NotADirectoryError:
            return [self.ERRNO_NOTDIR]
        except PermissionError:
            return [self.ERRNO_PERM]
        return [self.ERRNO_SUCCESS]

    def poll_oneoff(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Concurrently poll for the occurrence of a set of events.
        subs = args[0]
        outs = args[1]
        nsub = args[2]
        nout = args[3]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        csub = []
        rsub = []
        wsub = []
        for i in range(nsub):
            # Each subscription is 48 bytes
            addr = subs + i * 48
            userdata = mems.get_u64(addr)
            eype = mems.get_u8(addr + 8)
            match eype:
                case self.EVENTTYPE_CLOCK:
                    ckid = mems.get_u64(addr + 16)
                    nval = mems.get_u64(addr + 24)
                    flag = mems.get_u32(addr + 40)
                    ctim = self.help_time(ckid)
                    delt = ctim - nval if flag & self.SUBCLOCKFLAGS_SUBSCRIPTION_CLOCK_ABSTIME else nval
                    ends = nval if flag & self.SUBCLOCKFLAGS_SUBSCRIPTION_CLOCK_ABSTIME else ctim + nval
                    csub.append([userdata, ckid, delt, ends])
                case self.EVENTTYPE_FD_READ:
                    file = mems.get_u32(addr + 16)
                    if self.help_badf(file):
                        return [self.ERRNO_BADF]
                    if self.help_perm(file, self.RIGHTS_POLL_FD_READWRITE):
                        return [self.ERRNO_NOTCAPABLE]
                    rsub.append([userdata, file])
                case self.EVENTTYPE_FD_WRITE:
                    file = mems.get_u32(addr + 16)
                    if self.help_badf(file):
                        return [self.ERRNO_BADF]
                    if self.help_perm(file, self.RIGHTS_POLL_FD_READWRITE):
                        return [self.ERRNO_NOTCAPABLE]
                    wsub.append([userdata, file])
        # Calculate minimum timeout.
        delt = 8
        if csub:
            delt = min([e[2] for e in csub]) / 1000000000.0
        ryes, wyes, _ = select.select(
            [self.fd[fd].host_fd for _, fd in rsub],
            [self.fd[fd].host_fd for _, fd in wsub],
            [],
            delt,
        )
        neve = 0
        for e in csub:
            if self.help_time(e[1]) < e[3]:
                continue
            mems.put_u64(outs, e[0])
            mems.put_u16(outs + 8, self.ERRNO_SUCCESS)
            mems.put_u8(outs + 10, self.EVENTTYPE_CLOCK)
            outs += 32
            neve += 1
        for e in rsub:
            if self.fd[e[1]].host_fd not in ryes:
                continue
            mems.put_u64(outs, e[0])
            mems.put_u16(outs + 8, self.ERRNO_SUCCESS)
            mems.put_u8(outs + 10, self.EVENTTYPE_FD_READ)
            outs += 32
            neve += 1
        for e in wsub:
            if self.fd[e[1]].host_fd not in wyes:
                continue
            mems.put_u64(outs, e[0])
            mems.put_u16(outs + 8, self.ERRNO_SUCCESS)
            mems.put_u8(outs + 10, self.EVENTTYPE_FD_WRITE)
            outs += 32
            neve += 1
        mems.put_u32(nout, neve)
        return [self.ERRNO_SUCCESS]

    def proc_exit(self, _: pywasm.core.Machine, args: typing.List[int]) -> None:
        # Terminate the process normally. An exit code of 0 indicates successful termination of the program. The
        # meanings of other values is dependent on the environment.
        if self.return_on_exit:
            raise Exception(SystemExit, args[0])
        sys.exit(args[0])

    def proc_raise(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Send a signal to the process of the calling thread.
        if args[0] != self.SIGNAL_NONE:
            return [self.ERRNO_INVAL]
        return [self.ERRNO_SUCCESS]

    def random_get(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Write high-quality random data into a buffer.
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        mems.put(args[0], bytearray(random.randbytes(args[1])))
        return [self.ERRNO_SUCCESS]

    def sched_yield(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Temporarily yield execution of the calling thread.
        assert len(args) == 0
        return [self.ERRNO_SUCCESS]

    def sock_accept(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Accept a new incoming connection.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_sock(args[0]):
            return [self.ERRNO_NOTSOCK]
        if self.help_perm(args[0], self.RIGHTS_SOCK_ACCEPT):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        kype = {
            self.FILETYPE_SOCKET_STREAM: socket.SOCK_STREAM,
            self.FILETYPE_SOCKET_DGRAM: socket.SOCK_DGRAM,
        }[file.wasm_type]
        sock = socket.fromfd(file.host_fd, socket.AF_INET, kype)
        if args[1] & self.FDFLAGS_NONBLOCK:
            sock.setblocking(False)
        conn, _ = sock.accept()
        host_fd = conn.fileno()
        wasm_fd = len(self.fd)
        self.fd.append(self.File(
            host_fd=host_fd,
            host_flag=0,
            host_name=file.host_name,
            host_status=self.FILE_STATUS_OPENED,
            pipe=None,
            wasm_fd=wasm_fd,
            wasm_flag=args[1],
            wasm_name=file.wasm_name,
            wasm_rights_base=file.wasm_rights_base,
            wasm_rights_root=file.wasm_rights_root,
            wasm_status=self.FILE_STATUS_OPENED,
            wasm_type=file.wasm_type,
        ))
        mems.put_u32(args[2], wasm_fd)
        return [self.ERRNO_SUCCESS]

    def sock_recv(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Receive a message from a socket.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_sock(args[0]):
            return [self.ERRNO_NOTSOCK]
        if self.help_perm(args[0], self.RIGHTS_FD_READ):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        kype = {
            self.FILETYPE_SOCKET_STREAM: socket.SOCK_STREAM,
            self.FILETYPE_SOCKET_DGRAM: socket.SOCK_DGRAM,
        }[file.wasm_type]
        sock = socket.fromfd(file.host_fd, socket.AF_INET, kype)
        iovs_ptr = args[1]
        iovs_len = args[2]
        ro_flags = 0
        ri_flags = 0
        if args[3] & self.RIFLAGS_RECV_PEEK:
            ri_flags |= socket.MSG_PEEK
        if args[3] & self.RIFLAGS_RECV_WAITALL and file.wasm_type == self.FILETYPE_SOCKET_STREAM:
            # Only meaningful for stream sockets.
            ri_flags |= socket.MSG_WAITALL
        size_all = 0
        for _ in range(iovs_len):
            elem_len = mems.get_u32(iovs_ptr + 4)
            size_all += elem_len
            iovs_ptr += 8
        try:
            data = sock.recv(size_all, ri_flags)
        except BrokenPipeError:
            return [self.ERRNO_PIPE]
        data_len = len(data)
        # If no data received, check for connection closure.
        if data_len == 0 and file.wasm_type == self.FILETYPE_SOCKET_STREAM:
            ro_flags |= self.EVENTRWFLAGS_FD_READWRITE_HANGUP
        # Distribute data across iovec buffers.
        iovs_ptr = args[1]
        offs = 0
        for _ in range(iovs_len):
            if offs >= data_len:
                break
            elem_ptr = mems.get_u32(iovs_ptr)
            elem_len = mems.get_u32(iovs_ptr + 4)
            size = min(elem_len, data_len - offs)
            if size > 0:
                mems.put(elem_ptr, bytearray(data[offs:offs + size]))
                offs += size
            iovs_ptr += 8
        if data_len < size_all:
            ro_flags |= self.ROFLAGS_RECV_DATA_TRUNCATED
        mems.put_u32(args[4], data_len)
        mems.put_u32(args[5], ro_flags)
        return [self.ERRNO_SUCCESS]

    def sock_send(self, m: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Send a message on a socket.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_sock(args[0]):
            return [self.ERRNO_NOTSOCK]
        if self.help_perm(args[0], self.RIGHTS_FD_WRITE):
            return [self.ERRNO_NOTCAPABLE]
        mems = m.store.mems[m.stack.frame[-1].module.mems[0]]
        file = self.fd[args[0]]
        kype = {
            self.FILETYPE_SOCKET_STREAM: socket.SOCK_STREAM,
            self.FILETYPE_SOCKET_DGRAM: socket.SOCK_DGRAM,
        }[file.wasm_type]
        sock = socket.fromfd(file.host_fd, socket.AF_INET, kype)
        iovs_ptr = args[1]
        iovs_len = args[2]
        data = bytearray()
        for _ in range(iovs_len):
            elem_ptr = mems.get_u32(iovs_ptr)
            elem_len = mems.get_u32(iovs_ptr + 4)
            elem = mems.get(elem_ptr, elem_len)
            data.extend(elem)
            iovs_ptr += 8
        try:
            size = sock.send(data)
        except BrokenPipeError:
            return [self.ERRNO_PIPE]
        mems.put_u32(args[4], size)
        return [self.ERRNO_SUCCESS]

    def sock_shutdown(self, _: pywasm.core.Machine, args: typing.List[int]) -> typing.List[int]:
        # Shut down socket send and receive channels.
        if self.help_badf(args[0]):
            return [self.ERRNO_BADF]
        if self.help_sock(args[0]):
            return [self.ERRNO_NOTSOCK]
        if self.help_perm(args[0], self.RIGHTS_SOCK_SHUTDOWN):
            return [self.ERRNO_NOTCAPABLE]
        file = self.fd[args[0]]
        kype = {
            self.FILETYPE_SOCKET_STREAM: socket.SOCK_STREAM,
            self.FILETYPE_SOCKET_DGRAM: socket.SOCK_DGRAM,
        }[file.wasm_type]
        sock = socket.fromfd(file.host_fd, socket.AF_INET, kype)
        shut = 0
        match args[1]:
            case self.SDFLAGS_RD:
                shut = socket.SHUT_RD
            case self.SDFLAGS_WR:
                shut = socket.SHUT_WR
            case self.SDFLAGS_RW:
                shut = socket.SHUT_RDWR
            case _:
                return [self.ERRNO_INVAL]
        try:
            sock.shutdown(shut)
        except OSError as e:
            if platform.system().lower() == 'darwin' and e.errno == 57:
                return [self.ERRNO_CONNABORTED]
            raise e
        return [self.ERRNO_SUCCESS]

#!/usr/bin/env python
import sys

# http://127.0.0.1:8080/source/xref/linux/arch/x86/include/asm/page_64_types.h#35
START_KERNEL_map = 0xffffffff80000000

def v2p(vaddr):
    return vaddr - START_KERNEL_map

if __name__ == "__main__":
    print sys.argv
    vaddr = int(sys.argv[1], 16)

    paddr = v2p(vaddr)
    print "0x{:x}(v) => 0x{:x} {}(p)".format(vaddr, paddr, paddr)

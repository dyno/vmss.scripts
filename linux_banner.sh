#!/bin/bash
set -x

vmss=$PWD/../CentOS6.5-11bd56db.vmss
vmlinux=$PWD/../debuginfo/usr/lib/debug/lib/modules/2.6.32-431.el6.x86_64/vmlinux

set -x
vaddr=0x$(nm $vmlinux | grep linux_banner | awk '{print $1;}')
paddr=$(($vaddr - 0xffffffff80000000))
blockpos=$(./vmss_construct.py  $vmss | grep -F "Memory[0, 0]" | sed -r -e 's/.*pos=(.*),.*$/\1/')
xxd --seek $(($blockpos+$paddr)) -l 256 $vmss

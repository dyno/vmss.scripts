#!/usr/bin/env python

from construct import *

#------------------------------------------------------------------------------
CptDumpHeader = Struct("CptDumpHeader",
    ULInt32("id"),
    ULInt32("version"),
    ULInt32("numgroups"),
)

TAG_VALSIZE_MASK        = 0x3F
TAG_ISBLOCK             = TAG_VALSIZE_MASK
TAG_ISBLOCK_COMPRESSED  = TAG_VALSIZE_MASK - 1
# Poor man's bit fields
# TAG: | NAMELEN | NINDX | VALSIZE |
# bits |15      8|7     6|5       0|
# size |    8    |   2   |    6    |

#tag, name, <i1>, <i2>, value  OR
#tag, name, <i1>, <i2>, nbytes, file offset, <pad>, blockdata
CptGroupItem = Struct("CptGroupItem",
    #Peek(ULInt16("tag")),
    Embed(Union("_u",
        ULInt16("tag"),
        Embed(BitStruct("_tag",
            BitField("nindx", 2), # XXX: mind twist ...
            BitField("valsize", 6),
            BitField("namelen", 8),
        )),
    )),
    Value("is_block", lambda ctx : ctx.valsize in (TAG_ISBLOCK, TAG_ISBLOCK_COMPRESSED)),
    Value("is_block_compressed", lambda ctx : ctx.valsize == TAG_ISBLOCK_COMPRESSED),
    If(lambda ctx : ctx.tag != 0, Embed(Struct("_data",
        String("name", lambda ctx : ctx.namelen),
        Array(lambda ctx : ctx.nindx, SLInt32("index")),
        IfThenElse("_data", lambda ctx: not ctx.is_block,
            Embed(Struct("_value",
                Switch("val", lambda ctx: ctx.valsize, {
                    1 : ULInt8("val"),
                    2 : ULInt16("val"),
                    4 : ULInt32("val"),
                    8 : ULInt64("val"), },
                ),
            )),
            Embed(Struct("_block",
                ULInt64("nbytes"),
                ULInt64("nbytesInMem"),
                ULInt16("padSize"),
                Anchor("pos"),
                Value("blockpos", lambda ctx: ctx.pos + ctx.padSize),
                OnDemand(Array(lambda ctx : ctx.padSize, ULInt8("pad"))),
                OnDemand(Array(lambda ctx : ctx.nbytes, ULInt8("blockdata"))),
            )),
        ),
    ))),
)

CptGroupItems = RepeatUntil(lambda item, ctx: item.tag == 0, CptGroupItem)

MAX_LENGTH      = 64
CptGroup = Struct("CptGroup",
    Embed(Union("_u",
        String("_name", MAX_LENGTH),
        CString("name"),
    )),
    ULInt64("position"),
    Pointer(lambda ctx : ctx.position, CptGroupItems),
    ULInt64("size"),
)

# The on-disk representation is
# <cptDumpHeader>, numgroups<cptGroupDesc>, items...
CheckPoint = Struct("CheckPoint",
    CptDumpHeader,
    Array(lambda ctx: ctx.CptDumpHeader.numgroups, CptGroup),
)

#------------------------------------------------------------------------------
def parse_checkpoint(fp):
    vmss = CheckPoint.parse_stream(fp)
    title = "= Checkpoint Dump Header ="
    print("{}{}".format(title, "=" * (80 - len(title))))
    print("id={id:x}, version={version}, numgroups={numgroups}".format(**vmss.CptDumpHeader))

    print("")
    title = "= Checkpoint Groups ="
    print("{}{}".format(title, "=" * (80 - len(title))))
    groups = {}
    for i, group in enumerate(vmss.CptGroup):
        groups[group.name] = group
        print("{:3d}: name={name:<24} pos={position:<#8x} \t size={size:<#8x}".format(i, **group))

    print("")
    print("{}".format("=" * 80))
    for group_name, group in groups.items():
        print("")
        title = "- Group: {} pos={:#x} size={:#x} -".format(
                group_name, group["position"], group["size"])
        print("{}{}".format(title, "-" * (80 - len(title))))

        for item in group.CptGroupItem:
            if item.tag == 0: break
            item_name = "{}{}".format(item.name, list(item.index) if item.nindx else "")
            if not item.is_block:
                val_format = "{:#0%dx}" % (item.valsize * 2,)
                print("{:40s} => {}".format(item_name, val_format.format(item.val)))
            else:
                print("{:40s} =>{} BLOCK, pos={:#x}, size={:#x}".format(
                      item_name, " COMPRESSED" if item.is_block_compressed else "", item.blockpos, item.nbytes))


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        vmss_filename = sys.argv[1]
    else:
        vmss_filename = "../CentOS6.5-11bd56db.vmss"
    with open(vmss_filename) as fp:
        parse_checkpoint(fp)


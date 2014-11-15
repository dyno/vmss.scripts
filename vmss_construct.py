#!/usr/bin/python

from construct import *

#------------------------------------------------------------------------------
CptDumpHeader = Struct("CptDumpHeader",
    ULInt32("id"),
    ULInt32("version"),
    ULInt32("numgroups"),
)

MAX_LENGTH      = 64
CptGroupDesc = Struct("CptGroupDesc",
    String("name", MAX_LENGTH),
    ULInt64("position"),
    ULInt64("size"),
)

# The on-disk representation is
# <cptDumpHeader>, numgroups<cptGroupDesc>, items...
CheckPoint = Struct("CheckPoint",
    Embed(CptDumpHeader),
    Array(lambda ctx: ctx.numgroups, CptGroupDesc),
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
CptItem = Struct("CptItem",
    Peek(ULInt16("_tag")),
    BitStruct("tag",
        BitField("nindx", 2), # XXX: mind twist ...
        BitField("valsize", 6),
        BitField("namelen", 8),
        Value("is_block", lambda ctx : ctx.valsize in (TAG_ISBLOCK, TAG_ISBLOCK_COMPRESSED)),
        Value("is_block_compressed", lambda ctx : ctx.valsize == TAG_ISBLOCK_COMPRESSED),
    ),
    If(lambda ctx : ctx._tag != 0, Embed(Struct("_data",
        String("name", lambda ctx : ctx.tag.namelen),
        Array(lambda ctx : ctx.tag.nindx, SLInt32("index")),
        IfThenElse("_data", lambda ctx: not ctx.tag.is_block,
            Embed(Struct("_value",
                Switch("val", lambda ctx: ctx.tag.valsize, {
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

#------------------------------------------------------------------------------
def parse_checkpoint(fp):
    vmss = CheckPoint.parse_stream(fp)
    title = "= Checkpoint Dump Header ="
    print("{}{}".format(title, "=" * (80 - len(title))))
    print("id={id:x}, version={version}, numgroups={numgroups}".format(**vmss))

    print("")
    title = "= Checkpoint Groups ="
    print("{}{}".format(title, "=" * (80 - len(title))))
    groups = {}
    for i in range(vmss.numgroups):
        desc = vmss.CptGroupDesc[i]
        d = dict(desc)
        d["name"] = CString("name").parse(d["name"])
        groups[d["name"]] = d
        print("{:3d}: name={name:<24} pos={position:<#8x} \t size={size:<#8x}".format(i, **d))

    print("")
    print("{}".format("=" * 80))
    for group_name in groups:
        print("")
        title = "- Group: {} pos={:#x} size={:#x} -".format(
                group_name, groups[group_name]["position"], groups[group_name]["size"])
        print("{}{}".format(title, "-" * (80 - len(title))))

        fp.seek(groups[group_name]["position"])
        c = CptItem.parse_stream(fp)
        while c._tag != 0:
            var = c.name
            if list(c.index):
                var = "{}{}".format(c.name, list(c.index))
            if not c.tag.is_block:
                val_format = "{:#0%dx}" % (c.tag.valsize * 2,)
                print("{:40s} => {}".format(var, val_format.format(c.val)))
            else:
                print("{:40s} =>{} BLOCK, pos={:#x}, size={:#x}".format(
                      var, " COMPRESSED" if c.tag.is_block_compressed else "", c.blockpos, c.nbytes))
            c = CptItem.parse_stream(fp)

if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        vmss_filename = sys.argv[1]
    else:
        vmss_filename = "CentOS6.5-11bd56db.vmss"
    with open(vmss_filename) as fp:
        parse_checkpoint(fp)

